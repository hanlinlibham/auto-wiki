#!/usr/bin/env python3
"""五试机审·机器镜头预检（advisory）— auto-wiki v0.4.0 新增。

两个确定性镜头，在 LLM 判断与人裁之前把机器能断言的问题拦在起草侧：

  镜头 S（schema 预检）——R11 tech_air 批次教训的四类病根：
    双 yaml 块（违「一卡一页」）、枚举值夹注释、relations 键名想当然（to/slug/page）、
    必填字段缺失/格式错。schema 校验本就是 v0.3.x 既有硬闸，本镜头把它前移并扩类。

  镜头 D（重复性预检）——秩维框架「写入前共线检查」的字符串级退化实现：
    新候选名 vs 现有 slug/title/aliases 的撞车检测。**同类型才算撞车候选**；
    跨类型高相似降为提示（来源页↔事件页是四界故意分开建的合法对——
    2026-07-25 回测试点实证：embedding/相似度看不见四界，必须按类型分层）。
    语义级（embedding）版本等 sqlite-vec 建成后另行实现，见 ROADMAP。

纪律（R7 四纪律对齐）：advisory——镜头 D 永不拦截，只输出候选与建议，
建新页与否仍由 ingest 分支判断+人裁决定；镜头 S 默认也只报告（退出码 0），
`--strict` 才以退出码表达失败（既有 schema 闸在 ingest 第 6 步照旧执行）。

用法：
  python precheck.py page <file.md|wiki_dir> [--strict]        # 镜头 S
  python precheck.py dup "<候选名>" --wiki <wiki_dir>          # 镜头 D 单查
      [--aliases 别名1,别名2] [--type entity] [--threshold 0.75]
  python precheck.py sweep --wiki <wiki_dir> [--threshold 0.80] [--include-sources]
                                                               # 镜头 D 全库扫描 → t0-merge 候选
  python precheck.py contract <vault_or_wiki_dir>              # 镜头 M 契约/出生戳迁移检查（0.4.1）
  python precheck.py stamp                                     # 输出 policy 版本章（run 档用）
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import warnings
from pathlib import Path

import yaml

# 关系词表的权威在各域 _ontology.md（受控词表）；schema.py 硬编码的通用集合
# 对合法域词表（built_on/classified_as/instance_of…）会误报——预检静音之。
# 词表机器可读化（从 _ontology.md 读真词表做真校验）排 0.5.0，见 ROADMAP。
warnings.filterwarnings("ignore", message=r"非标准关系类型")

HERE = Path(__file__).resolve().parent

# 枚举字段：值里出现括号/注释即为「枚举夹注」（R11 病根：source_type: 二手(券商)）
ENUM_FIELDS = ("type", "subtype", "source_type", "confidence", "durability")
ANNOT_RE = re.compile(r"[()（）\[\]【】]|注[:：]")
# relations 合法键（含时态扩展列）；此外一律视为键名想当然
REL_KEYS = {"target", "type", "valid_from", "valid_to", "retract_event_slug"}


# ── 公共 ──────────────────────────────────────────────────

def _split(text: str):
    """返回 (frontmatter_dict|None, body, err)。"""
    if not text.startswith("---"):
        return None, text, "缺 YAML frontmatter"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text, "frontmatter 未闭合"
    try:
        return (yaml.safe_load(parts[1]) or {}), parts[2], None
    except Exception as e:
        return None, parts[2], f"YAML 解析失败: {e}"


def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-z一-鿿]", "", str(s).lower())


def _node_pages(wiki_dir: Path):
    """扫描节点子目录，返回 [{slug,title,aliases,type,subtype,path}]。"""
    out = []
    for d in sorted(wiki_dir.iterdir()):
        if not d.is_dir() or d.name.startswith((".", "_")):
            continue
        for f in sorted(d.glob("*.md")):
            if f.name.startswith("_"):
                continue
            fm, _, err = _split(f.read_text(encoding="utf-8", errors="ignore"))
            if err or not isinstance(fm, dict):
                continue
            out.append({
                "slug": f.stem,
                "title": str(fm.get("title", f.stem)),
                "aliases": [str(a) for a in (fm.get("aliases") or [])],
                "type": str(fm.get("type", "")),
                "subtype": str(fm.get("subtype", "")),
                "path": str(f.relative_to(wiki_dir)),
            })
    return out


# ── 镜头 S：schema 预检 ───────────────────────────────────

def check_page(path: Path) -> list[dict]:
    """返回问题列表 [{level: error|warn, code, msg}]。"""
    issues = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    fm, body, err = _split(text)
    if err:
        return [{"level": "error", "code": "frontmatter", "msg": err}]
    if str(fm.get("type", "")).startswith("_"):
        return []  # folder note

    # 1) 双 yaml 块：正文里再次出现能解析成 dict 且带 title/type 的 --- 块
    for m in re.finditer(r"(?ms)^---\s*\n(.*?)^---\s*$", body):
        try:
            extra = yaml.safe_load(m.group(1))
        except Exception:
            continue
        if isinstance(extra, dict) and ("type" in extra or "title" in extra):
            issues.append({"level": "error", "code": "double-yaml",
                           "msg": "正文疑似含第二个 frontmatter 块（违「一卡一页」，应拆独立页面）"})
            break

    # 2) 枚举夹注
    for k in ENUM_FIELDS:
        v = fm.get(k)
        if isinstance(v, str) and ANNOT_RE.search(v):
            issues.append({"level": "error", "code": "enum-annot",
                           "msg": f"枚举字段 {k}='{v}' 夹带注释/括号——枚举值必须干净，说明写正文"})

    # 3) relations 键名
    rels = fm.get("relations") or []
    if isinstance(rels, list):
        for i, r in enumerate(rels):
            if not isinstance(r, dict):
                issues.append({"level": "error", "code": "rel-shape",
                               "msg": f"relations[{i}] 不是映射：{r!r}"})
                continue
            bad = set(r) - REL_KEYS
            if bad:
                issues.append({"level": "error", "code": "rel-key",
                               "msg": f"relations[{i}] 含非法键 {sorted(bad)}（合法：target/type[/valid_from/valid_to/retract_event_slug]）"})
            if "target" not in r or "type" not in r:
                issues.append({"level": "error", "code": "rel-missing",
                               "msg": f"relations[{i}] 缺 target 或 type：{r!r}"})

    # 4) 既有 schema 闸（pydantic 全字段校验）
    sys.path.insert(0, str(HERE))
    try:
        import schema as _schema  # noqa: PLC0415
        ok, msg = _schema.validate_page(path)
        if not ok:
            issues.append({"level": "error", "code": "schema", "msg": msg})
        elif "MIGRATE" in msg:
            issues.append({"level": "warn", "code": "schema", "msg": msg})
    except ImportError as e:
        issues.append({"level": "warn", "code": "schema-skip", "msg": f"schema.py 依赖缺失，跳过 pydantic 校验: {e}"})
    return issues


def cmd_page(target: Path, strict: bool) -> int:
    files = ([target] if target.is_file()
             else [f for d in sorted(target.iterdir())
                   if d.is_dir() and not d.name.startswith((".", "_"))
                   for f in sorted(d.glob("*.md")) if not f.name.startswith("_")])
    n_err = 0
    for f in files:
        issues = check_page(f)
        errs = [i for i in issues if i["level"] == "error"]
        n_err += len(errs)
        if issues:
            print(f"✗ {f}")
            for i in issues:
                print(f"    [{i['level']}] {i['code']}: {i['msg']}")
    print(f"\n[镜头S] {len(files)} 页 · {n_err} 处 error（advisory{'' if not strict else '·strict'}）")
    return 1 if (strict and n_err) else 0


# ── 镜头 D：重复性预检 ────────────────────────────────────

def _match(cand_names: list[str], page: dict, threshold: float):
    """返回 (score, 依据) 或 None。"""
    targets = [page["slug"], page["title"], *page["aliases"]]
    best = None
    for c in cand_names:
        nc = _norm(c)
        if not nc:
            continue
        for t in targets:
            nt = _norm(t)
            if not nt:
                continue
            if nc == nt:
                score, how = 1.0, f"同名（{t}）"
            elif len(nc) >= 4 and len(nt) >= 4 and (nc in nt or nt in nc):
                score, how = 0.9, f"包含（{t}）"
            else:
                r = difflib.SequenceMatcher(None, nc, nt).ratio()
                if r < threshold:
                    continue
                score, how = r, f"相似 {r:.2f}（{t}）"
            if best is None or score > best[0]:
                best = (score, how)
    return best


def cmd_dup(name: str, wiki: Path, aliases: list[str], ptype: str, threshold: float, as_json: bool) -> int:
    pages = _node_pages(wiki)
    cands = [name, *aliases]
    same_type, cross_type = [], []
    for p in pages:
        m = _match(cands, p, threshold)
        if not m:
            continue
        row = {"score": round(m[0], 3), "how": m[1], **p}
        if ptype and p["type"] and p["type"] != ptype:
            cross_type.append(row)
        else:
            same_type.append(row)
    same_type.sort(key=lambda r: -r["score"])
    cross_type.sort(key=lambda r: -r["score"])
    if as_json:
        print(json.dumps({"candidate": name, "same_type": same_type, "cross_type": cross_type},
                         ensure_ascii=False, indent=1))
        return 0
    if same_type:
        print(f"[镜头D] 「{name}」撞车候选（同类型，建议走分支A合并论证；建新页须在 log 说明不合并理由）：")
        for r in same_type[:5]:
            print(f"    {r['score']:.2f} {r['path']} ← {r['how']}")
    else:
        print(f"[镜头D] 「{name}」无同类型撞车。")
    if cross_type:
        print("  跨类型提示（通常合法：来源页↔事件页等四界分建对，不算重复）：")
        for r in cross_type[:3]:
            print(f"    {r['score']:.2f} {r['path']} ← {r['how']}")
    return 0


def cmd_sweep(wiki: Path, threshold: float, include_sources: bool) -> int:
    pages = [p for p in _node_pages(wiki) if include_sources or p["type"] != "source"]
    pairs = []
    for i in range(len(pages)):
        for j in range(i + 1, len(pages)):
            a, b = pages[i], pages[j]
            if a["type"] != b["type"]:
                continue  # 跨类型不算重复（四界分建）
            m = _match([a["slug"], a["title"], *a["aliases"]], b, threshold)
            if m:
                pairs.append((round(m[0], 3), a["path"], b["path"], m[1]))
    pairs.sort(reverse=True)
    print(f"[镜头D·sweep] {len(pages)} 页（阈值 {threshold}）→ {len(pairs)} 对同类型近重复（t0-merge 候选，仅提示不拦截）：")
    for s, a, b, how in pairs[:20]:
        print(f"    {s:.2f}  {a}  ↔  {b}   ({how})")
    return 0


# ── 镜头 M：契约与出生戳检查（advisory，0.4.1 新增） ──────

def cmd_contract(target: Path) -> int:
    """引擎升级永不静默改契约（环 1a 自治），只在此提示实例主人来裁。"""
    sys.path.insert(0, str(HERE))
    import instance as _inst  # noqa: PLC0415
    cur = _inst.engine_version()
    wiki = target / "wiki" if (target / "wiki").is_dir() else target
    metas = sorted(wiki.glob("*/meta.yaml"))
    if not metas:
        print(f"[镜头M] {wiki} 下未发现任何域（meta.yaml）")
        return 0
    for mp in metas:
        try:
            m = yaml.safe_load(mp.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"✗ {mp.parent.name}: meta.yaml 解析失败 {e}")
            continue
        dom = m.get("name", mp.parent.name)
        notes = []
        born = str(m.get("born_of", "") or "")
        if not born:
            notes.append(("info", "无 born_of（出生早于 0.4.1）——建议补 `born_of: auto-wiki@pre-0.4.1`"))
        elif born != f"auto-wiki@{cur}":
            notes.append(("info", f"出生于 {born}，当前引擎 {cur}——版本间迁移要求见 ROADMAP 对应节"))
        onto = mp.parent / "_ontology.md"
        if onto.exists():
            t = onto.read_text(encoding="utf-8", errors="ignore")
            if "<填判据>" in t or "脚手架生成的占位表" in t:
                notes.append(("warn", "_ontology.md 仍是脚手架占位——首次 ingest 前必须填实类型判据表"))
            if "engine:" not in t:
                notes.append(("info", "契约无 engine: 机器可读块——0.5.0 词表真校验将要求，现阶段无需动作"))
        else:
            notes.append(("warn", "缺 _ontology.md 契约"))
        flag = "✗" if any(lv == "warn" for lv, _ in notes) else "·"
        print(f"{flag} {dom}（{born or '无出生戳'}）")
        for lv, msg in notes:
            print(f"    [{lv}] {msg}")
    print(f"\n[镜头M] {len(metas)} 域检查完毕（advisory 不拦截）")
    return 0


# ── policy 版本章 ─────────────────────────────────────────

def cmd_stamp() -> int:
    skill = HERE.parent / "SKILL.md"
    ver = "unknown"
    # 0.4.3 起版本在 metadata.version；仍兼容旧版顶层 version。
    m = re.search(r'(?m)^\s{0,2}version:\s*["\']?([\d.]+)', skill.read_text(encoding="utf-8")) if skill.exists() else None
    if m:
        ver = m.group(1)
    def sha8(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:8] if p.exists() else "missing"
    print(f"auto-wiki@{ver}·schema@{sha8(HERE / 'schema.py')}·precheck@{sha8(Path(__file__))}")
    return 0


# ── CLI ───────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="precheck", description="五试机审·机器镜头预检（advisory）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("page", help="镜头S：schema 预检")
    sp.add_argument("target")
    sp.add_argument("--strict", action="store_true")

    sd = sub.add_parser("dup", help="镜头D：候选名撞车检测")
    sd.add_argument("name")
    sd.add_argument("--wiki", required=True)
    sd.add_argument("--aliases", default="")
    sd.add_argument("--type", dest="ptype", default="")
    sd.add_argument("--threshold", type=float, default=0.75)
    sd.add_argument("--json", action="store_true")

    sw = sub.add_parser("sweep", help="镜头D：全库同类型近重复扫描")
    sw.add_argument("--wiki", required=True)
    sw.add_argument("--threshold", type=float, default=0.80)
    sw.add_argument("--include-sources", action="store_true")

    sc = sub.add_parser("contract", help="镜头M：契约/出生戳迁移检查")
    sc.add_argument("target")

    sub.add_parser("stamp", help="输出 policy 版本章")

    a = ap.parse_args(argv)
    if a.cmd == "page":
        return cmd_page(Path(a.target), a.strict)
    if a.cmd == "dup":
        aliases = [x.strip() for x in a.aliases.split(",") if x.strip()]
        return cmd_dup(a.name, Path(a.wiki), aliases, a.ptype, a.threshold, a.json)
    if a.cmd == "sweep":
        return cmd_sweep(Path(a.wiki), a.threshold, a.include_sources)
    if a.cmd == "contract":
        return cmd_contract(Path(a.target))
    if a.cmd == "stamp":
        return cmd_stamp()
    return 1


if __name__ == "__main__":
    sys.exit(main())
