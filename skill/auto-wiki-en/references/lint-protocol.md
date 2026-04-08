# Lint Protocol

> Lint is not just checking problems, it's **governance**—merging, archiving, fixing. Prevents wiki from becoming an information graveyard.

## Flow

```
1. Scan all pages
   ├─ Read meta.yaml for wiki basic info
   ├─ Read index.md for page list
   ├─ Traverse sources/ entities/ concepts/ analyses/ directories
   └─ Compare index vs actual files (find index omissions or extras)

2. Check item by item (7 checks)
   ├─ 2.1 Validation — Page format compliance
   ├─ 2.2 Contradiction — Contradictions between pages
   ├─ 2.3 Duplication — Duplicate pages
   ├─ 2.4 Orphan — Orphaned pages
   ├─ 2.5 Broken Link — Broken links
   ├─ 2.6 Staleness — Outdated content
   └─ 2.7 Coverage — Knowledge coverage gaps

3. Execute fixes (auto + pending confirmation)
   ├─ Auto-fix: index sync, broken link repair, format completion
   └─ Pending confirmation: Merge duplicates, archive outdated, label conflicts

4. Output health report
5. Update meta.yaml statistics
6. Append log.md
```

## Two Levels

Lint has two levels. Structural checks can auto-run full pages; semantic checks require Agent to understand content page by page, cost grows linearly with page count.

| Level | Included Checks | Execution | Cost |
|-------|-----------------|-----------|------|
| **Structural** (must run) | Validation, Orphan, Broken Link, Staleness | Full scan, deterministic output | O(N) file reads |
| **Semantic** (on-demand) | Contradiction, Duplication, Coverage | Agent sampling or user-specified scope | O(N²) semantic comparison |

**Default behavior**: `lint` only runs structural. User says "deep lint" or "check conflicts" to run semantic.

**Semantic scope control**:
- wiki < 50 pages: Full scan
- wiki 50-200 pages: Only pages touched by ingest in last 30 days + their related pages
- wiki > 200 pages: User must specify scope (e.g., "check conflicts under entities/")

---

## 7 Check Details

### 2.1 Validation (Format Validation) — Structural

Check each page per Validation Rules in wiki-format.md:

| Rule | Auto-fix? |
|------|-----------|
| Missing frontmatter field | Yes — Add defaults (type=entity, confidence=medium) |
| Invalid type value | No — Report, wait user confirmation |
| Empty sources (non-source types) | No — Report, suggest association |
| Slug inconsistent with filename | No — Report |
| Date format error | Yes — Attempt auto-correction |

### 2.2 Contradiction (Conflict Detection) — Semantic

Scan entity and concept pages, check:
- Same fact has different values/conclusions in different pages
- Entity page has `contested` label—check if new source can resolve

```
Found conflict:
- alpha-corp.md says AUM 1200 billion (source: 2026-policy-doc)
- industry-overview.md says institution market share implies approx 1000 billion (source: industry-report-2025)
→ Label both pages confidence → contested
```

### 2.3 Duplication (Duplicate Detection) — Semantic

Check if two pages describe same entity/concept:
- Similar filenames (e.g., `alpha-corp.md` and `alpha-annuity.md`)
- Similar titles
- High content overlap

**Action**: Merge into one page, keep more complete version, merge unique info from other. Requires user confirmation.

### 2.4 Orphan (Orphan Detection) — Structural

Page has no incoming links (no other page references it via `[[slug]]`).

**Action**:
1. Check if there should be pages referencing it → Yes → Add wikilink
2. Still no association → Suggest archive or delete

### 2.5 Broken Link (Broken Link Detection) — Structural

Page has `[[slug]]` but corresponding file doesn't exist.

**Action**:
1. If can infer which page it should be (slug spelling close) → Fix wikilink
2. Otherwise → Create stub page (only frontmatter + "TODO"), or remove broken link

### 2.6 Staleness (Outdated Detection) — Structural

| Condition | Determination |
|-----------|---------------|
| Page `updated` > 6 months ago, and confidence ≤ medium | Staleness candidate |
| All page sources > 12 months old | Staleness candidate |
| Page confidence is low and never reinforced by ingest | Staleness candidate |

**Action**: Label "pending verification" or suggest archive. Don't auto-delete.

### 2.7 Coverage (Coverage Assessment) — Semantic

Not finding errors, but finding gaps:
- Entity referenced by 5 other pages but content is thin (< 100 words) → Suggest deepening
- Few pages of certain type (e.g., concepts/) but many entities/ → Suggest extracting concepts
- Many source pages but few analysis pages → Suggest comprehensive analysis

## Health Report Format

```
## Wiki Health Report: {topic name}
Generated: {date}

### Overview
- Total pages: 42 (sources: 12, entities: 15, concepts: 10, analyses: 5)
- Health: Good / Needs Attention / Needs Intervention
- confidence distribution: high 30 / medium 8 / low 2 / contested 2

### This Run Fixes
- [Auto] index.md sync (added 2 missing entries)
- [Auto] Fixed 1 broken link (portable-annuity → portable-annuity-scheme)
- [Pending] Merge alpha-corp.md and alpha-annuity.md (suspected duplicate)

### Pending Issues
- Conflicts: 2 (list specific pages and conflict points)
- Outdated: 1 page suggested for archive (portfolio-category, 6 months no update)

### Coverage Suggestions
- entities/beta-corp.md content thin (only 50 words), referenced by 4 pages, suggest ingest more materials
- concepts/ only 10 pages while entities/ has 15 pages, suggest extract more concept pages

### Statistics
- Most active source: 2026-policy-doc (referenced by 8 pages)
- Most isolated entity: portfolio-category (0 incoming links)
- Recent ingest: 2026-04-06 (3 days ago)
```
