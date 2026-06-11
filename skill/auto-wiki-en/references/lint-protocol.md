# Lint Protocol

> Lint is not just about finding problems — more importantly it is **governance**: merging, archiving, fixing. It prevents the wiki from turning into an information graveyard.

## Flow

```
1. Scan all pages
   ├─ Read meta.yaml for the wiki's basic info
   ├─ Read the hub page ({Domain Name}.md) for the page list
   ├─ Traverse the sources/ entities/ concepts/ analyses/ directories
   └─ Compare the hub page against actual files (find entries the hub missed or lists in excess)

2. Check item by item (7 checks)
   ├─ 2.1 Validation — Is each page format-compliant?
   ├─ 2.2 Contradiction — Do different pages contradict each other?
   ├─ 2.3 Duplication — Are there duplicate pages?
   ├─ 2.4 Orphan — Are there orphaned pages?
   ├─ 2.5 Broken Link — Are there broken links?
   ├─ 2.6 Staleness — Is there outdated content?
   └─ 2.7 Coverage — Are there obvious gaps in knowledge coverage?

3. Execute fixes (automatic + confirmation-required)
   ├─ Automatic: hub page sync, broken link repair, format completion
   └─ Confirmation required: merging duplicates, archiving stale pages, labeling contradictions

4. Output the health report
5. Update meta.yaml statistics
6. Append to log.md
```

## Two-Tier Execution

Lint runs in two tiers. Structural checks can run automatically over the full page set; semantic checks require the Agent to understand content page by page, with cost growing linearly in page count.

| Tier | Included Checks | Execution | Cost |
|------|-----------------|-----------|------|
| **Structural tier** (always run) | Validation, Orphan, Broken Link, Staleness | Full scan, deterministic output | O(N) file reads |
| **Semantic tier** (on demand) | Contradiction, Duplication, Coverage | Agent sampling or user-specified scope | O(N²) semantic comparison |

**Default behavior**: `lint` runs the structural tier only. The semantic tier runs when the user says "deep lint" or "check contradictions".

**Scope control for the semantic tier**:
- wiki < 50 pages: full scan
- wiki 50-200 pages: only pages touched by ingest in the last 30 days + their linked pages
- wiki > 200 pages: the user must specify a scope (e.g., "check contradictions under entities/")

---

## The 7 Checks in Detail

### 2.1 Validation (Format Validation) — Structural tier

Check every page against the Validation Rules in wiki-format.md:

| Rule | Auto-fix? |
|------|-----------|
| Missing frontmatter field | Yes — fill in defaults (type=entity, confidence=medium) |
| Invalid type value | No — report, wait for user confirmation |
| Empty sources (non-source types) | No — report, suggest linking |
| Slug inconsistent with filename | No — report |
| Malformed date | Yes — attempt auto-correction |

### 2.2 Contradiction (Contradiction Detection) — Semantic tier

Scan entity and concept pages, checking for:
- The same fact carrying different values/conclusions on different pages
- `contested` labels inside an entity page — check whether a new source can resolve them

```
Contradiction found:
- alpha-corp.md says AUM is 120 billion (source: 2026-policy-doc)
- industry-overview.md says the institution's market share implies roughly 100 billion (source: industry-report-2025)
→ Label both pages confidence → contested
```

### 2.3 Duplication (Duplicate Detection) — Semantic tier

Check whether two pages describe the same entity/concept:
- Similar filenames (e.g., `alpha-corp.md` and `alpha-annuity.md`)
- Similar titles
- High body-content overlap

**Action**: merge into one page — keep the more complete version and fold in the unique information from the other. Requires user confirmation.

### 2.4 Orphan (Orphan Detection) — Structural tier

A page has no incoming links (no other page references it via `[[slug]]`).

**Action**:
1. Check whether some page should be referencing it → yes → add the wikilink
2. Still unlinked → suggest archiving or deletion

### 2.5 Broken Link (Broken Link Detection) — Structural tier

A page contains `[[slug]]` but the corresponding file does not exist.

**Action**:
1. If the intended page can be inferred (slug spelling is close) → fix the wikilink
2. Otherwise → create a stub page (frontmatter + "TODO" only), or remove the broken link

### 2.6 Staleness (Staleness Detection) — Structural tier

| Condition | Verdict |
|-----------|---------|
| Page `updated` > 6 months ago, and confidence ≤ medium | Staleness candidate |
| All of the page's sources are > 12 months old | Staleness candidate |
| Page confidence is low and it has never been reinforced by ingest | Staleness candidate |

**Action**: label as "pending verification" or suggest archiving. Never auto-delete.

### 2.7 Coverage (Coverage Assessment) — Semantic tier

Not about finding errors — about finding gaps. Detected in 5 categories:

#### Gap-1: Page Missing

Referenced by other pages via `[[slug]]` but the actual file does not exist. Different from Broken Link — a Broken Link is a misspelled link, Page Missing means the knowledge itself is absent.

- Detection: traverse all wikilinks, find references pointing at non-existent pages
- Verdict: 3+ pages reference the same non-existent slug → not a typo, but a knowledge gap
- Output: `{ gap_type: "page_missing", slug: "xxx", referenced_by: [...] }`

