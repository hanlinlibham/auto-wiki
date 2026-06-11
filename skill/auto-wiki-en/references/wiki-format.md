# Wiki Page Format

> **This document is the domain-agnostic engine specification.** It defines what every wiki page looks like, which frontmatter fields exist, how relations are written, and where values go. A specific domain's ontology contract (e.g. `wiki/macro/_ontology.md`) is an instance of this specification — the engine spec comes first, the domain contract second; where the two agree, the domain contract takes precedence in making things concrete.
>
> **All frontmatter structures are defined and validated by the Pydantic models in `schema.py`.** This document is the human-readable specification; `schema.py` is the machine-executable validator; the two must stay consistent.
> Validation command: `python references/schema.py wiki/{domain}/`

---

## Three Master Principles (rules first)

1. **A three-way split of nodes / data / edges.**
   - **A value is never a node** — `7-day reverse repo rate = 1.40%` gets no page; it goes into `data.db`. The graph contains only the named series "7-day reverse repo rate", never a "1.40%" point. Concrete values never go in frontmatter either.
   - **A relation is an edge, not a node** — "the central bank runs the 7-day reverse repo" is one `operated_by` edge, not a node called "runs".
   - **A classification label is not a node** — labels that bucket a bunch of things, like "quantity-based / price-based / structural", are `classified_as` edges attached to nodes; they never get their own pages.
2. **Data goes into structure (YAML / data.db); analysis goes into the body.** The body never holds data tables, only narrative analysis. Frontmatter carries structured facts, data.db carries values/states/events/relations, and the body carries the interpretation YAML cannot express.
3. **Compilation is one-way**: `Inbox (human-written prose) → ingest → wiki (ontology product)`. The wiki is only consumed in reverse by `recall`. Rigor applies to knowledge already crystallized (wiki), not knowledge still crystallizing (Inbox).

---

## Directory Structure (type is directory, directory is graph coloring)

The wiki is organized by **domain**, not by research topic. One directory per domain, with subdirectories per node type inside. Research topics are demoted to a single page under `analyses/`; they no longer get their own top-level directories.

```
wiki/{domain}/               # e.g. wiki/macro/
├── _ontology.md            # This domain's ontology contract (humans and Agents read it before ingest/recall)
├── {Domain}.md             # Hub / MOC, graph navigation center (named after the domain, e.g. Macro.md)
├── log.md                  # ingest operation log (append-only, human-readable)
├── data.db                 # Sole source of truth: values, states, events, relations
├── institutions/   …       # Entity · institution (red, center)
├── instruments/    …       # Entity · instrument (blue)
├── indicators/     …       # Entity · indicator (cyan)
├── mechanisms/     …       # Concept · mechanism (green)
├── events/         …       # Event (yellow)
├── analyses/       …       # Analysis: research topics / derived views archive (gray)
└── sources/        …       # Source: report/article original carrier pages (light gray)
```

**Color discipline**: the Obsidian graph colors by subdirectory rules such as `path:institutions/`. **≤ 6 top-level node directories = ≤ 6 colors** (9 colors are indistinguishable to the eye; the three entity subdirectories take red/blue/cyan, events/analyses/sources one color each, mechanisms one color). Never put a trailing `path:wiki` catch-all gray rule in `graph.json`, or it will override all the colors.

> **wiki/ must be a visible directory** — committed to git, present in the Obsidian graph, directly browsable by humans. **Never use a `.wiki/` dot directory** (Obsidian hides dotfolders; they are invisible in the graph).

---

## Node Types (extended from 5 to 7)

