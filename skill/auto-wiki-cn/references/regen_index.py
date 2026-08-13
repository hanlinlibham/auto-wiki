#!/usr/bin/env python3
"""L1 分层索引重建 —— 顶层 hub 保持"导航页"体量，页面清单下沉到各类型子索引。

为什么存在：hub 若是全量清单，页面数一涨它就线性膨胀，而 recall/ingest 每次都整读
它 —— 上下文随库大小无上限增长。本脚本把清单下沉到 {类型}/_index.md，
顶层 hub 只留计数与入口，读一次的代价与库大小解耦。

用法：
    python regen_index.py wiki/reading            # 重建子索引 + 顶层 hub
    python regen_index.py wiki/reading --check    # 只体检不写盘（ingest 收尾探测用）
    python regen_index.py wiki/reading --quiet    # 静默，只在超阈值时输出 WARN

约定：
- 顶层 hub 中 `## 知识结构` 的代码块是人写的，重建时原样保留；
- 子索引一律机器生成，人不要手改（改了下次重建会被覆盖）；
- 两个文件都带 `tags: [hub, moc]` / `_index` 文件名，供 Obsidian 图谱过滤排除。
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

TODAY = date.today().isoformat()

# 规模阈值（与 scaling.md 三档一致）
L1_PAGES = 50      # 超过：必须分层（本脚本产物）
L2_PAGES = 500     # 超过：必须再上 FTS5（fts_index.py）
HUB_KB = 8         # 顶层 hub 体量红线：导航页不该超过这个量级

SKIP_STEMS = {"_index", "_ontology", "log", "meta", "_report"}


def read_front(text: str) -> tuple[dict, str]:
    """极简 frontmatter 解析：只取标量键，坏格式一律降级为空，绝不抛。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm, body = text[3:end], text[end + 4 :]
    out = {}
    for line in fm.splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition(":")
        v = v.strip()
        if " #" in v:            # YAML 行尾注释：meta.yaml 的模板里每行都有
            v = v.split(" #", 1)[0].strip()
        out[k.strip()] = v.strip("'\"")
    return out, body


def one_liner(body: str, limit: int = 60) -> str:
    """取正文第一句作为一行描述：跳过标题、引用、空行。"""
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ">", "```", "|", "-", "*")):
            continue
        line = re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", line)  # 去 wikilink 语法
        line = re.sub(r"[*`]", "", line)
        for stop in ("。", "；", ". ", "! ", "? "):
            if stop in line:
                line = line.split(stop)[0] + ("。" if stop in ("。", "；") else "")
                break
        return line[:limit]
    return ""


def collect(type_dir: Path) -> list[dict]:
    rows = []
    for md in sorted(type_dir.glob("*.md")):
        if md.stem in SKIP_STEMS:
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except Exception as e:  # 单个坏文件不能拖垮整次重建
            print(f"  ! 跳过读不出的文件 {md.name}: {e}", file=sys.stderr)
            continue
        fm, body = read_front(text)
        rows.append(
            {
                "slug": md.stem,
                "title": fm.get("title") or md.stem,
                "conf": fm.get("confidence", ""),
                "updated": fm.get("updated", ""),
                "desc": one_liner(body),
            }
        )
    return rows


def write_sub_index(type_dir: Path, domain_hub: str, rows: list[dict]) -> None:
    lines = [
        "---",
        f"title: {type_dir.name}索引",
        "type: index",
        f"updated: '{TODAY}'",
        "tags: [hub, moc, index]",
        "---",
        "",
        f"# {type_dir.name} · 子索引（自动生成）",
        "",
        f"> 由 `regen_index.py` 重建，**勿手改**。共 {len(rows)} 页 · 返回 [[{domain_hub}]]",
        "",
    ]
    contested = [r for r in rows if r["conf"] == "contested"]
    if contested:
        lines += [f"**有分歧待裁决 {len(contested)} 页**：" + "、".join(f"[[{r['slug']}]]" for r in contested), ""]
    for r in rows:
        mark = " ⚠️" if r["conf"] == "contested" else ""
        desc = f" —— {r['desc']}" if r["desc"] else ""
        lines.append(f"- [[{r['slug']}]]{mark}{desc}")
    lines.append("")
    (type_dir / "_index.md").write_text("\n".join(lines), encoding="utf-8")


KNOW_RE = re.compile(r"(## 知识结构\n```.*?```)", re.S)