#### Gap-2: Concept Missing

Multiple entity pages repeatedly mention the same term/concept, but no standalone concept page explains it.

- Detection: extract high-frequency terms from entities/ body text, check whether concepts/ has a corresponding page
- Threshold: a term appears in 3+ different pages but has no standalone concept page → gap
- Output: `{ gap_type: "concept_missing", term: "xxx", mentioned_in: [...] }`

#### Gap-3: Data Missing

An entity page mentions a metric but data.db has no corresponding value, or the value lacks key dimensions (no period, no source).

- Detection: scan page bodies for metric names, cross-check against data.db
- Output: `{ gap_type: "data_missing", page: "xxx", field: "xxx" }`

#### Gap-4: Single Source

A page's confidence depends on a single source, and that source is not primary/authoritative.

- Detection: sources list length = 1 and source_type is neither "primary" nor "authoritative-secondary"
- Output: `{ gap_type: "single_source", page: "xxx", current_source: "xxx" }`

#### Gap-5: Outdated

Different from Staleness — Staleness flags stale candidates, Outdated focuses on data for which newer reporting periods already exist but the wiki has not kept up.

- Detection: a data.db value's period is > 12 months old, and the domain typically has annual updates
- Output: `{ gap_type: "outdated", page: "xxx", field: "xxx", last_period: "xxx" }`

#### Gap-6: Validator Gap — only when the wiki declares a validator

If meta.yaml declares a `seed` and the corresponding seed file points to a `validator`, Coverage additionally runs validator checks:

- Detection: call the validator (e.g., FIBO SPARQL) to query the required relations for an entity type (`someValuesFrom` constraints), and compare against the relations already established in the wiki
- Example: FIBO says a PensionFund must have a Trustee relation, but the wiki entity page lacks it → gap
- Output: `{ gap_type: "validator_gap", page: "xxx", missing_relation: "hasTrustee", standard: "FIBO" }`
- Degradation: if the validator is unreachable, silently skip and note in the report "External validator unreachable, skipped"

What this category detects is not "missing information" but "logical incompleteness" — you claim this is a PensionFund, yet by the industry-standard definition it still needs at least an investment manager, a custodian, and a regulator.

#### Coverage Heuristics (supplementary)

Beyond the 6 categories above, keep the original heuristic checks:
- An entity is referenced by 5 other pages but its own content is thin (< 100 words) → suggest deepening
- One type (e.g., concepts/) has very few pages while entities/ has many → suggest distilling concepts
- Many source pages but few analysis pages → suggest a synthesis analysis

## Health Report Format

```
## Wiki Health Report: {topic name}
Generated: {date}

### Overview
- Total pages: 42 (sources: 12, entities: 15, concepts: 10, analyses: 5)
- Health: Good / Needs Attention / Needs Intervention
- confidence distribution: high 30 / medium 8 / low 2 / contested 2

### Fixes This Run
- [Auto] Hub page sync (added 2 missing entries)
- [Auto] Fixed 1 broken link (portable-annuity → portable-annuity-scheme)
- [Confirm] Merge alpha-corp.md and alpha-annuity.md (suspected duplicate)

### Pending Issues
- Contradictions: 2 (list the specific pages and points of conflict)
- Stale: 1 page suggested for archive (portfolio-category, no update in 6 months)

### Coverage Suggestions
- entities/beta-corp.md is thin (only 50 words) yet referenced by 4 pages — suggest ingesting more material
- concepts/ has only 10 pages while entities/ has 15 — suggest distilling more concept pages

### Statistics
- Most active source: 2026-policy-doc (referenced by 8 pages)
- Most isolated entity: portfolio-category (0 incoming links)
- Latest ingest: 2026-04-06 (3 days ago)
```

## Gap Report Format (for deep-dive)

When the Coverage check is triggered by deep-dive, output a structured gap report in addition to the health report:

```
## Gap Report: {topic}
Generated: {date}
Scope: {full | specified range}

### Gaps Found: {N}

| # | Category | Target | Detail | Priority | Search Direction |
|---|----------|--------|--------|----------|------------------|
| 1 | page_missing | portable-annuity | Referenced by 4 pages | high | Search "portable pension scheme policy" |
| 2 | concept_missing | trustee qualification | Mentioned in 5 entity pages | high | Search "pension trustee qualification requirements" |
| 3 | single_source | alpha-corp | Only source: industry-report-2025 | medium | Search "Alpha Corp pension annual report" |

### Priority Rules
- high: page_missing (3+ references), concept_missing (5+ mentions)
- medium: single_source, data_missing
- low: outdated (data age 12-24 months)
```

### Scope Control (deep-dive scenario)

When triggered by deep-dive, Coverage accepts optional scope parameters:
- `deep-dive {topic}` → limit to the specified wiki
- `deep-dive {topic} entities/` → limit to a subdirectory
- `deep-dive {topic} --max-gaps N` → cap the number of gaps (default 10)
- No scope given → follow the semantic tier's scope control rules (<50 pages full scan, 50-200 pages last 30 days, >200 pages require an explicit scope)
