# Wiki 扩容方案

> 默认模式（grep + index.md）适用于 < 500 页。超过后启用 SQLite 索引层。
> 零额外依赖——Python 3 自带 sqlite3 + FTS5。

## 三档检索策略

| 档位 | 页面数 | 检索方式 | 触发条件 |
|------|--------|---------|---------|
| L0 | < 50 | 读 index.md + 直接读页面 | 默认 |
| L1 | 50-500 | 分层 index + grep 关键词 | 页面数 > 50 时自动切换 |
| L2 | 500+ | SQLite FTS5 + BM25 排序 | 页面数 > 500 或用户手动启用 |

---

## L1: 分层索引（50-500 页）

当页面数超过 50，index.md 拆分为分层结构：

```
.wiki/{主题}/
├── index.md              # 顶层索引（只有分类摘要 + 链接到子索引）
├── entities/
│   └── _index.md         # 实体子索引（该目录下所有页面的标题+一句话）
├── concepts/
│   └── _index.md         # 概念子索引
├── sources/
│   └── _index.md         # 源文件子索引
└── analyses/
    └── _index.md         # 分析子索引
```

**顶层 index.md 变为导航页**：

```markdown
# {主题} Wiki Index

> 287 pages | Last updated: 2026-04-06

## Overview
- Sources: 45 篇 → [sources/_index.md]
- Entities: 120 个 → [entities/_index.md]
- Concepts: 87 个 → [concepts/_index.md]
- Analyses: 35 篇 → [analyses/_index.md]

## 最近 ingest（最近 10 条）
- 2026-04-06: hrss-policy → 更新 8 页
- 2026-04-05: annual-report → 更新 5 页
...

## 高频实体 Top 10（被引用最多）
- [[alpha-corp]] (引用 23 次)
- [[national-council-ssf]] (引用 18 次)
...
```

Agent 查询时先读顶层 index 定位分类，再读对应子索引定位具体页面，避免一次加载全部。

---

## L2: SQLite FTS5 索引（500+ 页）

### 原理

Wiki 页面（markdown）仍然是数据源头。SQLite 只是索引——丢了可以从页面重建。

```
.wiki/{主题}/
├── search.db            # SQLite 索引文件（自动生成，可重建）
├── index.md             # 保留（给人浏览用）
├── meta.yaml
└── ...
```

### Schema

```sql
-- 页面表
CREATE TABLE pages (
    slug TEXT PRIMARY KEY,        -- 文件名（去 .md）
    type TEXT NOT NULL,           -- source/entity/concept/analysis
    title TEXT NOT NULL,
    content TEXT NOT NULL,         -- 正文全文
    confidence TEXT DEFAULT 'high',
    created TEXT,
    updated TEXT,
    sources TEXT                   -- JSON array of source slugs
);

-- FTS5 全文索引（内置 BM25 排名）
CREATE VIRTUAL TABLE pages_fts USING fts5(
    title,
    content,
    content='pages',
    content_rowid='rowid',
    tokenize='unicode61'          -- 支持中文分词
);

-- Wikilink 关系表
CREATE TABLE links (
    from_slug TEXT NOT NULL,
    to_slug TEXT NOT NULL,
    PRIMARY KEY (from_slug, to_slug)
);

-- 触发器：pages 变化时自动更新 FTS 索引
CREATE TRIGGER pages_ai AFTER INSERT ON pages BEGIN
    INSERT INTO pages_fts(rowid, title, content)
    VALUES (new.rowid, new.title, new.content);
END;
```

### 建索引脚本

Agent 在 ingest 完成后自动执行（如果 search.db 存在）：

```python
#!/usr/bin/env python3
"""从 wiki markdown 文件重建 SQLite FTS5 索引。"""
import sqlite3, os, re, json, yaml
from pathlib import Path

def parse_page(path):
    """解析 markdown 页面，提取 frontmatter 和正文。"""
    text = path.read_text(encoding='utf-8')
    if text.startswith('---'):
        _, fm, body = text.split('---', 2)
        meta = yaml.safe_load(fm)
        return meta, body.strip()
    return {}, text

def extract_links(content):
    """提取 [[wikilink]]。"""
    return re.findall(r'\[\[([^\]]+)\]\]', content)

def build_index(wiki_dir):
    db_path = wiki_dir / 'search.db'
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    # 建表（如果不存在）
    c.executescript('''
        CREATE TABLE IF NOT EXISTS pages (
            slug TEXT PRIMARY KEY, type TEXT, title TEXT,
            content TEXT, confidence TEXT, created TEXT,
            updated TEXT, sources TEXT
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
            title, content, content='pages', content_rowid='rowid',
            tokenize='unicode61'
        );
        CREATE TABLE IF NOT EXISTS links (
            from_slug TEXT, to_slug TEXT,
            PRIMARY KEY (from_slug, to_slug)
        );
    ''')

    # 清空重建
    c.execute('DELETE FROM pages')
    c.execute('DELETE FROM links')
    c.execute("INSERT INTO pages_fts(pages_fts) VALUES('delete-all')")

    # 遍历所有 md 文件
    for subdir in ['sources', 'entities', 'concepts', 'analyses']:
        dir_path = wiki_dir / subdir
        if not dir_path.exists():
            continue
        for f in dir_path.glob('*.md'):
            if f.name.startswith('_'):
                continue
            slug = f.stem
            meta, body = parse_page(f)
            c.execute(
                'INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?,?)',
                (slug, meta.get('type',''), meta.get('title',''),
                 body, meta.get('confidence','high'),
                 meta.get('created',''), meta.get('updated',''),
                 json.dumps(meta.get('sources',[])))
            )
            for link in extract_links(body):
                c.execute('INSERT OR IGNORE INTO links VALUES (?,?)', (slug, link))

    # 重建 FTS
    c.execute("INSERT INTO pages_fts(pages_fts) VALUES('rebuild')")

    conn.commit()
    count = c.execute('SELECT COUNT(*) FROM pages').fetchone()[0]
    conn.close()
    return count

if __name__ == '__main__':
    import sys
    wiki_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    n = build_index(wiki_dir)
    print(f'Indexed {n} pages → {wiki_dir}/search.db')
```

