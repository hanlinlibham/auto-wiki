"""把 wiki/{domain} 投影成一个 OKF v0.1 bundle（对外交换层）。

OKF（Open Knowledge Format, GoogleCloudPlatform/knowledge-catalog）是
「markdown + YAML frontmatter 目录」的最小知识交换格式，唯一必填项是 frontmatter
的 `type`。本库的页面天生已满足它，导出几乎无损；真正的损耗在 data.db 的双时态层
与受控关系边——OKF 没有它们的结构位置，本脚本把这部分压成带 ⚠️ 的 markdown 投影。

设计立场（见库根 CLAUDE.md「OKF 关系」）：
    严格内核（data.db + 受控词表 + 6 档时间模型）只在库内享用，
    OKF 是单向导出的「出入境口岸」——给非 Obsidian 工具/外部消费者读。
    **绝不反向以 OKF 为主存**（会丢时间、类型边、可查询性三样核心价值）。

用法：
    python export_okf.py wiki/macro                     # 默认输出到 wiki/macro/okf/
    python export_okf.py wiki/macro --out /tmp/macro-okf
    python export_okf.py wiki/macro --name "Macro OKF"

参考实现可视化（可选，需克隆官方仓库）：
    python -m reference_agent visualize --bundle <out>   # 渲染 viz.html
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import yaml


# ── auto-wiki 节点目录 → OKF type（描述性、自解释；OKF type 不集中注册）──────
DIR_TYPE = {
    "机构": "Institution",
    "工具": "Policy Instrument",
    "指标": "Indicator",
    "机制": "Mechanism",
    "事件": "Event",
    "分析": "Analysis",
    "来源": "Source",
}
# entity 的 subtype 更细，优先用它（institution/instrument/indicator）
SUBTYPE_TYPE = {
    "institution": "Institution",
    "instrument": "Policy Instrument",
    "indicator": "Indicator",
}
RESERVED = {"index.md", "log.md"}


def split_frontmatter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, m.group(2)


def load_config_labels(wiki_dir: Path) -> set[str]:
    """从库根 .burrow/config.json 读 classified_as 标签（边非页）。

    这些标签在本库刻意「不建页」，导出时渲染成普通文字而非链接，避免悬空。
    向上找最多 5 层；找不到则返回空集（退化为：标签 → 悬空链接，OKF 仍合法）。
    """
    p = wiki_dir.resolve()
    for _ in range(5):
        cfg = p / ".burrow" / "config.json"
        if cfg.is_file():
            try:
                data = json.loads(cfg.read_text(encoding="utf-8"))
                return set(data.get("dashboard", {}).get("labels", []) or [])
            except (json.JSONDecodeError, OSError):
                return set()
        if p.parent == p:
            break
        p = p.parent
    return set()


def collect_pages(wiki_dir: Path, skip_dir: Path | None = None):
    """slug -> {dir, fm, body, fname, rel}。跳过 _前缀、保留字、以及导出目录自身。

    skip_dir 防止把上一次导出的 bundle（若落在 wiki_dir 内）当成节点重抓（幂等）。
    """
    skip_res = skip_dir.resolve() if skip_dir else None
    pages = {}
    for p in sorted(wiki_dir.rglob("*.md")):
        if p.name.startswith("_") or p.name in RESERVED:
            continue
        if skip_res and skip_res in p.resolve().parents:
            continue
        rel = p.relative_to(wiki_dir)
        d = rel.parts[0] if len(rel.parts) > 1 else ""
        fm, body = split_frontmatter(p.read_text(encoding="utf-8"))
        pages[p.stem] = dict(dir=d, fm=fm, body=body, fname=p.name,
                             rel=str(rel).replace("\\", "/"))
    return pages


def okf_type(pg) -> str:
    sub = pg["fm"].get("subtype")
    if sub in SUBTYPE_TYPE:
        return SUBTYPE_TYPE[sub]
    return DIR_TYPE.get(pg["dir"], pg["fm"].get("type", "Concept"))


def bundle_link(pages, slug, labels):
    """目标 slug → (markdown 链接 或 纯文字)。分类标签渲成文字，避免悬空。"""
    if slug in labels:
        return f"**{slug}**"  # 边非页：本库刻意不建页
    pg = pages.get(slug)
    if pg:
        return f"[{slug}](/{pg['rel']})"
    return f"[{slug}](/{slug}.md)"  # 跨域 / 未建：OKF 容忍坏链接（§5.3/§9）


def wikilinks_to_okf(body, pages, labels):
    def repl(m):
        name = m.group(1).split("|")[0].strip()
        return bundle_link(pages, name, labels)
    return re.sub(r"\[\[([^\]]+)\]\]", repl, body)


def strip_relations_section(body: str) -> str:
    """删掉源页正文里的「## 关联」段，避免与下面生成的 # Relationships 重复。"""
    return re.split(r"\n#{1,6}\s*关联\s*\n", body, maxsplit=1)[0].rstrip() + "\n"


