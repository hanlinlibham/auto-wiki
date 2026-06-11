# Ingest Protocol

> Ingest is not appending files — it is **compilation**: check canonical first, read the old, compare the new, modify the old via the retirement protocol.
> This document is the **domain-agnostic engine specification**; the authoritative contract is each domain's `_ontology.md` (e.g. `wiki/macro/_ontology.md`), the concrete instance for that domain, defining node-type criteria, the controlled relation vocabulary, the six-tier time model, and table schemas. **Wherever any step below involves criteria / vocabulary / time tiers / table names, the target domain's `_ontology.md` prevails.** Examples below use objects from the macro domain, but the flow is generic to any domain.

---

## Core Mindset (memorize before starting)

1. **Three-way split: nodes / data / edges**:
   - **Numeric values are never nodes** — `7-day reverse repo rate = 1.40%` gets no page; it goes into `data.db`. The graph contains only the series "7-day reverse repo rate", never the point "1.40%".
   - **Relations are edges, not nodes** — "the PBoC operates the 7-day reverse repo" is one `operated_by` edge, not a page called "operates".
   - **Classification tags are not nodes** — labels like "quantity-based / price-based" are multi-dimensional tags attached to nodes (`classified_as` edges), not pages.
2. **Wikis are organized by domain, not by research topic** — pages land in `wiki/{domain}/{type-subdirectory}/` (institutions/instruments/indicators/mechanisms/events/analyses/sources). A research report is itself **one page** under `analyses/`, not a directory; its research topic is a derived view — deleting it leaves the ontology untouched.
3. **Compilation is one-way** — `Inbox (human prose) → ingest → wiki (ontology artifact)`. Rigor applies to crystallized knowledge (the wiki), not to knowledge still crystallizing (the Inbox).
4. **Retire, never delete** — any change to T1/T2/T3 means "seal the old row's `valid_to` + insert a new row", never DELETE, and there must always be a T4 event stamp (see the six-step retirement protocol below).

---

## Main Flow

```
1. Read the source file → write sources/{date}-{slug}.md (immutable faithful summary)
   ├─ Extract key information: node candidates, relations, values, conclusions, dates, events
   └─ frontmatter records source_type / source_origin / source_date

2. Extract terms one by one → first check whether a canonical page (incl. aliases) already exists  KEY CHANGE
   ├─ Read the target domain hub ({Domain}.md, e.g. Macro.md) to get the full page list
   ├─ For each candidate term, compare against existing pages' "filename slug" + "aliases field"
   │   (cross-report synonyms converge via aliases: OMO = 7-day reverse repo, MDS = outright reverse repo, "restarted/resumed" treasury bond trading)
   └─ Hit → branch A (exists); miss → branch B (does not exist)

   ┌─ A) Exists → merge / update via the retirement protocol
   │   ├─ Append the new source slug to the page's sources list
   │   ├─ New value/state: assign its time tier per step 4 → write to the matching table
   │   │   · T0 value → data_points (same-period overwrite only for corrections, otherwise insert a new row)
   │   │   · T1/T2/T3 change → never edit in place; follow the six-step "retire, never delete"
   │   └─ log: "merged/retired: {page}"
   │
   └─ B) Does not exist → run the target domain _ontology.md "classification decision tree" to assign a type → create the page in the matching subdirectory

3. Assign each piece of knowledge a tier in the six-tier time model → write to the matching table  KEY CHANGE
   (tiers and criteria in _ontology.md §4; table schemas in §7)
   ├─ T0 observation (one measurement of an indicator at a point in time, value is a number) → data_points
   ├─ T1 state / regime (a proposition true over a span, flipped in one stroke by an event)   → facts (zipper table)
   ├─ T2 durable logic (cross-cycle causal chain / definition, falsifiable)                   → facts (zipper table) + mechanism page body/durability field
   ├─ T3 entity / near-permanent relation (objective existents and essential attribution)     → entity page + relations (temporal)
   ├─ T4 event (has a date + actor, fixed once it happens)                                    → events (append-only) + event page
   └─ T5 type axiom (constrains what other knowledge looks like)                              → no record rows; goes into _ontology.md / DB CHECK

4. Add / retire controlled relation edges
   ├─ type must come from the target domain's controlled relation vocabulary (macro: operated_by/implements/transmits_to/
   │   bounds/classified_as/instance_of/part_of/created_by/changed_by/references)
   ├─ Dual-write: page frontmatter.relations[] (edges for Obsidian) + data.db relations table
   └─ Retracting a relation = write valid_to + retract_event_slug on the relations row; never delete the row

5. Land the report under analyses/ + update the hub ({Domain}.md) + append to log.md
   ├─ The report itself gets analyses/{date}-{slug}.md (type: analysis), tracing back via references edges to the nodes it cites
   ├─ Hub: add new pages to the right group, update counts and Last updated, leave existing entry descriptions untouched
   └─ log.md is append-only

6. Run schema validation (references/schema.py + data.db table constraints)

7. Refresh position encoding + report (calibrated graph layout)
   ├─ python references/position_encoding.py wiki/{domain}   → recompute _positions.json
   └─ python references/schema.py --report wiki/{domain}     → rebuild _report.html
```

