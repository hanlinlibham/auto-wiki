# Wiki Scaling Plan

> The default mode (grep + hub page) works for < 500 pages. Beyond that, enable the SQLite index layer.
> Zero extra dependencies — Python 3 ships with sqlite3 + FTS5.

## Three-Tier Retrieval Strategy

| Tier | Page Count | Retrieval Method | Trigger |
|------|------------|------------------|---------|
| L0 | < 50 | Read hub page + read pages directly | Default |
| L1 | 50-500 | Layered hub pages + grep keywords | Auto-switch when pages > 50 |
| L2 | 500+ | SQLite FTS5 + BM25 ranking | Pages > 500 or user enables manually |

---

## L1: Layered Index (50-500 pages)

When the page count exceeds 50, the hub page splits into a layered structure:

```
wiki/{domain}/
├── {Domain Name}.md           # Top-level hub (category summaries + links to sub-indexes only)
├── institutions/  _index.md   # Institutions sub-index (title + one-liner for every page in the directory)
├── instruments/   _index.md   # Instruments sub-index
├── indicators/    _index.md   # Indicators sub-index
├── mechanisms/    _index.md   # Mechanisms sub-index
├── events/        _index.md   # Events sub-index
├── analyses/      _index.md   # Analyses sub-index
└── sources/       _index.md   # Sources sub-index
```

**The top-level hub page becomes a navigation page**:

```markdown
# {Domain Name} Wiki Index

> 287 pages | Last updated: 2026-04-06

## Overview
- Institutions: 12 → [institutions/_index.md]
- Instruments: 40 → [instruments/_index.md]
- Indicators: 60 → [indicators/_index.md]
- Mechanisms: 35 → [mechanisms/_index.md]
- Events: 50 → [events/_index.md]
- Analyses: 35 → [analyses/_index.md]
- Sources: 55 → [sources/_index.md]

## Recent ingest (last 10)
- 2026-04-06: policy-doc → updated 8 pages
- 2026-04-05: annual-report → updated 5 pages
...

## Top 10 high-frequency entities (most referenced)
- [[alpha-corp]] (23 references)
- [[CalPERS]] (18 references)
...
```

When querying, the Agent first reads the top-level hub page to locate the category, then reads the corresponding sub-index to locate the specific pages — avoiding loading everything at once.

---

## L2: SQLite FTS5 Index (500+ pages)

### Principle

The wiki pages (markdown) remain the source of truth. SQLite is only an index — if lost, it can be rebuilt from the pages.

```
wiki/{topic}/
├── search.db            # SQLite index file (auto-generated, rebuildable)
├── {Domain Name}.md     # Kept (for human browsing)
├── meta.yaml
└── ...
```

### Schema

```sql
-- Pages table
CREATE TABLE pages (
    slug TEXT PRIMARY KEY,        -- Filename (without .md)
    type TEXT NOT NULL,           -- source/entity/concept/analysis
    title TEXT NOT NULL,
    content TEXT NOT NULL,         -- Full body text
    confidence TEXT DEFAULT 'high',
    created TEXT,
    updated TEXT,
    sources TEXT                   -- JSON array of source slugs
);

-- FTS5 full-text index (built-in BM25 ranking)
CREATE VIRTUAL TABLE pages_fts USING fts5(
    title,
    content,
    content='pages',
    content_rowid='rowid',
    tokenize='unicode61'          -- Unicode-aware tokenization
);

-- Wikilink relation table
CREATE TABLE links (
    from_slug TEXT NOT NULL,
    to_slug TEXT NOT NULL,
    PRIMARY KEY (from_slug, to_slug)
);

-- Trigger: keep the FTS index updated when pages change
CREATE TRIGGER pages_ai AFTER INSERT ON pages BEGIN
    INSERT INTO pages_fts(rowid, title, content)
    VALUES (new.rowid, new.title, new.content);
END;
```

### Index Build Script

The Agent runs this automatically after ingest completes (if search.db exists):

