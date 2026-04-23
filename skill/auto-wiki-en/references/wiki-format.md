# Wiki Page Format

> **All frontmatter structures are defined and validated by Pydantic models in `schema.py`.**
> This document is human-readable specification; `schema.py` is machine-executable validation tool. Both must be consistent.
> Validation command: `python references/schema.py .wiki/{topic}/`

## Directory Structure

One directory per research topic:

```
{topic_name}/
├── meta.yaml         # Wiki metadata (see storage-spec.md)
├── index.md          # Page index (Agent maintained, grouped by type)
├── log.md            # Operation log (append-only, human-readable)
├── sources/          # Source file summaries
├── entities/         # Entity pages (institutions, people, products)
├── concepts/         # Concept pages (systems, methods, metrics)
└── analyses/         # Analysis archive (valuable analyses from query)
```

cognitive type wiki directory variant:
```
{person_name}/
├── mental-models/    # Replaces entities/—one page per mental model
├── concepts/         # Heuristics, values, expression styles, tensions
├── sources/          # Collection sources
└── analyses/         # Analysis archive
```

## Page Format

Each page has two parts: **YAML frontmatter (structured data)** + **Markdown body (narrative analysis)**.

**Core principle: Data goes in YAML, analysis goes in body.** Body doesn't write data tables.

---

## Frontmatter Schema

### Base Fields (Required for all pages)

```yaml
---
title: Page Title
type: entity                    # entity | concept | source | analysis | mental-model
created: 2026-04-06
updated: 2026-04-06
sources: [source-slug-1, source-slug-2]
confidence: high                # high | medium | low | contested
tags: [entity]                  # Required: page type + optional status tags
aliases: []                     # Optional: page aliases
---
```

| Field | Required | Description |
|-------|----------|-------------|
| title | Yes | Page title |
| type | Yes | Page type |
| created | Yes | Creation date YYYY-MM-DD |
| updated | Yes | Last update date (must update on each change) |
| sources | Yes | List of referenced source page slugs (source type pages fill `[]`) |
| confidence | Yes | Confidence: `high` / `medium` / `low` / `contested` |
| tags | Yes | Obsidian tag list for search filtering and categorized browsing |
| aliases | No | Page alias list for Obsidian search and link completion |

### tags Rules (required for Obsidian search filtering)

`tags` must include the page type (`source` / `entity` / `concept` / `analysis` / `mental-model`), with optional status tags:

```yaml
tags:
  - concept                    # Required: page type
  - contested                  # Optional: when confidence=contested
  - low-confidence             # Optional: when confidence=low
```

Source type pages add source grade tags:

```yaml
tags:
  - source
  - primary-source             # Primary source
  # Or authoritative-secondary / secondary / hearsay / inference
```

These tags are for Obsidian search filtering (e.g., type `tag:#contested` in search bar to locate disputed pages). Graph coloring does NOT rely on tags — it uses `path:` rules for page type coloring and `[confidence:contested]` Properties query for risk node highlighting.

### aliases Rules

When title contains parenthetical explanations, split out the short name and parenthetical content as aliases:

```yaml
title: EET Tax Model (Personal Pension Tax Incentive)
aliases:
  - EET Tax Model
  - Personal Pension Tax Incentive
```

### Structured Data → data.db

**All quantifiable, verifiable, comparable data is written to `data.db` (SQLite), not placed in frontmatter.**

Agent calls `store.py`'s `WikiStore` interface during ingest:

```python
store.upsert_data("alpha-corp", "assets_under_management", 1350, "billion yuan", "2025-Q1", "2026-04-policy-doc", scope="including occupational annuity")
store.upsert_data("alpha-corp", "market_share", 12, "%", "2025-Q1", "2026-04-policy-doc", confidence="contested")
```

If same field same period already has old value, `upsert_data` automatically writes old value to `history` table and returns old record.

**Data field specification** (constrained by `store.py: data_points` table):

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `page_slug` | **Yes** | TEXT | Slug of owning page |
| `field` | **Yes** | TEXT | Data dimension name (e.g., "assets_under_management") |
| `value` | **Yes** | REAL | Numeric value |
| `unit` | **Yes** | TEXT | Unit (billion yuan, %, 10k people, count...) |
| `period` | **Yes** | TEXT | Data timepoint (e.g., "2023-12", "2025-Q1") |
| `source_slug` | **Yes** | TEXT | Source page slug |
| `scope` | No | TEXT | Statistical scope description |
| `verified` | No | INTEGER | NULL=unknown, 0=unverified, 1=verified |
| `confidence` | No | TEXT | This data point's confidence |

