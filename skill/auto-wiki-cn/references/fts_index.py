#!/usr/bin/env python3
"""L2 全文索引 —— SQLite FTS5 + BM25，零额外依赖（Python 自带 sqlite3）。

为什么存在：页面数过 500 后，靠"读索引 + grep"定位既慢又费上下文。
本脚本把正文建成独立的 search.db（与 data.db 分开，随时可删可重建），
检索只回"命中哪几页 + 一段摘要"，让上下文开销与库大小解耦。

用法：
    python fts_index.py wiki/reading build              # 建/重建索引
    python fts_index.py wiki/reading search "系统1 直觉"  # BM25 排序检索
    python fts_index.py wiki/reading search "CPO" --type 机制 --limit 5
    python fts_index.py wiki/reading stat               # 索引状态

中文分词：用 unicode61 并按字切分（trigram 需 SQLite 3.34+，不强求）。
中文按字建索引后，BM25 对多字词依然有效——检索词内部空格分隔即可。
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path

SKIP_STEMS = {"_index", "_ontology", "log", "meta", "_report"}
DB_NAME = "search.db"


def cjk_segment(text: str) -> str:
    """CJK 按字切开、拉丁词保留整体——unicode61 才能索引到中文。"""
    out = []
    for ch in text:
        if "一" <= ch <= "鿿" or "぀" <= ch <= "ヿ":
            out.append(f" {ch} ")
        else:
            out.append(ch)
    return "".join(out)


CJK = lambda ch: "\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff"


def desegment(text: str) -> str:
    """展示层还原：去掉建索引时插进 CJK 之间的空格，摘要才是人话。"""
    out = []
    for ch in text:
        if ch == " " and out and CJK(out[-1]):
            continue
        out.append(ch)
    return "".join(out).strip()


def strip_md(text: str) -> tuple[str, str]:
    """剥掉 frontmatter，返回 (title, 正文纯文本)。"""
    title = ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if line.strip().startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip("'\"")
            text = text[end + 4 :]
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", text)
    text = re.sub(r"[#>*`|\-]{1,}", " ", text)
    return title, re.sub(r"\s+", " ", text).strip()


def connect(ddir: Path) -> sqlite3.Connection:
    return sqlite3.connect(str(ddir / DB_NAME))


def build(ddir: Path) -> int:
    conn = connect(ddir)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS pages_fts")
    cur.execute(
        "CREATE VIRTUAL TABLE pages_fts USING fts5("
        "slug UNINDEXED, ptype UNINDEXED, title, body, tokenize='unicode61')"
    )
    n = 0
    for md in sorted(ddir.rglob("*.md")):
        if md.stem in SKIP_STEMS or md.parent == ddir:
            continue
        try:
            raw = md.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  ! 跳过 {md}: {e}", file=sys.stderr)
            continue
        title, body = strip_md(raw)
        cur.execute(
            "INSERT INTO pages_fts (slug, ptype, title, body) VALUES (?,?,?,?)",
            (md.stem, md.parent.name, cjk_segment(title or md.stem), cjk_segment(body)),
        )
        n += 1
    conn.commit()
    conn.close()
    print(f"✓ 已索引 {n} 页 → {ddir / DB_NAME}")
    return n


def search(ddir: Path, query: str, ptype: str | None, limit: int) -> None:
    db = ddir / DB_NAME
    if not db.exists():
        print(f"✗ 索引不存在，先跑：python fts_index.py {ddir} build", file=sys.stderr)
        sys.exit(1)
    terms = [cjk_segment(t).strip() for t in query.split() if t.strip()]
    if not terms:
        print("✗ 检索词为空", file=sys.stderr)
        sys.exit(1)
    match = " AND ".join(f'"{t}"' for t in terms)
    conn = connect(ddir)
    sql = (
        "SELECT slug, ptype, snippet(pages_fts, 3, '《', '》', '…', 12), bm25(pages_fts) AS r "
        "FROM pages_fts WHERE pages_fts MATCH ?"
    )
    params: list = [match]
    if ptype:
        sql += " AND ptype = ?"
        params.append(ptype)
    sql += " ORDER BY r LIMIT ?"
    params.append(limit)
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        print(f"✗ 检索失败：{e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()
    if not rows:
        print("（无命中）——查不到就明说，不要猜；必要时登记 query-miss")
        return
    for slug, pt, snip, r in rows:
        print(f"[{pt}] {slug}   rank={r:.3f}")
        print(f"    {desegment(snip)}")


def stat(ddir: Path) -> None:
    db = ddir / DB_NAME
    if not db.exists():
        print("索引未建立")
        return
    conn = connect(ddir)
    n = conn.execute("SELECT count(*) FROM pages_fts").fetchone()[0]
    conn.close()
    print(f"{db}：{n} 页 · {db.stat().st_size / 1024:.1f} KB")


def main() -> int:
    ap = argparse.ArgumentParser(description="L2 全文索引（FTS5 + BM25）")
    ap.add_argument("domain_dir", help="领域目录，如 wiki/reading")
    ap.add_argument("cmd", choices=["build", "search", "stat"])
    ap.add_argument("query", nargs="?", default="", help="检索词（空格分隔，AND 关系）")
    ap.add_argument("--type", dest="ptype", default=None, help="限定类型目录，如 机制")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    ddir = Path(args.domain_dir)
    if not ddir.is_dir():
        print(f"✗ 目录不存在：{ddir}", file=sys.stderr)
        return 1
    if args.cmd == "build":
        build(ddir)
    elif args.cmd == "stat":
        stat(ddir)
    else:
        search(ddir, args.query, args.ptype, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
