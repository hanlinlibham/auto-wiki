# Domain Research Collection Strategy

> Applies when researching a **domain** — an objectively existing field organized around a central entity (e.g. "macro monetary policy", "enterprise annuity (企业年金)", "regulation of some industry"). Typical output: entity pages (institutions/instruments/indicators), concept pages (mechanisms), event pages, relation network.
> This document is the **domain-agnostic collection engine spec**. Macro monetary policy is used as the running example below (central bank, 7-day reverse repo, interest rate corridor, MLF reform, ...), but the rules apply to any domain.
> **The authoritative contract is each domain's own `_ontology.md`** (e.g. `wiki/macro/_ontology.md`). This page is the generic engine-side explanation; on conflict, the domain contract wins.

## 0. Three Governing Principles (rules first)

1. **A domain, not a topic**: the wiki is organized by **domain** — `wiki/macro/`, `wiki/annuity/` are each an independent ontology realm with their own `_ontology.md` and central entity. **A research topic never gets its own domain** — it is demoted to **one page** under that domain's `analyses/` directory (a derived view; deleting it does not affect the ontology).
2. **Node / data / edge trichotomy**:
   - **A value is never a node** — `7-day reverse repo rate = 1.40%` gets no page; it goes into `data.db`. The graph contains only the named series "7-day reverse repo rate", never the point "1.40%".
   - **A relation is an edge, not a node** — "the central bank operates the 7-day reverse repo" is one `operated_by` edge, not a node called "operates".
   - **A classification label is an edge, not a node** — in "the 7-day reverse repo is a price-based instrument", "price-based" is one `classified_as` edge; no page.
3. **Compilation is one-way**: `Inbox (human prose) → ingest → wiki (ontology artifacts)`. This collection strategy only covers the **wiki accumulation phase**, crystallizing scattered source text into the ontology; it never generates Inbox content back from the wiki.

## Collection Dimensions (each item notes which tier of the six-tier time model it lands in, see §Time Placement)

### 1. Policy, Regulation & Institutional Documents
- **Find**: ministry regulations, industry standards, regulatory notices, formal documents issued by acting bodies
- **Extract**: ① issue date + acting body (→ **event**, T4) ② instruments or mechanisms created/changed (→ entity/concept) ③ causal chains or definitions of core rules (→ T2 logic) ④ repeal/replacement relationships (→ retirement protocol)
- **Output**: `sources/` page + (as needed) `events/` page + `instruments/`, `mechanisms/` pages + `relations` edges (`created_by`/`changed_by`/`implements`)

### 2. Domain Data & Statistics
- **Find**: official statistical bulletins, association annual reports, disclosure standards
- **Extract**: ① the **named time series** itself (e.g. "M2 YoY", "DR007") → create an `indicators/` entity page whose identity is the series ② the **value** at each point in time → no page; into `data_points` (T0) ③ definition/statistical-scope notes → into the indicator page body
- **Output**: `indicators/` entity page + `data_points` rows (values never enter page bodies as the source of truth)

