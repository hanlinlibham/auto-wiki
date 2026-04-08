# Ingest Protocol

> Ingest is not appending files, it's compilation—read old, compare new, modify old.

## Flow

```
1. Read source file
   ├─ Extract key info: entities, concepts, data, conclusions, dates
   └─ Generate source summary page (sources/{date}-{slug}.md)

2. Search existing wiki
   ├─ Read index.md to get all page list
   ├─ Identify existing pages related to new info
   └─ Read current content of these pages

3. Compare old vs new page by page (core step)—three outcomes, must choose one
   │
   ├─ A) Reinforce: New info consistent with existing conclusion, provides additional evidence
   │   → Add new source slug to page sources list
   │   → If confidence is medium/low → raise to high
   │   → Body unchanged or only supplement details
   │   → log: "reinforced: {page}"
   │
   ├─ B) Update: New info clearly overturns or corrects existing conclusion (newer data/more authoritative source)
   │   → store.upsert_data() writes new value (old value auto-enters history table)
   │   → Rewrite Markdown body to new conclusion
   │   → Update frontmatter updated date and sources list
   │   → log: "updated: {page}, reason: {brief}"
   │
   └─ C) Conflict: New and old info contradict, but can't determine which is right (different data scope/equal source authority)
       → Don't rewrite, present both views in page, label respective sources
       → confidence → contested
       → log: "conflict: {page}, {view A} vs {view B}"
   
   Decision rule: New info has newer date or more authoritative source → B (Update);
   Both equal, can't determine superiority → C (Conflict); Others → A (Reinforce).

4. Structured data written to data.db
   ├─ Numeric data → store.upsert_data() (auto-handles history)
   ├─ Relations → store.add_relation()
   └─ Page metadata → store.upsert_page()

5. Create/update Markdown pages
   ├─ New entities/concepts → Create pages per wiki-format.md (frontmatter only stores metadata)
   ├─ Body writes narrative analysis, cites data conclusions but doesn't repeat specific values
   ├─ Add wikilinks to existing related pages
   └─ Add wikilink to new page in existing related pages

6. Update index.md
   ├─ Add new pages to corresponding group
   ├─ Update page count and Last updated date
   └─ Don't modify existing entry descriptions (unless page title changed)

7. Append log.md
   ├─ Record all operations of this ingest
   └─ Format see wiki-format.md
```

## Key Principles

**1. Modify old before creating new**

After searching wiki, found existing `entities/alpha-corp.md`, new report also mentions this institution → Update existing page, don't create `entities/alpha-corp-2.md`.

**2. Don't delete, only archive**

Outdated conclusions aren't deleted, moved to "## History" section. This preserves the evolution trace of knowledge.

```markdown
## Assets Under Management

By end of 2025, institution AUM reached XXX billion yuan. (Source: [[2026-04-06-policy-doc]])

## History

- ~~AUM approx XXX billion yuan~~ (Source: [[2024-12-annual-report]], superseded by updated data)
```

**3. Don't reconcile conflicts**

When two sources contradict, don't fabricate a compromise explanation. Present both, label sources, let user or subsequent evidence judge.

```markdown
## Market Share

> ⚠️ contested — Two sources have inconsistent data

- Per [[2026-04-06-policy-doc]]: Institution A market share approx 15%
- Per [[2025-annual-industry-report]]: Institution A market share approx 12%

Difference may come from different statistical scope.
```

**4. One ingest touching multiple pages is normal**

One research report may involve 5-10 entities and concepts. Updating 8 pages in one ingest is normal. Record fully in log.

**5. Source pages are immutable**

Summary pages in `sources/` directory aren't modified after creation (unless summary has errors). They're faithful records of original materials. Other pages reference them via `sources` frontmatter field.

---

## Worked Example: Complete Ingest Flow

> Using enterprise annuity domain as example. Replace with user's target domain in actual execution.

**Scenario**: User ingests a policy document into a domain wiki. Wiki already has related entity pages.

### Step 1 — Read source file, generate source summary page

Create `sources/2026-04-06-hrss-policy.md`:

```yaml
---
title: MOHRSS 2025 Annual Enterprise Annuity Fund Statistics Report
type: source
created: 2026-04-06
updated: 2026-04-06
sources: []
confidence: high
source_type: primary
source_origin: MOHRSS official website
source_date: 2025-12-31
---
```

Body writes faithful summary of key information from original text.

### Step 2 — Search existing wiki

Read index.md, find `entities/alpha-corp.md` related to new file. Query current data for this page in data.db:

```python
store.query_data(page_slug="alpha-corp")
# → [{ field: "assets_under_management", value: 800, unit: "billion yuan", period: "2024-12", source_slug: "2024-12-annual-report" }]
```

### Step 3 — Compare old vs new, determine result

New file says: "By end of 2025, institution AUM reached 1200 billion yuan."

Decision: New data is more recent (2025 vs 2024) → Choose **B) Update**.

Agent executes two operations:

**a) Structured data written to data.db** (auto-records history):

```python
old = store.upsert_data("alpha-corp", "assets_under_management", 1200, "billion yuan", "2025-12", "2026-04-06-policy-doc")
# old = { value: 800, unit: "billion yuan", source_slug: "2024-12-annual-report" }
# → history table auto-writes old value
store.add_relation("alpha-corp", "trustee_market_landscape", "part_of")
```

**b) Update Markdown page** (frontmatter only keeps metadata):

```yaml
---
title: Alpha Corp Pension Business
type: entity
created: 2026-04-01
updated: 2026-04-06
sources: [2024-12-annual-report, 2026-04-06-policy-doc]
confidence: high
relations:
  - target: trustee_market_landscape
    type: part_of
---
```

Body updates analysis content (cite data conclusions, don't write specific values—values are in data.db).

### Step 4-7 — Create pages, write to DB, update index, append log

New file also mentions "portable enterprise annuity" concept (not in wiki) → Create `concepts/portable-annuity.md`:

```yaml
---
title: Portable Enterprise Annuity
type: concept
created: 2026-04-06
updated: 2026-04-06
sources: [2026-04-06-hrss-policy]
confidence: medium  # Only single source first mention
relations:
  - target: enterprise_annuity_system
    type: part_of
---
```

log.md append:
```
## 2026-04-06 14:30 — ingest
- Source: 2026-04-06-policy-doc
- Updated: entities/alpha-corp (data.assets_under_management 800→1200 billion)
- Created: concepts/portable-annuity
- Conflicts: none
```