```python
#!/usr/bin/env python3
"""Rebuild the SQLite FTS5 index from wiki markdown files."""
import sqlite3, os, re, json, yaml
from pathlib import Path

def parse_page(path):
    """Parse a markdown page, extracting frontmatter and body."""
    text = path.read_text(encoding='utf-8')
    if text.startswith('---'):
        _, fm, body = text.split('---', 2)
        meta = yaml.safe_load(fm)
        return meta, body.strip()
    return {}, text

def extract_links(content):
    """Extract [[wikilink]]s."""
    return re.findall(r'\[\[([^\]]+)\]\]', content)

def build_index(wiki_dir):
    db_path = wiki_dir / 'search.db'
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    # Create tables (if they don't exist)
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

    # Clear and rebuild
    c.execute('DELETE FROM pages')
    c.execute('DELETE FROM links')
    c.execute("INSERT INTO pages_fts(pages_fts) VALUES('delete-all')")

    # Traverse all md files
    for subdir in ['institutions', 'instruments', 'indicators', 'mechanisms', 'events', 'analyses', 'sources']:
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

    # Rebuild FTS
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

### Querying

In the query operation, the Agent queries SQLite via Python:

```python
#!/usr/bin/env python3
"""BM25 search over wiki pages."""
import sqlite3, sys, json

def search(db_path, query, limit=10):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # BM25 ranking: built into FTS5; the smaller the rank, the more relevant
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

**Usage example**:

```bash
# Build the index
python3 build_index.py wiki/enterprise-annuity/

# BM25 search
python3 search.py wiki/enterprise-annuity/search.db "trustee market share"

# Output
# [entity] Alpha Corp Pension Business (alpha-corp) confidence=high rank=-3.42
#   ...trustee >>>market share<<< approx 15%...
# [analysis] Trustee Market Landscape Comparison (trustee-market-comparison) confidence=high rank=-2.87
#   ...each >>>trustee<<<'s >>>market share<<< shift...
```

### Backlink Queries

```sql
-- Who references alpha-corp?
SELECT from_slug FROM links WHERE to_slug = 'alpha-corp';

-- Whom does alpha-corp reference?
SELECT to_slug FROM links WHERE from_slug = 'alpha-corp';

-- Most isolated pages (fewest incoming links)
SELECT p.slug, p.title, COUNT(l.from_slug) as inlinks
FROM pages p
LEFT JOIN links l ON l.to_slug = p.slug
GROUP BY p.slug
ORDER BY inlinks ASC
LIMIT 10;

-- Most central pages (most referenced)
SELECT p.slug, p.title, COUNT(l.from_slug) as inlinks
FROM pages p
LEFT JOIN links l ON l.to_slug = p.slug
GROUP BY p.slug
ORDER BY inlinks DESC
LIMIT 10;
```

### Lint Enhancement

In L2 mode, lint can run efficiently via SQL:

```sql
-- Find contested pages
SELECT slug, title FROM pages WHERE confidence = 'contested';

-- Find orphans (no incoming links + not source type)
SELECT p.slug, p.title FROM pages p
LEFT JOIN links l ON l.to_slug = p.slug
WHERE l.from_slug IS NULL AND p.type != 'source';

-- Find broken links (wikilink target doesn't exist)
SELECT l.from_slug, l.to_slug FROM links l
LEFT JOIN pages p ON p.slug = l.to_slug
WHERE p.slug IS NULL;

-- Find stale pages (no update in 6 months + low confidence)
SELECT slug, title, updated, confidence FROM pages
WHERE updated < date('now', '-6 months')
AND confidence IN ('low', 'medium');

-- Coverage stats
SELECT type, COUNT(*) as count,
       SUM(CASE WHEN confidence = 'contested' THEN 1 ELSE 0 END) as contested
FROM pages GROUP BY type;
```

---

## When to Upgrade

| Signal | Recommendation |
|--------|----------------|
| Hub page exceeds 200 lines | Enable L1 layered index |
| grep search > 5 seconds | Enable L2 SQLite index |
| Page count > 500 | L2 is mandatory |
| Backlink queries needed | Enable L2 (links table) |
| BM25 ranking needed | Enable L2 (FTS5) |
| Multi-user collaboration / vector retrieval | Beyond Skill scope → migrate to an external platform |

**Upgrades are non-destructive** — the wiki pages (markdown) stay unchanged; only a search.db appears alongside them. Delete search.db and the wiki remains fully usable, just falling back to grep retrieval.