| Type | type value | subtype | Subdirectory | Criterion | Tags | Graph color |
|---|---|---|---|---|---|---|
| **Entity · institution** | `entity` | `institution` | `institutions/` | A named actor | `entity` `institution` | Red (center) |
| **Entity · instrument** | `entity` | `instrument` | `instruments/` | A named tool created and run by some institution | `entity` `instrument` | Blue |
| **Entity · indicator** | `entity` | `indicator` | `indicators/` | A named time series that can be re-queried (its identity is the series, not any single day's value) | `entity` `indicator` | Cyan |
| **Concept · mechanism** | `concept` | — | `mechanisms/` | Machinery/framework only understandable via an intensional definition | `concept` `mechanism` | Green |
| **Event** | `event` | — | `events/` | Has a definite date + an actor; happens once and never again | `event` | Yellow |
| **Analysis** | `analysis` | — | `analyses/` | Research judgments derived from the nodes above (a derived view; deleting it does not harm the ontology) | `analysis` | Gray |
| **Source** | `source` | — | `sources/` | The carrier page of one report/article original; every assertion is traceable to it | `source` | Light gray |

### Core Criterion: individual vs class

> **"Can I point a finger and say 'this exact one' — and will the same name still point to the same thing next year?"**
> Yes → **entity (individual)**; no — you must first explain "how it works / how it is defined" before anyone understands → **concept/mechanism (class)**.

"Does it have data / does it have structure / is it abstract" will deceive you — the interest rate corridor has an upper/lower-bound structure and numbers, yet it remains a concept (there is no "one named thing that created it"). The only reliable criterion is "can you point a finger at that one thing". This replaces the old "abstract or not / has data or not" criteria.

> **Note**: the old version had a `mental-model` type for cognitive wikis. In the v2 engine, mental models are modeled as `concept` (mechanism) — they too are classes that "require a definition before they are understood". If a domain genuinely needs a dedicated subtype, extend it in that domain's `_ontology.md`; the engine does not open one by default.

---

## Page Format

Each page has two parts: **YAML frontmatter (structured data)** + **Markdown body (narrative analysis)**.

---

## Frontmatter Schema

### Base fields (required on all pages)

```yaml
---
title: 7-day reverse repo
type: entity                    # entity | concept | event | analysis | source
created: 2026-06-07
updated: 2026-06-07             # must be updated on every modification
sources: [2026-05-25-broker-fixed-income-report]   # slugs of referenced source pages (source type uses [])
confidence: high                # high | medium | low | contested
tags: [entity, instrument]      # required: page-type tags + optional status tags
aliases: [OMO, open market operations]   # optional: aliases (cross-report dedup relies on them)
---
```

| Field | Required | Description |
|------|------|------|
| `title` | Yes | Page title (= slug = filename) |
| `type` | Yes | Node type: `entity` / `concept` / `event` / `analysis` / `source` |
| `subtype` | Required for entity | `institution` / `instrument` / `indicator` (only with `type: entity`) |
| `created` | Yes | Creation date `YYYY-MM-DD` |
| `updated` | Yes | Last update date (must be updated on every modification) |
| `sources` | Yes | List of referenced source page slugs (source type uses `[]`) |
| `confidence` | Yes | Confidence: `high` / `medium` / `low` / `contested` |
| `tags` | Yes | Obsidian tag list (type tags + optional status tags) |
| `aliases` | No | Alias list, **the workhorse of cross-report dedup** (OMO = 7-day reverse repo, MDS = outright reverse repo, "restarted/resumed" treasury bond trading) |

### Time-Tier Fields (the v2 core: different time tiers, different fields)

Frontmatter carries different fields depending on the node's **time tier**. The six-tier time model lives in `_ontology.md` §4; only the fields mapped onto frontmatter are listed here.

**Entities' essential-affiliation edges / states (T1 states / T3 near-permanent relations)** — temporality goes on the `relations[]` entries:

```yaml
relations:
  - {target: People's Bank of China, type: operated_by, valid_from: 1900-01-01, is_current: true}
```

| Field | Used on | Description |
|------|------|------|
| `valid_from` | relations entries / states | When this relation/state **became true in the world** (valid-time) |
| `valid_to` | relations entries / states | When it expired; near-permanent edges leave it empty or `9999-12-31` |
| `is_current` | relations entries / states | Whether it still holds; set to `false` upon retirement |

> **Values never enter frontmatter** (T0 observations go into `data.db data_points`). The "states" in frontmatter carry only **textual propositions** (e.g. "current policy rate = 7-day reverse repo"), never numbers. State changes land primarily in the `data.db facts` zipper table, with a callout at the top of the page marking retirement (see "Retirement" below).

**Mechanisms (concepts, T2 durable logic)** — carry durability and falsifiability conditions:

```yaml
durability: high                # T2 durability: high (definitional) | medium (causal transmission) | low (empirical regularity)
preconditions: [short-end rates are dominated by the central bank]        # the premises under which this logic holds
falsifiable_by: [corridor framework abandoned in favor of a single policy rate]  # what would falsify / invalidate it
```

**Events (T4)** — carry a date, an actor, and what they retired/set:

```yaml
event_date: 2025-03-01          # date the event occurred
actor: People's Bank of China   # actor (institution slug)
retires: [MLF is the policy rate anchor]       # which old propositions this event invalidated
sets: {policy rate anchor: 7-day reverse repo} # which state this event set to what
```

### tags Rules (required for Obsidian search filtering)

`tags` must include the page-type tags and may append status tags. **EN-edition wikis use English tags**:

```yaml
tags:
  - entity                     # required: node type
  - instrument                 # an entity's subtype also gets a tag (institution/instrument/indicator)
  - contested                  # optional: added when confidence=contested
  - retired                    # optional: added when the state has been retired by an event
```

Type tag mapping:

| type | subtype | Tags |
|------|---------|---------|
| entity | institution | `entity` `institution` |
| entity | instrument | `entity` `instrument` |
| entity | indicator | `entity` `indicator` |
| concept | — | `concept` `mechanism` |
| event | — | `event` |
| analysis | — | `analysis` |
| source | — | `source` |

Status tags: `contested` (contested), `low-confidence` (low), `retired` (state sealed by an event).

Source-type pages additionally carry a source-grade tag: `primary-source` / `authoritative-secondary` / `secondary` / `hearsay` / `inferred`.

Source-grade mapping:

| source_type | Tag |
|-------------|---------|
| primary | `primary-source` |
| authoritative-secondary | `authoritative-secondary` |
| secondary | `secondary` |
| hearsay | `hearsay` |
| inference | `inference` |

These tags serve Obsidian search filtering (e.g. type `tag:#contested` in the search bar to locate contested pages quickly). Graph coloring does not rely on tags — page types are distinguished by `path:` subdirectory rules, and risky nodes are highlighted by the `[confidence:contested]` Properties query.

### aliases Rules

aliases are **the workhorse of cross-report dedup**: different reports call the same thing by different names; stuff them all into `aliases`, and at ingest, first check aliases — if an existing page is hit, do not create a duplicate page.

When a title contains a parenthetical qualifier, also split out the short name and the parenthetical content as aliases:

```yaml
title: outright reverse repo
aliases:
  - MDS
  - outright reverse repo operations
title: treasury bond trading
aliases:
  - restart of treasury bond trading
  - resumption of treasury bond trading
```

---

## Structured Data → data.db (values never enter frontmatter)

**All quantifiable, verifiable, comparable data is written into `data.db` (SQLite) — never into frontmatter and never into body tables.**

data.db stores more than values; it is split into tables by time tier (full schema in `_ontology.md` §7):

| Table | What it stores | Time tier | Key columns |
|----|--------|--------|--------|
| `data_points` | Numeric observations (per-period time series; the value is a number) | T0 | `value REAL, unit, period, recorded_at, source_slug, supersedes_id` |
| `facts` | State/logic propositions (object is text/slug, non-numeric) | T1 states / T2 logic | `predicate, object_text, object_slug, valid_from, valid_to, is_current, recorded_at, caused_by_event, supersedes_id` |
| `events` | Events (the stampers of switches, append-only) | T4 | `slug, event_date, actor_slug, description, source_slug, recorded_at` |
| `relations` | Relation edges (temporal) | T3 | `from_slug, to_slug, type, bound_role, valid_from, valid_to, recorded_at, retract_event_slug` |

**T0 value field specification** (`data_points` table constraints):

| Field | Required | Type | Description |
|------|------|------|------|
| `page_slug` | Yes | TEXT | Slug of the owning page |
| `field` | Yes | TEXT | Data dimension name (e.g. "7-day reverse repo rate") |
| `value` | Yes | REAL | Numeric value |
| `unit` | Yes | TEXT | Unit (%, bp, CNY 100mn, CNY tn, ...) |
| `period` | Yes | TEXT | Data point in time (e.g. `2026-05`, `2025-Q1`) = valid-time |
| `recorded_at` | Yes | TEXT | Which report recorded it, on which day = transaction-time |
| `source_slug` | Yes | TEXT | source page slug (every number must have a provenance) |
| `supersedes_id` | No | INTEGER | Points to the old row when a newer report corrects the same period |
| `confidence` | No | TEXT | Confidence of this data point |
| `scope` | No | TEXT | Statistical scope notes |

**Key adjudications**:
- `7-day reverse repo rate = 1.40%` → **T0**, goes into `data_points`; the value is a number, one row per month.
- `current policy rate = 7-day reverse repo` → **T1 state**, goes into `facts`; the object is text, switched by events.
- Two different kinds of thing — they must be recorded differently.

At ingest, the Agent calls the `WikiStore` interface of `store.py` to write each table (`upsert_data` writes T0; state/relation changes go through the retirement protocol).

---

## Controlled Relation Vocabulary (relations are first-class citizens, yet still edges)

`relations[].type` **does not allow free text**; it must be chosen from the table below. Each edge has a `source→target` type constraint, and `lint` rejects out-of-vocabulary edges. Relations are **double-written**: page `frontmatter.relations[]` (gives Obsidian its edges) + the `data.db relations` table (for queries/validation); the two must agree.

| type | source → target | Meaning | Example |
|---|---|---|---|
| `operated_by` | instrument → institution | Who runs the instrument | 7-day reverse repo → People's Bank of China |
| `transmits_to` | indicator/instrument → indicator | Rate transmission (directed) | 7-day reverse repo rate → DR007 |
| `bounds` | indicator → mechanism (edge attribute `bound_role=upper/lower/center`) | Forms the corridor's upper/lower bound or center | SLF rate → (upper) interest rate corridor |
| `classified_as` | instrument → classification label | Attaches a classification dimension (multiple dimensions may coexist; labels get no pages) | 7-day reverse repo → price-based |
| `implements` | institution → mechanism | An institution implements a mechanism | People's Bank of China → interest rate corridor |
| `instance_of` | instrument/indicator → mechanism | An individual belongs to a class | MLF → monetary policy toolkit |
| `part_of` | mechanism → mechanism | Containment between mechanisms | interest rate corridor → interest rate transmission mechanism |
| `created_by` / `changed_by` | instrument/mechanism → event | An individual's creation/change is hooked to an event | MLF rate-anchor status → (changed_by) 2025-03-MLF-reform |
| `references` | analysis/source → any | Citation (provenance only, not part of the semantic graph) | Central Bank Toolkit Panorama → 7-day reverse repo |

**relations writing conventions**:

```yaml
relations:
  - {target: People's Bank of China, type: operated_by}
  - {target: price-based, type: classified_as}
  - {target: interest rate corridor, type: bounds, bound_role: center}   # bounds must carry bound_role
  - {target: 7-day reverse repo, type: operated_by, valid_from: 1900-01-01, is_current: true}  # may carry temporality
```

- `target` is the slug (no path prefix)
- `type` must come from the table above; out-of-vocabulary edges are rejected by lint
- `bounds` edges must carry `bound_role` (`upper` / `lower` / `center`)
- T3 near-permanent edges may carry `valid_from` / `valid_to` / `is_current`; retired edges are never deleted — seal `valid_to` + write `retract_event_slug`

---

## Extra Fields on source Pages

```yaml
---
title: 2026-05-25-broker-fixed-income-report
type: source
created: 2026-06-07
updated: 2026-06-07
sources: []
confidence: high
source_type: authoritative-secondary   # primary | authoritative-secondary | secondary | hearsay | inference | oral
source_origin: a broker's fixed income team
source_date: 2026-05-25         # date of the original material (not the ingest date)
source_url: ""                  # source URL (if any)
tags: [source, authoritative-secondary]
---
```

---

## Frontmatter Templates per Type

### Entity · institution

```yaml
---
title: People's Bank of China
type: entity
subtype: institution
created: 2026-06-07
updated: 2026-06-07
aliases: [central bank, PBoC, PBC]
sources: [2026-05-25-broker-fixed-income-report]
confidence: high
relations:
  - {target: interest rate corridor, type: implements}
tags: [entity, institution]
---
```

### Entity · instrument

```yaml
---
title: 7-day reverse repo
type: entity
subtype: instrument
created: 2026-06-07
updated: 2026-06-07
aliases: [OMO, open market operations, 7-day reverse repo operations]
sources: [2026-05-25-broker-fixed-income-report]
confidence: high
relations:
  - {target: People's Bank of China, type: operated_by, valid_from: 1900-01-01, is_current: true}
  - {target: price-based, type: classified_as}
  - {target: monetary policy toolkit, type: instance_of}
tags: [entity, instrument]
---
```

### Entity · indicator

```yaml
---
title: 7-day reverse repo rate
type: entity
subtype: indicator
created: 2026-06-07
updated: 2026-06-07
aliases: [OMO rate, 7-day reverse repo operation rate]
sources: [2026-05-25-broker-fixed-income-report]
confidence: high
relations:
  - {target: DR007, type: transmits_to}
  - {target: interest rate corridor, type: bounds, bound_role: center}
tags: [entity, indicator]
# Note: concrete values (e.g. 1.40%) do not go here; they go into data.db data_points
---
```

### Concept · mechanism

```yaml
---
title: interest rate corridor
type: concept
created: 2026-06-07
updated: 2026-06-07
sources: [2026-05-25-broker-fixed-income-report]
confidence: high
durability: medium              # T2 durability: high / medium / low
preconditions: [short-end rates are dominated by the central bank]
falsifiable_by: [corridor framework abandoned in favor of a single policy rate]
relations:
  - {target: SLF rate, type: bounds, bound_role: upper}
  - {target: excess reserve rate, type: bounds, bound_role: lower}
  - {target: 7-day reverse repo rate, type: bounds, bound_role: center}
  - {target: interest rate transmission mechanism, type: part_of}
tags: [concept, mechanism]
---
```

### Event

```yaml
---
title: 2025-03 MLF American-style auction reform
type: event
event_date: 2025-03-01
actor: People's Bank of China
created: 2026-06-07
updated: 2026-06-07
sources: [2026-05-25-broker-fixed-income-report]
confidence: high
retires: [MLF is the policy rate anchor]
sets: {policy rate anchor: 7-day reverse repo}
tags: [event]
---
```

### Source

```yaml
---
title: 2026-05-25-broker-fixed-income-report
type: source
created: 2026-06-07
updated: 2026-06-07
sources: []
confidence: high
source_type: authoritative-secondary
source_origin: a broker's fixed income team
source_date: 2026-05-25
source_url: ""
tags: [source, authoritative-secondary]
---
```

### Analysis

```yaml
---
title: Central Bank Toolkit Panorama
type: analysis
created: 2026-06-07
updated: 2026-06-07
sources: [2026-05-25-broker-fixed-income-report]
confidence: medium
relations:
  - {target: 7-day reverse repo, type: references}
  - {target: MLF, type: references}
  - {target: monetary policy toolkit, type: references}
tags: [analysis]
# Research topics are demoted to analysis pages; an analysis is a derived view — deleting it does not harm the ontology
---
```

---

## Body Conventions

**The body holds only narrative analysis and contextual interpretation, never data tables.**

```markdown
# 7-day reverse repo

Since 2025-03, the 7-day reverse repo has been the central bank's sole policy rate anchor
(previously [[MLF]]). It transmits via the [[7-day reverse repo rate]] to [[DR007]]
and forms the center of the [[interest rate corridor]].
As an instrument it is price-based; see [[monetary policy toolkit]].

>  The policy paradigm drifted from quantity-based to price-based over 2014→2025, with no single switch date; see [[interest rate transmission mechanism]].
```

**Body rules**:
- Use `[[slug]]` or `[[slug|display name]]` for page links
- When mentioning data, quote conclusions — **never repeat the concrete values held in frontmatter / data.db** (avoids inconsistency)
- `> ` callouts may flag important warnings (e.g. scope differences, retirement)
- Analytical content is the body's core value — it is the part YAML cannot carry

### Retirement Callout (when a state/mechanism is overturned by an event)

After a T1 state or T2 mechanism is sealed by an event, **not a single character of the body is deleted** (it was true back then — it is expired, not wrong); only add a callout at the top and amend the frontmatter:

```markdown
> [!warning] Retired (effective 2025-03): MLF is no longer the policy rate anchor;
> the 7-day reverse repo is now the sole policy rate anchor. See [[2025-03-MLF-reform]].
```

```yaml
is_current: false
valid_to: 2025-03
tags: [concept, mechanism, retired]
```

The full retirement flow (write the event page → stamp the old facts row's valid columns → wire the `caused_by_event` pointer → insert the successor row → historicize the page) lives in `_ontology.md` §6. **Core iron law: never DELETE; seal the old row's `valid_to` + insert a new row; every change is stamped by a T4 event; valid-time and transaction-time are recorded separately.**

### Page Footer: `## Relations` (recommended)

Spell out the frontmatter `relations` in natural language, so an Agent reading the body gains the structural context without parsing YAML.

```markdown
## Relations

- **Operated by**: [[People's Bank of China]] (operated_by)
- **Transmits to**: [[DR007]] (transmits_to)
- **Forms the corridor center**: [[interest rate corridor]] (bounds · center)
- **Classification**: price-based (classified_as)
```

### Data-Heavy Pages: `## Key Data` (recommended)

When a page has corresponding data points in data.db, add a lightweight section telling the Agent "structured data is queryable here". **It is not a database echo, but a data anchor; concrete values defer to data.db.**

```markdown
## Key Data

| Indicator | Period | Source |
|------|------|------|
| 7-day reverse repo rate | 2026-05 | [[2026-05-25-broker-fixed-income-report]] |
| Change vs. prior period (bp) | 2026-05 | [[2026-05-25-broker-fixed-income-report]] |

Full values, historical changes, and bitemporal records live in `data.db`.
```

---

## File Naming and Slug Unification (critical)

**A page has exactly one canonical slug, and every layer must use that same one. A single English slug = filename = `[[wikilink]]` = `data.db` primary key.**

| Layer | Use the same slug | Anti-example (split-brain) |
|----|-------------|-------------------|
| Filename | `7-day reverse repo.md` | Natural-language filename, but `reverse_repo_7d` in the DB |
| frontmatter `sources` | `["2026-05-25-broker-fixed-income-report"]` | Writing a machine id while the filename is natural language |
| `data.db` `page_slug` | `7-day reverse repo` | A second machine-style canonical slug |
| `data.db` `relations` | `from: 7-day reverse repo` | A machine-style slug |
| `[[wikilink]]` | `[[7-day reverse repo]]` | Linking via the machine id |

**Rules**:
- slug = filename minus `.md` = `page_slug` in `data.db` = `from_slug`/`to_slug` in `relations` = the `[[wikilink]]` target
- **EN-edition wikis use natural-language English slugs**, Obsidian-friendly and human-readable
- **Never invent a second machine-style id (snake_case / PascalCase)** — it creates a parallel naming scheme that fights Obsidian's filename-based links. Alias normalization across reports relies on the `aliases:` field, not on machine ids
- source pages get a date prefix: `2026-05-25-broker-fixed-income-report.md` (hyphen-separated date)
- event pages are named `date-event-name`: `2025-03-MLF-reform.md`
- **At ingest, the Agent must use the same slug to operate on both the file and data.db; two naming schemes are never allowed**

---

## Hub Page Format

The Hub page is named after the **domain name** (e.g. `Macro.md`), not `index.md`.

**Naming rationale**: Obsidian graph nodes display the filename; if every wiki used `index`, they would be indistinguishable. With the domain name as the hub filename, the graph's central node shows a recognizable domain name.

The Hub is the **first file** an Agent reads upon entering recall; it must provide both navigation and a sense of structure.

```markdown
# Macro Wiki Index

> {N} pages | Last updated: {date} | Domain: macro
>  Contested: [[Page A]], [[Page B]]
>  Retired: [[MLF is the policy rate anchor]] (since 2025-03)

## Knowledge Structure

Core topology (show only hub nodes and key edges; do not dump the whole graph):

People's Bank of China ── implements ──→ interest rate corridor
  ├── 7-day reverse repo ── operated_by ──→ People's Bank of China
  ├── 7-day reverse repo rate ── bounds(center) ──→ interest rate corridor
  ├── SLF rate ── bounds(upper) ──→ interest rate corridor
  └── monetary policy toolkit ←── instance_of ── MLF / SLF / RRR cut …

## Institutions ({N})
- [[People's Bank of China]] — monetary policy decision-making and execution body

## Instruments ({N})
- [[7-day reverse repo]] — price-based, current policy rate anchor
- [[MLF]] — quantity-based  anchor status retired (2025-03)

## Indicators ({N})
- [[7-day reverse repo rate]] — policy rate series
- [[DR007]] — interbank pledged repo weighted rate

## Mechanisms ({N})
- [[interest rate corridor]] — upper/lower-bound control framework
- [[interest rate transmission mechanism]] — transmission chain from policy rates to market rates

## Events ({N})
- [[2025-03-MLF-reform]] — MLF American-style auction reform, policy anchor switch

## Analyses ({N})
- [[Central Bank Toolkit Panorama]] — toolkit classification and transmission panorama

## Sources ({N})
- [[2026-05-25-broker-fixed-income-report]] — a broker's fixed income team report
```

**Hub page rules**:
- The top header lists contested and retired pages (if any), so an Agent entering recall knows at first glance which knowledge is unreliable / expired
- `## Knowledge Structure` shows a text tree of 5-8 hub nodes + key relation edges + status markers, giving the Agent a global structural sense in one read
- The categorized lists are grouped by node type (institutions/instruments/indicators/mechanisms/events/analyses/sources), one entry per line as `[[slug]] — one-line description`

---

## log.md Format

```markdown
# Macro Wiki Log

## 2026-06-07 14:30 — ingest
- Source: 2026-05-25-broker-fixed-income-report
- Created: institutions/People's Bank of China, instruments/7-day reverse repo, indicators/7-day reverse repo rate, mechanisms/interest rate corridor
- Updated: (none)
- Conflicts: (none)

## 2026-06-07 15:00 — ingest (retirement protocol)
- Source: 2026-05-25-broker-fixed-income-report
- Created: events/2025-03-MLF-reform
- Retired: facts "MLF is the policy rate anchor" sealed valid_to=2025-03, is_current=0, caused_by_event=2025-03-MLF-reform
- Set: facts "policy rate anchor = 7-day reverse repo" valid_from=2025-03, is_current=1
- Conflicts: (none; old row kept, not deleted)
```

---

## Validation Rules

| Rule | Requirement |
|------|------|
| Frontmatter complete | The six fields `title` `type` `created` `updated` `sources` `confidence` must exist |
| type value legal | `entity` / `concept` / `event` / `analysis` / `source` |
| subtype legal | `type: entity` must have `subtype ∈ {institution, instrument, indicator}` |
| Event fields complete | `type: event` must have `event_date` + `actor` |
| Mechanism time-tier field | `type: concept` should have `durability` (T2 durability) |
| No values in frontmatter | Frontmatter never contains concrete values; values go into `data.db data_points` |
| data field conformance | Every T0 data point must have `value` `unit` `period` `recorded_at` `source_slug` |
| Retirement append-only | Every T1/T2 change: seal old row's `valid_to` + insert new row, never DELETE; every change has `caused_by_event` |
| relations controlled | Every relation has `target` + `type`; `type` must belong to the controlled vocabulary; `bounds` must carry `bound_role` |
| sources non-empty | Except for the source type, `sources` has at least one slug |
| Date format | `YYYY-MM-DD` |
| Slug matches filename | Filename (minus `.md`) = slug = `page_slug` = `[[wikilink]]` target; no machine-id duplicate |

---

## Confidence Update Rules

| Event | Confidence change |
|------|-----------|
| A new source confirms existing data (data agrees) | → `high` |
| A new source updates existing T0 data (newer period / more authoritative source) | upsert a new row; the old row is kept via `recorded_at` / `supersedes_id` |
| A new source contradicts existing data and it cannot be adjudicated | That field's confidence → `contested` |
| A T1/T2 state is overturned by an event | Run the retirement protocol (seal `valid_to` + insert new row + `caused_by_event`); do not change confidence, change `is_current` |
| lint finds a field in data without a source | → `low` |
| A page untouched by ingest for 6 months | lint suggests marking it "pending verification" |