def write_hub(ddir: Path, hub_file: Path, hub: str, central: str, direction: str,
              buckets: dict[str, list[dict]], recent_log: list[str]) -> None:
    keep = ""
    if hub_file.exists():
        try:
            m = KNOW_RE.search(hub_file.read_text(encoding="utf-8"))
            if m:
                keep = m.group(1)
        except Exception:
            pass
    total = sum(len(v) for v in buckets.values())
    lines = [
        "---",
        f"title: {hub}",
        "type: ontology",
        f"domain: {ddir.name}",
        f"direction: {direction}",
        f"updated: '{TODAY}'",
        "tags: [hub, moc]",
        "---",
        "",
        f"# {hub}领域 Wiki · 导航",
        "",
        f"> 中心实体 [[{central}]] · 本体契约见 [[_ontology]] · 数据见 data.db · 方向：{direction}",
        "",
        f"> **本页是导航，不是清单。**共 {total} 页；页面明细在各类型的 `_index.md`，",
        "> 全文检索用 `fts_index.py`。读本页即可定位到类型，**不要把子索引整读进上下文**。",
        "",
        "## 分类入口",
        "",
        "| 类型 | 页数 | 入口 |",
        "|---|---|---|",
    ]
    for t in sorted(buckets):
        n = len(buckets[t])
        lines.append(f"| {t} | {n} | [[{t}/_index\\|{t}索引]] |")
    lines.append("")

    contested = [r for v in buckets.values() for r in v if r["conf"] == "contested"]
    if contested:
        lines += [
            f"## 待裁决（{len(contested)}）",
            "",
            "、".join(f"[[{r['slug']}]]" for r in contested[:20])
            + ("……" if len(contested) > 20 else ""),
            "",
        ]

    lines.append(keep if keep else "## 知识结构\n```\n（首次 ingest 后补：中心实体辐射图）\n```")
    lines.append("")
    if recent_log:
        lines += ["## 最近 ingest", ""] + [f"- {l}" for l in recent_log[:10]] + [""]
    hub_file.write_text("\n".join(lines), encoding="utf-8")


def recent_from_log(ddir: Path, n: int = 10) -> list[str]:
    log = ddir / "log.md"
    if not log.exists():
        return []
    try:
        lines = [l.strip("- ").strip() for l in log.read_text(encoding="utf-8").splitlines()
                 if l.startswith("- ")]
    except Exception:
        return []
    return lines[-n:][::-1]


def main() -> int:
    ap = argparse.ArgumentParser(description="L1 分层索引重建（顶层 hub 瘦身 + 类型子索引）")
    ap.add_argument("domain_dir", help="领域目录，如 wiki/reading")
    ap.add_argument("--check", action="store_true", help="只体检不写盘")
    ap.add_argument("--quiet", action="store_true", help="只在超阈值时输出")
    args = ap.parse_args()

    ddir = Path(args.domain_dir)
    if not ddir.is_dir():
        print(f"✗ 目录不存在：{ddir}", file=sys.stderr)
        return 1

    meta = {}
    mp = ddir / "meta.yaml"
    if mp.exists():
        raw = mp.read_text(encoding="utf-8")
        try:
            import yaml  # 与 new_domain.py 同一依赖
            meta = yaml.safe_load(raw) or {}
        except Exception:
            meta, _ = read_front("---\n" + raw + "\n---\n")
    if not isinstance(meta, dict):
        meta = {}
    hub = str(meta.get("hub") or ddir.name).strip()
    if not hub or any(c in hub for c in "#/\\\n") or " " in hub:
        print(f"WARN  meta.yaml 的 hub 值可疑（{hub!r}），回退用目录名 {ddir.name}", file=sys.stderr)
        hub = ddir.name
    central = meta.get("central_entity", "")
    direction = meta.get("direction", "未分类")
    hub_file = ddir / f"{hub}.md"

    buckets = {}
    for sub in sorted(p for p in ddir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        rows = collect(sub)
        if rows or (sub / "_index.md").exists():
            buckets[sub.name] = rows

    total = sum(len(v) for v in buckets.values())
    hub_kb = hub_file.stat().st_size / 1024 if hub_file.exists() else 0

    if not args.check:
        for t, rows in buckets.items():
            write_sub_index(ddir / t, hub, rows)
        write_hub(ddir, hub_file, hub, central, direction, buckets, recent_from_log(ddir))
        new_kb = hub_file.stat().st_size / 1024
        if not args.quiet:
            print(f"✓ 重建完成：{ddir}")
            for t in sorted(buckets):
                print(f"    {t}/_index.md  {len(buckets[t])} 页")
            print(f"    顶层 hub {hub_file.name}：{hub_kb:.1f} KB → {new_kb:.1f} KB（共 {total} 页）")
        hub_kb = new_kb

    warns = []
    if total > L2_PAGES:
        warns.append(f"页面数 {total} > {L2_PAGES}：必须启用 L2 全文索引 —— `python fts_index.py {ddir} build`")
    elif total > L1_PAGES:
        warns.append(f"页面数 {total} > {L1_PAGES}：已处于 L1 分层区间，ingest 收尾请保持重建本索引")
    if hub_kb > HUB_KB:
        warns.append(f"顶层 hub {hub_kb:.1f} KB > {HUB_KB} KB：导航页偏胖，检查是否有人往里塞了清单")
    for w in warns:
        print(f"WARN  {w}")
    if args.check and not warns and not args.quiet:
        print(f"✓ 规模体检通过：{total} 页，hub {hub_kb:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