---

## Key Principles

**1. Check canonical first; modifying old beats creating new**

When a term is extracted, **the first move is to check whether it is already a canonical page (compare filename slug + aliases), not to create a page**. If it matches the existing `instruments/7-day reverse repo.md` and the new report mentions it too (even under aliases like "OMO" / "open market operations") → merge into the existing page, **never** create `instruments/7-day reverse repo 2.md`. Append newly discovered aliases into that page's `aliases:` field so the next ingest also matches.

**2. One single slug — never invent a second naming scheme**

**Filename (minus .md) = `[[wikilink]]` target = `data.db` primary key = the slug on both ends of a relation** — the entire system has exactly this one set of slugs (slug = filename = wikilink = data.db primary key, English slugs). Do **not** introduce a separate PascalCase id scheme (that would fight Obsidian's filename-based links and create a second naming layer). Cross-report deduplication relies solely on `aliases:`, not on parallel ids.

**3. Numeric values never go into pages — they go into data.db**

Page bodies carry narrative analysis: **quote data conclusions without repeating the specific numbers** (write "the policy rate stays low", not "= 1.40%"). Concrete figures go into `data_points`. A data-heavy page may add a `## Key Data` section listing a digest of that page's data points in data.db (a digest, not the source of truth).

**4. Retire, never delete (six steps for any T1/T2/T3 change)**

Outdated T1/T2 conclusions are **neither deleted nor edited in place** — back then they were high-confidence; they are not wrong, just expired. Every change is append-only; not one byte of the original record is lost. See the "six-step retirement protocol" below.
(**Sole exception**: a T0 pure correction within the same `period` may overwrite, but keep both rows + distinguish them via `recorded_at`; do not stuff them into history.)

**5. Bitemporal — never mix the two time axes**

Every assertion records two time axes: `valid_from/valid_to` (when it was true in the world, valid-time) + `recorded_at` (which report of mine recorded it, transaction-time).
- **`valid_from` changes = the world changed** (regime evolution, e.g. the policy anchor switching) → run the retirement protocol, stamp with an event.
- **Only `recorded_at` moves = my own erratum** (same fact, new source / corrected entry) → not a world change, no event stamp.
These two must never be mixed.

**6. Every change of "current state" needs a T4 event stamp**

Any flip of a T1/T2 current state must trace back to a T4 event page (`caused_by_event`). If no event exists, create one first (gradual transitions get a proxy-event stake; see _ontology.md §9).

**7. One ingest touching many pages is normal**

A single report may involve 5-10 nodes. One ingest updating 8 pages is normal; record it all in the log.

**8. Source pages are immutable**

Summary pages under `sources/` are never modified after creation (unless the summary itself is wrong). They are the faithful record of the raw material; other pages reference them via the `sources` frontmatter field.

---

## Six-Step Retirement Protocol — when old logic is overturned by a T4 event

> **Canonical example**: `MLF rate = policy rate anchor` (T1 state) overturned by `2025-03 MLF American-style auction reform` (T4 event). Fully append-only; not one byte of the original record is lost. Swap in your own domain's objects when working elsewhere.

1. **Write the event page first** `events/2025-03-MLF-reform.md` (`type: event`); frontmatter declares `event_date`, `actor`, `retires: [[MLF is the policy rate anchor]]`, `sets: {policy rate anchor: 7-day reverse repo}`. Simultaneously INSERT into the `events` table.
2. **Stamp the old facts row's valid column** (the only allowed in-place write, touching one column only): `valid_to: 9999 → 2025-03`, `is_current: 0`. The old conclusion stays **word-for-word untouched**.
3. **Wire the causal pointer**: the old facts row gets `caused_by_event → [[2025-03-MLF-reform]]`.
4. **Insert the successor row**: `policy rate anchor = 7-day reverse repo, valid_from=2025-03, is_current=1, supersedes_id = old row id`.
5. **Historicize at the page layer**: the body of the affected mechanism/entity page is **not deleted**; add a callout at the top:
   `> [!warning] Retired (invalid since 2025-03): MLF is no longer the policy rate anchor; the 7-day reverse repo became the sole policy rate anchor. See [[2025-03-MLF-reform]]`. Frontmatter set to `is_current: false`, `valid_to: 2025-03`.
6. **Relation layer (if T3 edges changed)**: write `valid_to` + `retract_event_slug` on the overturned relations rows, insert new edges, never delete old ones.

**Effect**: query "current anchor" → 7-day reverse repo; query "what did I believe the anchor was in 2024" → MLF; ask "why did it change" → hop via `caused_by_event` to the event page. What was once true, when it became false, and what changed it — all three fully traceable.

---

## Same source, same rank, no way to adjudicate → conflict side by side

When new and old claims contradict, the sources are of equal rank with no newer date, and there is no way to tell who is right (typically: different statistical scopes), **do not reconcile, do not invent a compromise**. Present both claims side by side in the page, each labeled with its source; frontmatter `confidence: contested`; log records `conflict`.

```markdown
## Market Share

> [!warning] contested — two sources disagree

- Per [[2026-04-06-policy-doc]]: the institution's market share is ~15%
- Per [[2025-annual-industry-report]]: the institution's market share is ~12%

The gap may stem from differing statistical scopes (with/without a certain sub-item).
```

> Distinguish carefully: **a newer date or a more authoritative source** → that is world evolution or an erratum — run the retirement protocol (not a conflict); **equal rank with no way to adjudicate** → only then is it a contested side-by-side.

---

## Worked Example: Full Ingest Flow

> Uses the macro domain as the example; in real runs, substitute the user's target domain and its `_ontology.md`.

**Scenario**: the user ingests a fixed-income research report into `wiki/macro/`. The wiki already has some pages.

### Step 1 — Read the source file, generate the source summary page

Create `sources/2026-05-25-broker-fixed-income-report.md`:

```yaml
---
title: Broker fixed-income report (2026-05-25)
type: source
created: 2026-05-25
updated: 2026-05-25
sources: []
confidence: high
source_type: secondary          # broker research report
source_origin: A broker's research institute
source_date: 2026-05-25
---
```

The body is a faithful summary of the original's key information.

### Step 2 — Extract terms, check canonical first (including aliases)

The report mentions "the OMO rate holds at 1.40%", "MLF is no longer the policy rate anchor", "treasury bond trading restarted".

Read the hub `Macro.md` for the page list, compare each term against slug + aliases:

- "OMO" → hits `indicators/7-day reverse repo rate.md` (its `aliases:` includes "OMO rate") → **branch A, exists**.
- "MLF policy rate anchor" → hits the T1 state `MLF is the policy rate anchor` inside a mechanism page → **branch A, and the state is overturned → retirement protocol**.
- "treasury bond trading" → hits `instruments/treasury bond trading.md` (aliases include "restarted treasury bond trading") → **branch A**.

Check the indicator's current value in data.db:

```python
store.query_data(page_slug="7-day reverse repo rate")
# → [{ field:"rate", value:1.40, unit:"%", period:"2026-05",
#      recorded_at:"2026-04-...", source_slug:"..." }]
```

### Step 3 — Assign each piece of knowledge a time tier, write the matching table

- **`7-day reverse repo rate = 1.40%`** → **T0 observation**. New period (2026-05) → insert a new row into `data_points`, with `recorded_at`, `source_slug`; do not overwrite old periods.

  ```python
  store.upsert_data(
      page_slug="7-day reverse repo rate", field="rate", value=1.40, unit="%",
      period="2026-05", recorded_at="2026-05-25",
      source_slug="2026-05-25-broker-fixed-income-report")
  ```

- **`MLF is the policy rate anchor` overturned** → this is a **T1 state flipped by a T4 event** → run the six-step "retire, never delete":
  1. Create `events/2025-03-MLF-reform.md` (`type: event`, `retires`, `sets`) + INSERT into `events`.
  2. Stamp the old facts row: `valid_to=2025-03, is_current=0` (`object_text` untouched word-for-word).
  3. Old row gets `caused_by_event = 2025-03-MLF-reform`.
  4. Insert the new row: `policy rate anchor = 7-day reverse repo, valid_from=2025-03, is_current=1, supersedes_id = old row id`.
  5. Add the `[!warning]` callout atop the mechanism page, frontmatter `is_current: false`.

  ```python
  store.insert_event(slug="2025-03-MLF-reform", event_date="2025-03-01",
                     actor_slug="People's Bank of China",
                     description="MLF switched to American-style auction, exiting the policy-rate-anchor role",
                     source_slug="2026-05-25-broker-fixed-income-report")
  store.retire_fact(old_fact_id, valid_to="2025-03",
                    caused_by_event="2025-03-MLF-reform")
  store.insert_fact(page_slug="monetary policy toolkit", predicate="policy rate anchor",
                    object_slug="7-day reverse repo", valid_from="2025-03",
                    is_current=1, supersedes_id=old_fact_id,
                    caused_by_event="2025-03-MLF-reform",
                    source_slug="2026-05-25-broker-fixed-income-report")
  ```

### Step 4 — Controlled relation edges (dual-write)

```python
# instrument → institution (T3, near-permanent edge, valid_to stays 9999)
store.add_relation("treasury bond trading", "People's Bank of China", "operated_by")
# instrument → classification tag (no page, just an edge)
store.add_relation("7-day reverse repo", "price-based", "classified_as")
```

Page frontmatter writes `relations:` in sync — both sides consistent.

### Step 5 — Land the analysis page + update the hub + log

The report itself gets `analyses/2026-05-25-fixed-income-view.md` (`type: analysis`), tracing back via `references` edges to the nodes it cites (not part of the semantic graph). Update the `Macro.md` hub groups and counts.

Append to `log.md`:

```
## 2026-05-25 14:30 — ingest
- Source: sources/2026-05-25-broker-fixed-income-report
- Merged: indicators/7-day reverse repo rate (data_points +1 row, period 2026-05, value 1.40%)
- Retired: monetary policy toolkit "policy rate anchor" MLF → 7-day reverse repo (event 2025-03-MLF-reform)
- Created: events/2025-03-MLF-reform
- Relations: treasury bond trading → People's Bank of China operated_by
- Conflicts: none
```

### Step 6 — Schema validation

Run `references/schema.py` (frontmatter validation) + data.db table constraints (`pages.type` includes `event`, facts zipper columns complete, relations temporal columns complete).

### Step 7 — Position encoding refresh (calibrated graph layout)

After any insert/update/delete of nodes/relations, the coordinates are stale and must be recomputed:

```bash
python references/position_encoding.py wiki/{domain}   # y = ontology level, x = Laplacian spectral coordinate, pe = sin/cos vector → _positions.json
python references/schema.py --report wiki/{domain}     # _report.html auto-enables the calibrated layout
```

`_positions.json` is a derived artifact (like `_report.html`): recompute anytime, deleting it never harms the ontology; do not hand-edit.

---

## Frontmatter Quick Reference (consult when writing pages)

> Full templates in the target domain's `_ontology.md` appendix. Below are the kinds most often written during ingest.

```yaml
# Entity (institution/instrument/indicator — pick one subtype)
type: entity
subtype: instrument        # institution | instrument | indicator
aliases: [OMO, open market operations]   # cross-report dedup lives here — no parallel id scheme
sources: [2026-05-25-broker-fixed-income-report]
relations:
  - {target: People's Bank of China, type: operated_by}
  - {target: price-based, type: classified_as}

# Concept / mechanism (with T2 durability and falsification conditions)
type: concept
durability: medium          # high/medium/low
preconditions: [short-end rates are steered by the central bank]
falsifiable_by: [abandoning corridor-based control for a single policy rate]

# Event (T4, append-only)
type: event
event_date: 2025-03-01
actor: People's Bank of China
retires: [MLF is the policy rate anchor]
sets: {policy rate anchor: 7-day reverse repo}
```

---

## From-Lint Flow (the ingest stage of the deep-dive pipeline)

When ingest is triggered by the deep-dive pipeline, the input is not a user-provided source file but the Gap Report output by lint Coverage.

### Differences from standard ingest

| Aspect | Standard ingest | from-lint ingest |
|------|------------|------------------|
| Input | User-provided source file | Gap entries in the Gap Report |
| Source acquisition | Already provided by the user | Agent fetches via search tools |
| Batch behavior | Usually 1 source file | Possibly N gaps, handled one by one |
| User confirmation | Not needed (user provided proactively) | Needed (confirm scope before search, quality after search) |

### Flow

```
Input: Gap Report (from lint Coverage)

For each confirmed gap:

1. Build a search plan
   ├─ page_missing → search basic info on that node (institution/instrument/indicator/mechanism)
   ├─ concept_missing → search the mechanism's definition and workings
   ├─ data_missing → search the indicator's latest data (lands as T0 / data_points)
   ├─ event_missing → search whether a switch maps to an event with date + actor (lands as T4)
   ├─ single_source → search additional sources for cross-validation
   └─ outdated → search the latest info on the indicator/state (may trigger the retirement protocol)

2. Execute the search (requires search tools — active mode)
   ├─ Use WebSearch / search-class MCPs to fetch candidate sources
   ├─ Search-tool priority: domain-specialized tools > generic search
   ├─ Grade and filter per source-validation.md
   └─ Exclude blacklisted channels; keep the top 1-3 credible sources

3. Show search results, ask the user to confirm
   ├─ Show each source's title, URL, credibility grade
   ├─ User chooses: accept / skip / replace
   └─ Results not good enough → mark "unfilled", skip

4. For each confirmed source, run the standard ingest main flow
   ├─ Steps 1-6 identical to normal ingest (incl. canonical-first, time-tier assignment, retirement protocol)
   └─ The source summary page additionally records deep-dive metadata (see source-validation.md)
```

### Anti-sprawl mechanisms

- Each gap gets at most 3 searches (with reworded keywords). No credible source after 3 tries → mark "unfilled".
- A single deep-dive handles at most 10 gaps (adjustable via `--max-gaps`).
- If a found source introduces nodes entirely absent from the wiki, **do not auto-create pages** — fill only known gaps; never proactively expand the wiki's scope.
- All searched-in sources have a `confidence` cap of medium (unless the source is primary / authoritative secondary).

### Completion report

```
## Deep-Dive Completion Report: {domain}
Run time: {date}

### Filled: {N} / {total} gaps
| # | Gap | Action | Source | Confidence |
|---|-----|--------|--------|------------|
| 1 | page_missing: SLF | Created instruments/SLF.md | [authoritative-secondary] PBoC official site | medium |
| 2 | single_source: interest-rate-corridor | Added 1 source | [secondary] industry report | medium |

### Unfilled: {M} gaps
| # | Gap | Reason |
|---|-----|--------|
| 3 | data_missing: DR007 / latest value | 3 searches found no credible source |

### Suggestions
- For the latest DR007 data, the user should provide it manually or connect a data MCP (bulk market data does not enter the wiki).
```
