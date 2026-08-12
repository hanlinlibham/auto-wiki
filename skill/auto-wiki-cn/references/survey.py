#!/usr/bin/env python3
"""survey.py —— 存量勘察扫描器（survey 模式的确定性半边）

只读文件系统元数据反推知识结构：目录树、文件名、扩展名、修改时间。
默认**不打开任何文件**——用户的存量可能含敏感材料，零内容暴露才敢让人扫。

    python survey.py <目录> [<目录> ...]
    python survey.py <目录> --frontmatter    # 额外读 YAML 头（仍不读正文）
    python survey.py <目录> --json           # 结构化输出，给 Agent 消费
    python survey.py <目录> --top 12         # 收紧输出（默认 30）

计数一律由本脚本给出，Agent 不许自己数——数错的提案比没提案更坏。

**输出恒定**：所有分节都按 --top 截断，输出长度不随语料规模增长——扫 100 个
文件和扫 10 万个文件，报告都是一页。绝不打印文件清单，只打印聚合量。存量库
动辄上万文件，一次性灌进上下文就没有下一步了；要下钻就对**用户点名的那一个
子目录**重跑本脚本，不要一次扫全库再在上下文里筛。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

# 扫描时永远跳过的目录：版本控制、缓存、依赖、系统垃圾
SKIP_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", ".pytest_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", ".idea", ".vscode", ".trash",
    ".DS_Store", ".obsidian", ".stfolder", "$RECYCLE.BIN",
}
TEXT_EXT = {".md", ".markdown", ".txt", ".org", ".rst"}
# 文件名里的噪声词：日期、序号、通用后缀，不进高频词
NOISE = re.compile(r"^(?:\d+|v?\d+[\d.\-_]*|copy|副本|新建|未命名|untitled|final|最终)$", re.I)


def bucket_mtime(ts: float, now: float) -> str:
    days = (now - ts) / 86400
    if days <= 30:
        return "近30天"
    if days <= 90:
        return "31-90天"
    if days <= 365:
        return "91-365天"
    return "一年以上"


def ngrams(text: str, lo: int = 2, hi: int = 4):
    """中文按字 n-gram，英文按词。不引分词依赖。"""
    for token in re.findall(r"[A-Za-z][A-Za-z\-']+", text):
        if len(token) > 2 and not NOISE.match(token):
            yield token.lower()
    for run in re.findall(r"[一-鿿]+", text):
        for n in range(lo, hi + 1):
            for i in range(len(run) - n + 1):
                yield run[i:i + n]


def prune_substrings(counter: Counter, top: int) -> list[tuple[str, int]]:
    """去掉被更长高频词完全包含、且频次相近的碎片（"年金"vs"企业年金"）。"""
    items = [kv for kv in counter.most_common(top * 4) if kv[1] >= 2]
    kept: list[tuple[str, int]] = []
    for term, cnt in sorted(items, key=lambda kv: (-len(kv[0]), -kv[1])):
        # 被包含、或与已留词错位重叠一格（同一源片段的相邻 n-gram），且频次相近 → 丢
        if any(cnt <= c * 1.25 and (term in longer or term[1:] in longer or term[:-1] in longer)
               for longer, c in kept):
            continue
        kept.append((term, cnt))
    return sorted(kept, key=lambda kv: -kv[1])[:top]


def read_frontmatter_keys(path: Path) -> tuple[list[str], list[str]]:
    """只读 YAML 头的键，以及 tags 的值。不读正文——最多读到闭合的 '---'。"""
    keys: list[str] = []
    tags: list[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            if fh.readline().strip() != "---":
                return keys, tags
            for _ in range(60):                      # 头部最多看 60 行
                line = fh.readline()
                if not line or line.strip() == "---":
                    break
                m = re.match(r"^([A-Za-z_一-鿿][\w一-鿿\-]*):\s*(.*)$", line)
                if m:
                    keys.append(m.group(1))
                    if m.group(1).lower() in {"tags", "tag", "标签"}:
                        tags += re.findall(r"[\w一-鿿\-/]+", m.group(2))
    except OSError:
        pass
    return keys, tags


def scan(roots: list[Path], want_frontmatter: bool, top: int = 30) -> dict:
    now = time.time()
    files: list[dict] = []
    tree: Counter = Counter()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            here = Path(dirpath)
            rel_dir = here.relative_to(root)
            for name in filenames:
                if name.startswith("."):
                    continue
                p = here / name
                try:
                    st = p.stat()
                except OSError:
                    continue
                files.append({
                    "root": str(root),
                    "dir": str(rel_dir) if str(rel_dir) != "." else "",
                    "stem": p.stem,
                    "ext": p.suffix.lower(),
                    "mtime": st.st_mtime,
                    "size": st.st_size,
                    "path": p,
                })
            if str(rel_dir) != ".":
                tree[f"{root.name}/{rel_dir}"] += len(filenames)

    text_files = [f for f in files if f["ext"] in TEXT_EXT]
    name_terms: Counter = Counter()
    for f in files:
        name_terms.update(set(ngrams(f["stem"])))

    dir_terms: Counter = Counter()
    for f in files:
        for part in Path(f["dir"]).parts:
            dir_terms[part] += 1

    fm_keys: Counter = Counter()
    fm_tags: Counter = Counter()
    if want_frontmatter:
        for f in text_files:
            keys, tags = read_frontmatter_keys(f["path"])
            fm_keys.update(set(keys))
            fm_tags.update(tags)

    return {
        "roots": [str(r) for r in roots],
        "total_files": len(files),
        "text_files": len(text_files),
        "tree": tree.most_common(top),
        "dirs": dir_terms.most_common(top),
        "ext": Counter(f["ext"] or "<无后缀>" for f in files).most_common(min(top, 15)),
        "mtime": Counter(bucket_mtime(f["mtime"], now) for f in files),
        "recent": [f["stem"] for f in sorted(text_files, key=lambda f: -f["mtime"])[:min(top, 15)]],
        "name_terms": prune_substrings(name_terms, top),
        "fm_keys": fm_keys.most_common(min(top, 20)),
        "fm_tags": fm_tags.most_common(top),
        "scanned_frontmatter": want_frontmatter,
        "top": top,
    }


def render(r: dict) -> str:
    out: list[str] = []
    add = out.append
    add("=" * 60)
    add(f"存量勘察：{', '.join(r['roots'])}")
    add("=" * 60)
    add(f"文件 {r['total_files']} 个（文本类 {r['text_files']}）"
        f"{'  · 已读 YAML 头' if r['scanned_frontmatter'] else '  · 未打开任何文件'}")
    if r["total_files"] > 3000:
        add("⚠ 语料很大。本报告已按 top 截断、长度恒定；下钻请对单个子目录重跑，"
            "不要把全库塞进上下文。")

    add("\n【目录结构】用户自己的分类学，是节点类型的第一候选")
    for path, n in r["tree"][:r["top"]]:
        add(f"  {n:>5}  {path}/")
    if r["dirs"]:
        add("  高频目录名：" + "、".join(f"{d}({n})" for d, n in r["dirs"][:min(r["top"], 12)]))

    add("\n【文件名高频词】路由关键词与中心对象的候选")
    add(("  " + "、".join(f"{t}({n})" for t, n in r["name_terms"])) if r["name_terms"] else "  （无）")

    add("\n【修改时间分布】判断哪些是动态知识、哪些是稳定知识")
    for b in ("近30天", "31-90天", "91-365天", "一年以上"):
        if r["mtime"].get(b):
            add(f"  {b:<10} {r['mtime'][b]:>5} 个")
    if r["recent"]:
        add("  最近改动：" + "、".join(r["recent"][:8]))

    add("\n【文件类型】")
    add("  " + "、".join(f"{e} {n}" for e, n in r["ext"][:10]))

    if r["scanned_frontmatter"]:
        add("\n【frontmatter】")
        add("  键：" + ("、".join(f"{k}({n})" for k, n in r["fm_keys"][:12]) or "无"))
        add("  标签：" + ("、".join(f"{t}({n})" for t, n in r["fm_tags"][:20]) or "无"))

    add("\n" + "-" * 60)
    add("以上全部来自文件系统元数据。禁混规则挖不到——那只能问人（见 survey-protocol.md Phase 3）。")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="存量勘察：只读结构反推知识库骨架")
    ap.add_argument("dirs", nargs="+", help="要勘察的目录（用户圈定，不自行往上层走）")
    ap.add_argument("--frontmatter", action="store_true", help="额外读 YAML 头的键与标签（仍不读正文）")
    ap.add_argument("--json", action="store_true", help="输出 JSON，给 Agent 消费")
    ap.add_argument("--top", type=int, default=30, help="每节最多列几项（默认 30，收紧上下文用）")
    args = ap.parse_args()

    roots = []
    for d in args.dirs:
        p = Path(d).expanduser().resolve()
        if not p.is_dir():
            print(f"✗ 不是目录：{p}", file=sys.stderr)
            return 1
        roots.append(p)

    result = scan(roots, args.frontmatter, args.top)
    if args.json:
        result.pop("mtime_raw", None)
        result["mtime"] = dict(result["mtime"])
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