**Every number must have provenance.** `source_slug` points to which source page.

**Query examples**:

```python
# All data for an institution
store.query_data(page_slug="alpha-corp")

# Timeline for a field (including historical values)
store.query_timeline(field="assets_under_management")

# All contested data
store.conn.execute("SELECT * FROM data_points WHERE confidence='contested'").fetchall()
```

### relations Field (Structured Relationships)

Semantic relationships between pages, supplementing `[[wikilink]]` in body:

```yaml
relations:
  - target: beta-corp
    type: competes_with
  - target: trustee_market_landscape
    type: part_of
  - target: national_council_ssf
    type: regulated_by
```

**Common relationship types**:

| type | Meaning | Example |
|------|---------|---------|
| `part_of` | Part of | Institution A part_of trustee market |
| `manages` | Manages | Trustee manages annuity fund |
| `regulated_by` | Regulated by | Institution regulated_by MOHRSS |
| `competes_with` | Competes with | Institution A competes_with Institution B |
| `implements` | Implements | Institution implements fiduciary duty |
| `derived_from` | Derived from | Concept B derived_from Concept A |
| `contradicts` | Contradicts | Data A contradicts Data B |
| `influenced_by` | Influenced by (cognitive type) | Mental model influenced_by person |
| `applies_to` | Applies to | Mental model applies_to domain |

**relations specification**:
- `target` fills slug (no path prefix)
- `type` select from table above, or custom (but keep consistent within project)
- relations are structured declarations in frontmatter, `[[wikilink]]` in body is human-readable reference—both complement each other

### Extra fields for source type pages

```yaml
---
title: MOHRSS 2024 Annual Enterprise Annuity Fund Statistics Report
type: source
created: 2026-04-06
updated: 2026-04-06
sources: []
confidence: high
source_type: primary               # primary | authoritative-secondary | secondary | hearsay | inference | oral
source_origin: MOHRSS official website
source_date: 2024-12-31            # Original material date (not ingest date)
source_url: ""                     # Source URL (if available)
---
```

### Extra fields for cognitive type (mental model pages)

```yaml
---
title: Circle of Competence
type: mental-model
created: 2026-04-06
updated: 2026-04-06
sources: [poor-charlies-almanack]
confidence: high
verification:
  cross_domain: true            # Cross-domain reproducibility
  generative: true              # Generative power
  exclusive: true               # Exclusivity
  domains: [investing, business decisions, life choices]  # Domains where observed
---
```

---

## Body Conventions

**Body only writes narrative analysis and context interpretation, no data tables.**

Example below (using financial domain as example):

```markdown
# Institution A Business Overview

This institution is one of the largest participants in the industry. 2025 Q1 AUM grew to XXX billion yuan,
but market share data not directly comparable to previous report due to scope change.

[[competitor-a|Competitor A]] had industry-leading growth in same period, narrowing the gap.
See [[market_landscape]].
```

**Body rules**:
- Use `[[slug]]` or `[[slug|display name]]` for page links
- When mentioning data, cite conclusions, don't repeat specific values from frontmatter (avoid inconsistency)
- Can use `> ⚠️` blockquote to label important warnings (e.g., scope differences)
- Analytical content is core value of body—what YAML cannot carry

### Page Bottom: `## Relations` (Recommended)

Render frontmatter `relations` in natural language so the agent gets structural context while reading the body, without needing to parse YAML separately. Don't rewrite the body — just add a closing section.

```markdown
## Relations

- **Part of**: [[personal-pension-system]]
- **Drivers**: [[tax-incentive-effect]] ⚠️contested, [[enrollment-friction]]
- **International comparison**: [[ira-usa]] (contrasted_with)
```

### Data-Heavy Pages: `## Key Data` (Recommended)

When a page has corresponding data points in data.db, add a lightweight section informing the agent "structured data exists here." Not a database echo — a data anchor.

```markdown
## Key Data

| Metric | Value | Period | Source |
|--------|-------|--------|--------|
| Annual contribution limit | 12,000 CNY/yr | 2022 | [[state-council-2022-7]] |
| Actual contribution rate | 25% | 2023-10 | [[ism-study-pension]] |

Full data and change history available in `data.db`.
```