### 3. Research Reports & Analytical Judgments
- **Find**: broker research, think-tank reports, academic papers, white papers
- **Extract**: ① core conclusions and causal chains (→ T2 durable logic, written into mechanism/analysis pages) ② agreement/contradiction with existing assertions (→ trigger the retirement protocol or coexistence annotation) ③ data sources behind the evidence (→ T0/`source_slug`)
- **Output**: `sources/` page + `analyses/` page (that report's derived judgments) + updates to existing entity/concept/mechanism pages

### 4. Cases, Instances & Event Post-mortems
- **Find**: typical cases, product solutions, reform retrospectives, judicial precedents
- **Extract**: ① a one-off change with a definite **date + actor, fixed once it happened** → **event**, T4 ② participants (→ entities) ③ timeline nodes → archived as individual events, never lumped into one paragraph of prose
- **Output**: `sources/` page + `events/` page + `relations` edges hanging instrument/mechanism creations and changes off the events

### 5. Market Participant Profiles
- **Find**: institution websites, annual reports, qualifications, market share, org structure
- **Extract**: ① the institution itself (acting subject with a proper name) → `institutions/` entity page ② the **roles the institution plays** (trustee / custodian / market maker ...) → roles are edges or classification labels, **never merged into one page with the institution** ③ essential affiliation relations → `relations` (T3 near-permanent edges)
- **Output**: `institutions/` entity page + `relations` (institution vs role on separate axes, see no-confusion rules)

### 6. Historical Evolution & Institutional Change
- **Find**: institutional evolution histories, chronologies, policy iteration threads
- **Extract**: ① the **discrete switch event** at each key node → `events/` (T4) ② the **regime-state proposition** being switched (e.g. "current policy rate anchor = 7-day reverse repo") → `facts` temporal table (T1, switched by the stamping event) ③ gradual drift (e.g. the 2011-ish shift from quantity-based to price-based) → plant a proxy event and accept the modeling distortion
- **Output**: `events/` page + `facts` temporal rows + historicized mechanism page body (old conclusions are kept, with a retirement callout)

## Node Type Identification — the individual-vs-class cut

### Core criterion (one sentence)

> **"Can I point a finger at 'this very one', and will the same name still point to the same thing next year?"**
> Yes → **entity (individual)**; no — you must first explain "how it works / how it is defined" before anyone understands it → **concept (class / mechanism)**.

**"Does it have data / does it have structure" will deceive you** — the interest rate corridor has upper/lower bounds and numbers, yet it is still a **concept** (there is no single proper-named thing that created it; you must explain the mechanism first). The only reliable criterion is "can you point a finger at the one". **"Abstract or not / has data or not" is not the criterion.**

### Node Type Table (domain-agnostic)

| Type | Subdirectory | Criterion | Macro examples |
|---|---|---|---|
| **Entity · institution** | `institutions/` | Acting subject with a proper name | People's Bank of China, Federal Reserve |
| **Entity · instrument** | `instruments/` | Proper-named tool/means created and operated by some institution | 7-day reverse repo, MLF, SLF, RRR cut |
| **Entity · indicator** | `indicators/` | Repeatedly queryable **named time series** (its identity is the series, not any day's value) | 7-day reverse repo rate, LPR, M2, DR007 |
| **Concept · mechanism** | `mechanisms/` | Mechanism/framework understandable only via intensional definition | interest rate corridor, rate transmission mechanism, monetary policy toolbox |
| **Event** | `events/` | Definite date + actor; happens once and never recurs | 2025-03 MLF American-auction reform, 2024-10 launch of outright reverse repo |
| **Analysis** | `analyses/` | Research judgment derived from the nodes above (derived view; deletion does not affect the ontology) | Central bank toolbox panorama, Fed hikes and asset classes |
| **Source** | `sources/` | Carrier page for one report/article's original text; all assertions trace back to it | 2026-05-25-some-broker-fixed-income-report |

**Classification labels are not nodes and get no pages** — dimensions like "quantity-based / price-based / structural" that bucket a pile of things are multi-dimensional tags attached to instruments (`classified_as` edges); the graph can bucket and color by them, but the label itself is not a page.

### Classification Decision Tree (walk every noun through it at ingest)

```
For each noun in the source material:
├─ Is it "an indicator's value/definition at some point in time"? → not a node; into data.db (T0 data_points)
├─ Can you point a finger at "this very one"?
│   ├─ Is it an acting subject (institution)?            → institutions/
│   ├─ Is it a tool/means operated by some institution?  → instruments/
│   └─ Is it a named series you can repeatedly query?    → indicators/
├─ Definite date + actor, fixed once it happened?        → events/ (T4)
├─ Is it a label used to bucket a pile of things?        → classified_as edge (no page)
├─ Is it a framework that needs its mechanism defined first? → mechanisms/ (concept)
└─ Is it a judgment I derived from the above?            → analyses/
```

### No-confusion Rules (Anti-patterns)

Macro is the example; similar variants exist in every domain:

| Easy to confuse | Correct approach | Rationale |
|----------|---------|---------|
| **Institution vs role** | Institution gets an entity page; a role is an edge/classification label, no page | One institution can play multiple roles (a central bank is both market maker and regulator); a "role" does not point to "this very one", so it is not an entity |
| **Indicator vs observation** | Indicator gets an `indicators/` page (named series); observations go into `data_points` | "7-day reverse repo rate" is a series entity; "2026-05 that rate = 1.40%" is a T0 value — **a value is never a node** |
| **Instrument vs its rate value** | Instrument gets an `instruments/` page; its rate is an associated `indicators/` series, with each period's value in data.db | "7-day reverse repo" (instrument) ≠ "7-day reverse repo rate" (indicator series) ≠ "1.40%" (T0 value) — keep the three layers apart |
| **Classification label vs instance** | Label is a `classified_as` edge, no page; the instance gets an entity page | "price-based / quantity-based" is a bucketing dimension (edge); "7-day reverse repo" is the bucketed instrument (entity) |
| **Concept structure vs concept-as-node** | The corridor gets a `mechanisms/` concept page; its bounds are drawn with `bounds` edges | The corridor has values and structure but is still a concept; its upper/lower/center are connected by `indicator →(bound_role) mechanism` `bounds` edges, not by writing values into the page |
| **Event vs state** | Event gets an `events/` page (one-off, never reverts); state goes into the `facts` temporal table (true for a period, switched by an event) | "2025-03 MLF reform" is a T4 event; "current policy rate anchor = 7-day reverse repo" is a T1 state, switched by that event's stamp |

**Create-new vs update**: first search the domain hub page and each page's `aliases:` field (OMO = 7-day reverse repo, MDS = outright reverse repo); if a page exists, update it — **never create a synonymous page**.

## Placing Collection Output in the Six-Tier Time Model (after extraction, which table does each piece of knowledge land in)

Every collected piece of knowledge gets a time tier, which decides where it is recorded:

| Tier | What it is | Signal at collection time | Lands in |
|---|---|---|---|
| **T0 observation** | One measurement of an indicator at one point in time | "Change the period and it's a new record" | `data_points` (value is a number; fill `recorded_at`/`source_slug`) |
| **T1 state / regime state** | A proposition true for a stretch of time, switched by an event | "Will be switched by a dated event" | `facts` temporal table (object is text/slug) |
| **T2 durable logic** | Cross-cycle causal chain/definition, falsifiable | "It's an if→then, falsifiable by structural change" | mechanism page body + `durability`/`preconditions`/`falsifiable_by` fields (may also enter `facts`) |
| **T3 entity / near-permanent relation** | Objectively existing things and essential affiliations | "Has a queryable proper name, or is an essential-affiliation edge" | entity page + `relations` (with `valid_from`/`valid_to`) |
| **T4 event** | Has date + actor; fixed once it happened | "Once it happened it never changes" | `events` table + `events/` page, **append-only** |
| **T5 type axiom** | Constrains "the shape of other knowledge" | "Governs the shape of a whole class of knowledge" | domain `_ontology.md` + DB CHECK constraints |

> **Key ruling**: "current policy rate = 7-day reverse repo" is a **T1 state** (`facts`, object is text, switched by an event); "7-day reverse repo rate = 1.40%" is a **T0 measurement** (`data_points`, value is a number, one row per month). Two different kinds of thing; they must be recorded differently.

**Three iron laws of recording** (mandatory at ingest):
1. **Retire, never delete**: any "change" in T1/T2/T3 means "seal the old row's `valid_to` + insert a new row" — **never DELETE**. Overwriting in place is only allowed for T0 same-period corrections.
2. **Bitemporal axes kept apart**: every assertion records two time axes — `valid_from/valid_to` (when it was true in the world) + `recorded_at` (which of my reports recorded it). A change of `valid_from` = the world changed; touching only `recorded_at` = my own erratum. Never mix them.
3. **Event stamping**: every change to a T1/T2 "current state" must trace back to a T4 event (`caused_by_event`).

## Controlled Relation Vocabulary (relations are first-class citizens, yet still edges)

Relation `type` **never allows free text**; it must be chosen from the controlled vocabulary. Each edge has a `source→target` type constraint; `lint` rejects out-of-bound edges.

| type | source → target | Meaning | Example |
|---|---|---|---|
| `operated_by` | instrument → institution | Who operates the instrument | 7-day reverse repo → People's Bank of China |
| `implements` | institution → mechanism | Institution implements a mechanism | People's Bank of China → interest rate corridor |
| `transmits_to` | indicator/instrument → indicator | Transmission (directed) | 7-day reverse repo rate → DR007 |
| `bounds` | indicator → mechanism (edge attr `bound_role=upper/lower/center`) | Forms the corridor's upper/lower bound or center | SLF rate →(upper) interest rate corridor |
| `classified_as` | instrument → classification label | Attach a classification dimension (multiple dimensions may coexist; labels get no pages) | 7-day reverse repo → price-based |
| `instance_of` | instrument/indicator → mechanism | Individual belongs to a class | MLF → monetary policy toolbox |
| `part_of` | mechanism → mechanism | Containment inside mechanisms | interest rate corridor → rate transmission mechanism |
| `created_by` / `changed_by` | instrument/mechanism → event | Hang an individual's creation/change off an event | MLF rate-anchor status →(changed_by) 2025-03-MLF-reform |
| `references` | analysis/source → any | Citation (traceability only; not in the semantic graph) | Central bank toolbox panorama → 7-day reverse repo |

**Relation triple-write (three places, one truth)**: page `frontmatter.relations[]` (for Obsidian edges) + `data.db relations` table (for query/validation, with `valid_from`/`valid_to`) + natural `[[wikilink]]` references in the body.

## Naming & Directory Discipline

- **One single slug = filename = `[[wikilink]]` = `data.db` primary key**. Do **not** invent a second PascalCase id scheme (it creates a parallel naming system that fights Obsidian's filename-based links). Cross-report dedup relies on the `aliases:` field.
- **wiki/ is a visible directory**: tracked in git, included in the Obsidian graph. **No `.wiki/` dot-directory** (Obsidian hides dotfolders; they vanish from the graph).
- **Type = directory = graph coloring**: keep top-level directories ≤ 6 (≤ 6 colors; 9 colors are indistinguishable to the eye).

## Page Structure Templates

### Entity page (institution / instrument / indicator)

Sections: **Overview** (one-sentence positioning — the one you can point a finger at) → **Key Attributes** (an instrument's tenor/rate, an indicator's definition and timepoint, with sources noted; the source of truth for values is data.db, the body only excerpts) → **Relations** (wikilinks + frontmatter `relations` to related entities/concepts) → **History** (timeline pointing to `events/` pages; outdated states are historicized, never deleted)

Key frontmatter fields: `type: entity` + `subtype: institution|instrument|indicator` + `aliases` + `relations`.

### Concept page (mechanism)

Sections: **Definition** (one paragraph, with source) → **Mechanism** (how it works — the very reason it must be defined intensionally) → **Structure** (e.g. corridor bounds, via `bounds` edges instead of stuffing values into the body) → **Durability & Failure Conditions** (T2: `durability` + `preconditions` + `falsifiable_by`) → **Disambiguation** (differences from [[similar concept]])

Key frontmatter fields: `type: concept` + `durability: high|medium|low` + `preconditions` + `falsifiable_by` + `relations`.

### Event page

Sections: **Event** (one sentence: when, who did what) → **Impact** (which instruments/mechanisms/states it created or changed) → **Retirement Declaration** (`retires:` old propositions, `sets:` new states)

Key frontmatter fields: `type: event` + `event_date` + `actor` + `retires` + `sets`. Event pages are **append-only — never edited after creation**.

### Analysis page

The **derived judgments** of one report or one research topic. Sections: **Conclusions** → **Evidence** (`references` to entities/concepts/events) → **Agreement/Contradiction with Other Sources**. Deletion does not affect the ontology.

### Source page

Sections: **Basic Info** (issuer/date/document number) → **Core Content** (3-5 key points) → **Involved Nodes** (wikilink list, helping ingest locate update targets)

All page frontmatter follows wiki-format.md (title / type / created / updated / sources / confidence), with the domain's `_ontology.md` templates as the authority.