def render_relations(pg, pages, labels):
    rels = pg["fm"].get("relations") or []
    if not rels:
        return ""
    out = ["\n# Relationships\n",
           "> 类型由本行的 prose 承载（OKF 链接本身无类型，见 SPEC §5.3）。\n"]
    for r in rels:
        typ = r.get("type", "related")
        role = r.get("bound_role")
        label = f"`{typ}`" + (f" ({role})" if role else "")
        out.append(f"- {label} → {bundle_link(pages, r.get('target', ''), labels)}")
    return "\n".join(out) + "\n"


def render_db_projection(slug, db):
    """T0 观测 / T1+T2 fact 压成 markdown 表 —— 有损投影，打 ⚠️。"""
    cur = db.cursor()
    out = []
    dp = cur.execute(
        "select field,value,unit,period,recorded_at,confidence,supersedes_id "
        "from data_points where page_slug=? order by period", (slug,)).fetchall()
    if dp:
        out += ["\n# Data (snapshot projection)\n",
                "> ⚠️ OKF 无双时态层：下表丢失 valid/transaction 两轴的区分、"
                "supersedes 修正链、退役历史。权威值仍在本库 data.db。\n",
                "| field | value | unit | period | recorded_at | conf | supersedes |",
                "|---|---|---|---|---|---|---|"]
        for f, v, u, per, rec, c, sup in dp:
            out.append(f"| {f} | {v} | {u} | {per} | {rec} | {c} | {sup or ''} |")
    fa = cur.execute(
        "select predicate,object_text,object_slug,valid_from,valid_to,is_current,"
        "caused_by_event,retired_by_event from facts where page_slug=?", (slug,)).fetchall()
    if fa:
        out += ["\n# State / Facts (snapshot projection)\n",
                "> ⚠️ 拉链表压平：is_current=0 的退役行、caused_by/retired_by 事件指针"
                "在通用 OKF 消费端无结构位置。权威态仍在本库 data.db facts 拉链。\n",
                "| predicate | object | valid_from | valid_to | current | caused_by | retired_by |",
                "|---|---|---|---|---|---|---|"]
        for pr, ot, osl, vf, vt, cur_, cb, rb in fa:
            out.append(f"| {pr} | {ot or osl or ''} | {vf} | {vt} | {cur_} | {cb or ''} | {rb or ''} |")
    return "\n".join(out) + ("\n" if out else "")


def iso(d):
    if not d:
        return None
    s = str(d)
    return s if "T" in s else f"{s}T00:00:00Z"


