# Wiki 扩容方案

> 零额外依赖——Python 3 自带 sqlite3 + FTS5。
>
> **本文档描述方案；执行用两个装好即用的脚本，不要照抄下面的片段：**
>
> | 用途 | 命令 |
> |---|---|
> | L1 重建分层索引（顶层 hub 瘦身 + 各类型 `_index.md`） | `python references/regen_index.py wiki/{domain}` |
> | 规模体检（不写盘，超阈值打 WARN；ingest 收尾调用） | `python references/regen_index.py wiki/{domain} --check` |
> | L2 建全文索引 | `python references/fts_index.py wiki/{domain} build` |
> | L2 检索（BM25 排序，可 `--type` 限定类型） | `python references/fts_index.py wiki/{domain} search "关键词"` |
>
> **为什么必须分层**：hub 若承载"每页一行"的全量清单，它随页面数线性增长，
> 而 recall/ingest 每次都整读它——上下文开销随库大小无上限膨胀。
> 实测：713 页的库，hub 达 104 KB / 700+ 行；分层后顶层降到约 2 KB。
> 新库由 `new_domain.py` 直接生成 L1 骨架，从第一天就没有这条膨胀路径。

## 三档检索策略

| 档位 | 页面数 | 检索方式 | 触发条件 |
|------|--------|---------|---------|
| L0 | < 50 | 读 hub + 相关类型 `_index.md` + 直接读页面 | 默认 |
| L1 | 50-500 | 分层索引（`regen_index.py`）+ grep 关键词 | 新库默认即为分层结构 |
| L2 | 500+ | SQLite FTS5 + BM25（`fts_index.py`） | 页面数 > 500（`--check` 会 WARN） |

---

## L1: 分层索引（50-500 页）

当页面数超过 50，hub 页面拆分为分层结构：

```
wiki/{domain}/
├── {领域中文名}.md       # 顶层 hub（只有分类摘要 + 链接到子索引）
├── 机构/  _index.md      # 机构子索引（该目录下所有页面的标题+一句话）
├── 工具/  _index.md      # 工具子索引
├── 指标/  _index.md      # 指标子索引
├── 机制/  _index.md      # 机制子索引
├── 事件/  _index.md      # 事件子索引
├── 分析/  _index.md      # 分析子索引
└── 来源/  _index.md      # 来源子索引
```

**顶层 hub 页面变为导航页**：

```markdown
# {领域中文名} Wiki Index

> 287 pages | Last updated: 2026-04-06

## Overview
- 机构: 12 → [机构/_index.md]
- 工具: 40 → [工具/_index.md]
- 指标: 60 → [指标/_index.md]
- 机制: 35 → [机制/_index.md]
- 事件: 50 → [事件/_index.md]
- 分析: 35 → [分析/_index.md]
- 来源: 55 → [来源/_index.md]

## 最近 ingest（最近 10 条）
- 2026-04-06: hrss-policy → 更新 8 页
- 2026-04-05: annual-report → 更新 5 页
...

## 高频实体 Top 10（被引用最多）
- [[alpha-corp]] (引用 23 次)
- [[national-council-ssf]] (引用 18 次)
...
```

Agent 查询时先读顶层 hub 页面定位分类，再读对应子索引定位具体页面，避免一次加载全部。

---

## L2: SQLite FTS5 索引（500+ 页）

### 原理

Wiki 页面（markdown）仍然是数据源头。SQLite 只是索引——丢了可以从页面重建。

```
wiki/{主题}/
├── search.db            # SQLite 索引文件（自动生成，可重建）
├── {主题中文名}.md       # 保留（给人浏览用）
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
python3 build_index.py wiki/enterprise-annuity/

# BM25 搜索
python3 search.py wiki/enterprise-annuity/search.db "受托人 市场份额"

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
| hub 页面超过 200 行 | 启用 L1 分层索引 |
| grep 搜索 > 5 秒 | 启用 L2 SQLite 索引 |
| 页面数 > 500 | 必须启用 L2 |
| 需要反向链接查询 | 启用 L2（links 表） |
| 需要 BM25 排序 | 启用 L2（FTS5） |
| 多用户协作 / 向量检索 | 超出 Skill 范围 → 迁移到外部平台 |

**升级是非破坏性的**——wiki 页面（markdown）不变，只是旁边多了一个 search.db。删掉 search.db，wiki 完整可用，只是退回 grep 检索。