---

## File Naming & Slug Unification (Critical)

**Each page has exactly one canonical slug, used across ALL layers.**

| Layer | Use same slug | Anti-pattern (split-brain) |
|-------|-------------|---------------------------|
| Filename | `tax-incentive-effect.md` | File named one way, DB uses another |
| frontmatter `sources` | `["sem-study-2024"]` | Inconsistent slug reference |
| `data.db` `pages.slug` | `tax-incentive-effect` | Different from filename |
| `data.db` `relations` | `from: tax-incentive-effect` | Different from filename |
| `[[wikilink]]` | `[[tax-incentive-effect]]` | Different from filename |

**Rules**:
- slug = filename without `.md` = `data.db` `page_slug` = `relations` `from_slug`/`to_slug` = `[[wikilink]]` target
- Chinese wikis use Chinese slugs (Obsidian-friendly, human-readable)
- English wikis use English slugs: lowercase + hyphens, e.g., `alpha-corp`
- Source pages add date prefix: `2026-04-06-hrss-report.md` (hyphen-separated)
- **During ingest, the agent MUST use the same slug for both file operations and data.db — two naming systems are never allowed**

## index.md Format

Index is the **first file** the agent reads when entering recall — it must provide both navigation and structural awareness.

```markdown
# {topic_name} Wiki Index

> {N} pages | Last updated: {date} | Type: {ontology_type}
> ⚠️ Contested: [[page-a]], [[page-b]]

## Knowledge Structure

Core topology (only show hub nodes and key edges, don't dump entire graph):

{core-concept} ── part_of ──→ {parent-concept}
  ├── {sub-a} ←── derived_from ── {sub-b} ⚠️contested
  ├── {sub-c} ←── contrasted_with ── {intl-comparison}
  └── {sub-d}

## Entities ({N})
- [[alpha-corp]] — Institution A Pension Business
- [[beta-corp]] — Institution B Pension Insurance

## Concepts ({N})
- [[trustee-market-landscape]] — Trustee competitive landscape and share
- [[enterprise-annuity-system]] — Policy regulations and system framework

## Sources ({N})
- [[2026-04-06-hrss-report]] — MOHRSS 2024 Annual Report
- [[2026-04-06-q1-briefing]] — 2025 Q1 Market Briefing

## Analyses ({N})
- [[trustee-comparison]] — Trustee market landscape comparative analysis
```

**Index rules**:
- Top header includes contested page list (if any) — agent sees unreliable knowledge at first glance upon entering recall
- `## Knowledge Structure` uses text tree showing 5-8 hub nodes + key relationship edges + contested markers, giving agent immediate structural awareness
- Category listings: one entry per line, `[[slug]] — One sentence description`

## log.md Format

```markdown
# {topic_name} Wiki Log

## 2026-04-06 14:30 — ingest
- Source: 2026-04-06-hrss-report
- Created: entities/alpha-corp, concepts/trustee_market_landscape
- Updated: (none)
- Conflicts: (none)

## 2026-04-06 15:00 — ingest
- Source: 2026-04-06-q1-briefing
- Updated: entities/alpha-corp (assets_under_management 1200→1350 billion, share contested)
- Created: entities/beta-corp
- Conflicts: alpha-corp.market_share (15% vs 12%, different scope)
```

## Validation Rules

| Rule | Requirement |
|------|-------------|
| Complete frontmatter | `title`, `type`, `created`, `updated`, `sources`, `confidence` six fields must exist |
| Valid type values | `source` / `entity` / `concept` / `analysis` / `mental-model` |
| data field specification | Each data point must have `value`, `unit`, `period`, `source` |
| history has reason | Each history record must have `reason` field |
| relations has type | Each relation must have `target` and `type` |
| sources non-empty | Except source type, `sources` list must have at least one slug |
| Date format | `YYYY-MM-DD` |
| Slug matches filename | Filename (without `.md`) = slug |

## Confidence Update Rules

| Event | Confidence Change |
|-------|-------------------|
| New source corroborates existing data (data field consistent) | → `high` |
| New source updates existing data (newer timepoint/more authoritative source) | Update data, old value to history |
| New source contradicts existing data and cannot determine | data field confidence → `contested` |
| Lint finds data field without source | → `low` |
| Page not touched by ingest for 6 months | Lint suggests label "pending verification" |