### 查询方式

Agent 在 query 操作中，用 Python 查询 SQLite：

```python
#!/usr/bin/env python3
"""BM25 搜索 wiki 页面。"""
import sqlite3, sys, json

def search(db_path, query, limit=10):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # BM25 排序：FTS5 内置，rank 越小越相关
    results = c.execute('''
        SELECT p.slug, p.type, p.title, p.confidence,
               snippet(pages_fts, 1, '>>>', '<<<', '...', 30) as snippet,
               rank
        FROM pages_fts
        JOIN pages p ON pages_fts.rowid = p.rowid
        WHERE pages_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    ''', (query, limit)).fetchall()
    conn.close()
    return results

if __name__ == '__main__':
    db = sys.argv[1]
    q = sys.argv[2]
    for slug, type_, title, conf, snippet, rank in search(db, q):
        print(f'[{type_}] {title} ({slug}) confidence={conf} rank={rank:.2f}')
        print(f'  {snippet}')
        print()
```

**使用示例**：

```bash
# 建索引
python3 build_index.py .wiki/enterprise-annuity/

# BM25 搜索
python3 search.py .wiki/enterprise-annuity/search.db "受托人 市场份额"

# 输出
# [entity] Alpha Corp 养老金业务 (alpha-corp) confidence=high rank=-3.42
#   ...受托人>>>市场份额<<<约 15%...
# [analysis] 受托人市场格局对比 (trustee-market-comparison) confidence=high rank=-2.87
#   ...各>>>受托人<<<的>>>市场份额<<<变化...
```

### 反向链接查询

```sql
-- 谁引用了 alpha-corp？
SELECT from_slug FROM links WHERE to_slug = 'alpha-corp';

-- alpha-corp 引用了谁？
SELECT to_slug FROM links WHERE from_slug = 'alpha-corp';

-- 最孤立的页面（入链最少）
SELECT p.slug, p.title, COUNT(l.from_slug) as inlinks
FROM pages p
LEFT JOIN links l ON l.to_slug = p.slug
GROUP BY p.slug
ORDER BY inlinks ASC
LIMIT 10;

-- 最核心的页面（被引用最多）
SELECT p.slug, p.title, COUNT(l.from_slug) as inlinks
FROM pages p
LEFT JOIN links l ON l.to_slug = p.slug
GROUP BY p.slug
ORDER BY inlinks DESC
LIMIT 10;
```

### lint 增强

L2 模式下，lint 可以用 SQL 高效执行：

```sql
-- 找 contested 页面
SELECT slug, title FROM pages WHERE confidence = 'contested';

-- 找孤页（无入链 + 非 source 类型）
SELECT p.slug, p.title FROM pages p
LEFT JOIN links l ON l.to_slug = p.slug
WHERE l.from_slug IS NULL AND p.type != 'source';

-- 找断链（wikilink 目标不存在）
SELECT l.from_slug, l.to_slug FROM links l
LEFT JOIN pages p ON p.slug = l.to_slug
WHERE p.slug IS NULL;

-- 找过时页面（6 个月未更新 + 低置信度）
SELECT slug, title, updated, confidence FROM pages
WHERE updated < date('now', '-6 months')
AND confidence IN ('low', 'medium');

-- 统计 coverage
SELECT type, COUNT(*) as count,
       SUM(CASE WHEN confidence = 'contested' THEN 1 ELSE 0 END) as contested
FROM pages GROUP BY type;
```

---

## 何时升级

| 信号 | 建议 |
|------|------|
| index.md 超过 200 行 | 启用 L1 分层索引 |
| grep 搜索 > 5 秒 | 启用 L2 SQLite 索引 |
| 页面数 > 500 | 必须启用 L2 |
| 需要反向链接查询 | 启用 L2（links 表） |
| 需要 BM25 排序 | 启用 L2（FTS5） |
| 多用户协作 / 向量检索 | 超出 Skill 范围 → 迁移到外部平台 |

**升级是非破坏性的**——wiki 页面（markdown）不变，只是旁边多了一个 search.db。删掉 search.db，wiki 完整可用，只是退回 grep 检索。