def export(wiki_dir: Path, out_dir: Path, name: str | None):
    meta = {}
    meta_path = wiki_dir / "meta.yaml"
    if meta_path.is_file():
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    labels = load_config_labels(wiki_dir)
    pages = collect_pages(wiki_dir, skip_dir=out_dir)
    db_path = wiki_dir / "data.db"
    db = sqlite3.connect(str(db_path)) if db_path.is_file() else None

    stats = dict(pages=0, edges=0, dangling=0)
    by_dir: dict[str, list] = {}

    for slug, pg in pages.items():
        fm = pg["fm"]
        nfm = {"type": okf_type(pg), "title": fm.get("title", slug)}
        first_line = pg["body"].strip().split("\n")[0].strip() if pg["body"].strip() else ""
        if first_line and not first_line.startswith("#"):
            nfm["description"] = first_line[:120]
        # resource: 优先取 frontmatter 既有 url/resource/link；来源页可绑外部链接
        for k in ("resource", "url", "link", "source_url"):
            if fm.get(k):
                nfm["resource"] = fm[k]
                break
        ts = iso(fm.get("updated") or fm.get("created"))
        if ts:
            nfm["timestamp"] = ts
        if fm.get("aliases"):
            nfm["tags"] = fm["aliases"]
        if fm.get("confidence"):
            nfm["confidence"] = fm["confidence"]  # 扩展键，OKF 容忍

        body = strip_relations_section(wikilinks_to_okf(pg["body"], pages, labels))
        body += render_relations(pg, pages, labels)
        if db is not None:
            body += render_db_projection(slug, db)

        stats["edges"] += len(fm.get("relations") or [])
        for r in (fm.get("relations") or []):
            t = r.get("target")
            if t and t not in pages and t not in labels:
                stats["dangling"] += 1

        odir = out_dir / pg["dir"] if pg["dir"] else out_dir
        odir.mkdir(parents=True, exist_ok=True)
        fmtxt = "---\n" + yaml.safe_dump(nfm, allow_unicode=True, sort_keys=False) + "---\n"
        (odir / pg["fname"]).write_text(fmtxt + body, encoding="utf-8")
        by_dir.setdefault(pg["dir"], []).append(
            (nfm["title"], pg["fname"], nfm.get("description", "")))
        stats["pages"] += 1

    # index.md：每个子目录一份（OKF §6 渐进式披露）
    for d, items in by_dir.items():
        odir = out_dir / d if d else out_dir
        lines = [f"# {DIR_TYPE.get(d, d or 'Root')}\n"]
        for title, fname, desc in sorted(items):
            lines.append(f"* [{title}]({fname}) - {desc}")
        (odir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 根 index.md：唯一允许带 frontmatter 的 index（声明 okf_version）
    disp = name or meta.get("hub") or wiki_dir.name
    root = [f'---\nokf_version: "0.1"\ntitle: {disp}\n---\n',
            f"# {disp} — {meta.get('description', wiki_dir.name)}\n"]
    if meta.get("central_entity"):
        root.append(f"中心实体：{bundle_link(pages, meta['central_entity'], labels)}\n")
    for d in sorted(by_dir):
        if d:
            root.append(f"* [{DIR_TYPE.get(d, d)}]({d}/) - {len(by_dir[d])} concepts")
    (out_dir / "index.md").write_text("\n".join(root) + "\n", encoding="utf-8")

    # log.md 直接复制（已是 OKF §7 形态）
    src_log = wiki_dir / "log.md"
    if src_log.is_file():
        (out_dir / "log.md").write_text(src_log.read_text(encoding="utf-8"), encoding="utf-8")

    # 统计
    print("=" * 56)
    print(f"OKF export: {wiki_dir}  →  {out_dir}")
    print("=" * 56)
    print(f"  pages exported            : {stats['pages']}")
    print(f"  typed edges → prose links : {stats['edges']}")
    print(f"  dangling links (cross-domain / 未建) : {stats['dangling']}")
    if db is not None:
        for t in ("data_points", "facts", "events", "relations"):
            n = db.execute(f"select count(*) from {t}").fetchone()[0]
            print(f"  data.db {t:<12} (snapshot-only in OKF) : {n}")
        retired = db.execute("select count(*) from facts where is_current=0").fetchone()[0]
        bound = db.execute("select count(*) from relations where bound_role is not null").fetchone()[0]
        print(f"    ↳ retired facts losing zipper home   : {retired}")
        print(f"    ↳ edges losing bound_role attr       : {bound}")
        db.close()

    # OKF v0.1 conformance（§9：每非保留 .md 有可解析 frontmatter + 非空 type）
    bad = 0
    total = 0
    for p in out_dir.rglob("*.md"):
        if p.name in RESERVED:
            continue
        total += 1
        fm, _ = split_frontmatter(p.read_text(encoding="utf-8"))
        if not fm.get("type"):
            bad += 1
            print(f"  ✗ missing type: {p.relative_to(out_dir)}")
    print(f"\n  OKF v0.1 conformance: {total} concept docs, {bad} missing `type` "
          f"→ {'CONFORMANT' if bad == 0 else 'NON-CONFORMANT'}")
    return bad == 0


def main():
    ap = argparse.ArgumentParser(
        description="把 wiki/{domain} 投影成 OKF v0.1 bundle（单向导出 / 对外交换层）")
    ap.add_argument("wiki_dir", help="领域目录，如 wiki/macro")
    ap.add_argument("--out", default=None,
                    help="输出 bundle 目录（默认 <vault>/okf/<domain>，在 wiki 树外，"
                         "不污染 Obsidian 图谱）")
    ap.add_argument("--name", default=None, help="bundle 显示名（默认取 meta.hub）")
    args = ap.parse_args()

    wiki_dir = Path(args.wiki_dir)
    if not wiki_dir.is_dir():
        print(f"Not a directory: {wiki_dir}")
        sys.exit(1)
    # 默认落 <vault>/okf/<domain>：在 wiki 树外，避免污染 Obsidian 图谱与被重抓
    out_dir = Path(args.out) if args.out else wiki_dir.parent.parent / "okf" / wiki_dir.name
    ok = export(wiki_dir, out_dir, args.name)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
