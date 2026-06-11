---
name: auto-wiki
version: 0.3.0
description: |
  Knowledge compiler: teaches the agent to incrementally compile source files into a persistent wiki, enabling cross-session knowledge accumulation.
  Runtime dependencies: Python 3.8+ (stdlib + pydantic). Optional enhancements: WebSearch (active search), external MCP validators (logic validation).

  Five modes, auto-routed by user intent:

  recall → User wants questions answered from accumulated knowledge.
  Trigger words: recall, knowledge mode, open the wiki, answer with the wiki, according to the wiki,
  based on what we've accumulated, check the wiki, does the wiki have, we researched this before, from our earlier notes.

  ingest → User provided new material to compile into the wiki.
  Trigger words: ingest, compile, compile this, digest this, study this, archive this,
  add this in, accumulate, research this, organize this for me, add to the knowledge base.

  query → User asked a specific question and wants an answer from the wiki (one-shot).
  Trigger words: query, answer from the wiki, what does the wiki say, look it up.

  lint → User wants to check wiki health.
  Trigger words: lint, check the wiki, wiki health, clean it up, any contradictions.

  deep-dive → User wants the agent to find knowledge gaps automatically and fill them.
  Trigger words: deep-dive, deep dive, fill the gaps, hunt for gaps, go hard,
  auto-complete, knowledge completion, comprehensive fill.
  Note: deep-dive is not a standalone mode; it is a combined pipeline of lint (Coverage) + ingest (search-fill).

  Routing rules: if the user provides no new material but mentions the wiki or domain knowledge → recall.
  If the user provides files or large blocks of text → ingest.
  If the user says "deep-dive" or "go hard" → run the deep-dive pipeline.
  If unsure → ask the user.
---

# Knowledge Compiler

> The agent does research, pulls data, writes reports — the wiki threads these outputs together. The more you use the agent, the better it understands your domain.

## Runtime Dependencies & Permission Declaration

| Dependency | Required? | Notes |
|------|--------|------|
| **Python 3.8+** | Required | `schema.py` (frontmatter validation), `store.py` (SQLite data management), `build_index.py` (FTS5 indexing) are all Python scripts. Stdlib only (`sqlite3`, `json`, `pathlib`) + `pydantic` |
| **pydantic** | Required | Needed by `schema.py` frontmatter validation. `pip install pydantic` |
| **Filesystem write** | Required | Creates and edits Markdown, SQLite, and `.obsidian/` config under `wiki/{topic}/`. **Confirms the location with the user when first creating `wiki/`** |
| **WebSearch / WebFetch** | Optional | Needed for active mode (agent searches for materials autonomously). Not needed for passive mode (user provides files) |
| **External validator (MCP)** | Optional | Only invoked by lint when the wiki declares a validator. Silently skipped when unreachable, zero impact. **No user credentials required** — `Mcp-Session-Id` is the standard MCP protocol session handshake, completed automatically by the agent |
| **Search-class MCP** | Optional | deep-dive and active ingest can use domain data MCPs to enhance search quality. Falls back to WebSearch when absent |

> **Core promise**: passive mode (user provides files → agent compiles) only needs Python 3 + file read/write, zero network dependencies. All network calls are optional enhancements, and an environment check on first use informs the user of what is available.

## Quick Start

```
User: /auto-wiki recall personal-pension
Agent: [Scan wiki/personal-pension/ → read hub page ({Domain}.md, named in English) → load data.db summary]
Agent: Entered recall mode. Current wiki: 22 pages / 8 data points / 2 contested.
       From now on I will check the wiki before answering.

User: What causes the low participation rate?
Agent: [Read wiki pages such as enrollment-friction, tax-incentive-effect]
Agent: Based on the 6 sources accumulated in the wiki... (citing specific pages and data)
        Note: the tax-incentive effect is contested (77.8% vs 25%), see [[participation-willingness]]
```

## Core Idea

The agent does research, writes reports, and pulls data for you every day — then forgets it all. Next time you ask about the same domain, it starts from zero.

This Skill solves one thing: **give the agent a knowledge base that keeps accumulating.**

It is not RAG (ad-hoc retrieval from a document pile every time) — it is compilation. After reading a source file, the agent writes the key information into existing wiki pages, comparing against old knowledge, merging, and flagging conflicts. Before executing any future task, it reads the wiki first and works from the accumulated base.

## Four Modes

| Mode | Trigger | What the agent does |
|------|------|-------------|
| **recall** | `recall` / `recall {topic}` | Load wiki context; all subsequent questions check the wiki before answering |
| **ingest** | User provides source files or text | Read source → search existing wiki → compare old vs new → update/create pages → update index |
| **query** | User asks a question (one-shot) | Read hub page → find relevant pages → synthesize an answer → archive valuable analysis |
| **lint** | User says "check the wiki" | Scan all pages → merge duplicates → archive stale pages → report contradictions and health |
| **deep-dive** | `deep-dive` / "go hard" | Run Coverage lint → show gap report → user confirms → search + ingest to fill gaps |

> deep-dive is not a fifth standalone mode — it is a combined pipeline of lint (Coverage) and ingest (with search tools). Requires search tools (active mode).

recall mode vs query: query is a one-shot operation (one question, one wiki lookup). recall mode is a persistent state — once entered, every question in the conversation goes through the wiki first.

---

## recall Mode

### Entering

Triggered when the user says `/auto-wiki recall` or `/auto-wiki recall {topic}`.

The agent executes:

1. **Scan the `wiki/` directory** and list available wiki topics
2. If the user specified a topic → load that wiki; if not → list the available topics for the user to choose
3. **Read the hub page** (`{Domain}.md` — the main page in the wiki root named after the domain in English, matching meta.yaml `name`) → get the full page list and structure
4. **Read the data.db summary** → `python references/store.py dump wiki/{topic}/` to get counts of data points, relations, contested items
5. **Report to the user**:
   ```
   Entered recall mode: {topic}
   - Pages: {N} (sources: X, entities: Y, concepts: Z)
   - Data points: {N} | Relations: {N} | Contested: {N}
   From now on I will check the wiki before answering. Say "exit recall mode" to return to normal.
   ```

### Answering Flow

In recall mode, for each user question:

1. **Extract keywords from the question** (entity names, concept names, indicator names)
2. **Match relevant pages in the hub page** (title + description)
3. **Query relevant data points in data.db**:
   ```sql
   SELECT * FROM data_points WHERE field LIKE '%keyword%' OR page_slug LIKE '%keyword%'
   ```
4. **Read the matched wiki pages** (typically 2-5), expanding one hop along wikilinks
5. **Synthesize the answer**, and it must:
   - Cite specific pages: `[[slug]]`
   - Cite specific data: value + unit + period + source
   - Proactively flag any contested information involved
   - If the wiki lacks the information, say explicitly "the wiki has no accumulation on this; suggest ingesting XX"
6. **Never fabricate information the wiki does not contain.** Better to say "I don't know" than to pretend the wiki has it

### Exiting

Exit when the user says `exit recall`, switches to another operation (ingest/lint), or starts a new topic.

---

## Execution Flow

### Phase 0: Identify Target Domain & Ontology Type

On receiving user input, determine three things: **operation type**, **target domain wiki**, **ontology type**.

> **Wikis are organized by domain, not by research topic.** A research topic (e.g. "the Fed's hiking cycle") is demoted to a single page under `{domain}/analyses/` rather than getting its own wiki. First identify which domain the knowledge belongs to (macro / credit / ...), then land it in that domain's directory. See `references/storage-spec.md`.

| User input | Operation | Target domain wiki | Ontology type |
|---------|------|-----------|---------|
| "Organize this monetary-policy research report for me" + file | ingest | macro | domain |
| "Ingest into macro" + file | ingest | macro | domain |
| "Research Charlie Munger" + material | ingest | charlie-munger | cognitive |
| "How much room is left for PBoC reserve-requirement cuts?" | query | macro | — |
| "Check the macro wiki" | lint | macro | — |

The **ontology type** determines the wiki's node types and collection strategy:

| Ontology type | Research object | Node types | Authoritative contract / reference |
|---------|---------|---------|------|
| **domain** | A domain (institutions, instruments, indicators, mechanisms, events) | Entities (institutions/instruments/indicators) · Concept-mechanisms · Events · Analyses · Sources | Each domain's `wiki/{domain}/_ontology.md` + `references/ontology-types/domain.md` |
| **cognitive** | A person (mental models, decision-making style) | mental-model · Concepts · Sources · Analyses | `references/ontology-types/cognitive.md` |

**Each domain wiki's ontology is defined by its own `wiki/{domain}/_ontology.md` contract** (node types, controlled relation vocabulary, six-tier time model, retirement protocol); read it before ingest/recall. A domain uses one ontology type only — never mix cognitive and domain structures within the same domain.

**If the wiki directory does not exist**, first confirm the creation location with the user (default `wiki/{topic}/` under the current repository root), then create the initial structure per `references/storage-spec.md` (including meta.yaml, hub page template, log.md template). `wiki/` goes under git version control and must **not** be added to `.gitignore` — it has to appear in the Obsidian graph (do not use a `.wiki/` dot directory; Obsidian hides dotfolders).

**Domain seed**: if the target domain has a matching seed file (`seeds/{name}.md`), declare `seed: {name}` in meta.yaml. The seed provides a standard term vocabulary, relation templates, and no-confusion rules, so the wiki grows from a normalized starting point. Domains without a seed grow freely — both paths work. Seeds are community-contributable plugins: anyone can write a markdown file for their own vertical. See `references/seed-ontologies.md`.

**On first use**, run the environment check (see `references/source-validation.md`) and inform the user of currently available capabilities (passive mode vs active mode).

### Reference Loading Strategy

Do not read all references at once. Load on demand by operation type:

| Operation | Must read | Read on first time | Read when tools available |
|------|------|---------|-----------|
| **ingest** | `ingest-protocol.md`, `wiki-format.md`, `schema.py` | `storage-spec.md` (when wiki doesn't exist), `seed-ontologies.md` + `seeds/{name}.md` (when meta.yaml declares a seed) | `fact-check.md`, `source-validation.md` |
| **query** | `query-protocol.md` | — | — |
| **lint** | `lint-protocol.md`, `schema.py` | — | `validators/{name}.md` (when the seed declares a validator) |
| **deep-dive** | `lint-protocol.md`, `ingest-protocol.md`, `source-validation.md`, `wiki-format.md`, `schema.py` | `storage-spec.md` (when wiki doesn't exist) | `fact-check.md` |

**Not needed**: `scaling.md` is only relevant when page count > 500; `ontology-types/` only when creating a new wiki and deciding its type.

### Phase 1: Ingest (Knowledge Compilation)

**This is the core operation.** Detailed protocol in `references/ingest-protocol.md`.

Brief flow:

1. **Read the source file** and extract key information
2. **Validate key data** (if tools are available) — see `references/fact-check.md`
3. **Write the source summary page** (`sources/{date}-{slug}.md`)
4. **Search the wiki for existing related pages** (read the hub page, grep key entity names)
5. **Compare new vs old information page by page**:
   - New info **supports** an existing conclusion → add citation, raise confidence
   - New info **overturns** an existing conclusion → write the value into data.db (old value auto-enters the history table), rewrite the body analysis
   - New info **contradicts** and cannot be adjudicated → present both claims side by side, confidence → `contested`
6. **Create new pages** (only for entities/concepts the wiki does not yet have)
7. **Update the hub page + append to log.md**
8. **Schema validation** — run `python references/schema.py {page.md}` on every page created/modified in this pass, ensuring frontmatter conforms. Fix immediately on failure before continuing

After ingest, report to the user:
```
Ingested into the {topic} wiki:
- Created: {N} pages (list them)
- Updated: {N} pages (list + brief reason for each change)
- Conflicts: {N} (list the contradictions)
- Validation: all {N} pages passed / {M} pages have issues (list them)
```

### Phase 2: Query (Knowledge Lookup)

**Detailed protocol in `references/query-protocol.md`.**

1. Read the hub page and identify pages relevant to the question
2. Read the matched pages + expand one hop along wikilinks
3. Synthesize an answer from page content, **citing source pages**:
   ```
   Based on 5 source files accumulated in the wiki:
   ... analysis ...
   Sources: [[alpha-corp]], [[2026-policy-doc]]
   ```
4. If contested information is involved, flag the contradiction explicitly
5. If the answer contains valuable new analysis, suggest archiving it

**If the wiki lacks enough information to answer**, state the gap explicitly:
```
The wiki has insufficient information on XX; currently only 2 related source files.
Suggest ingesting more material about XX.
```

### Phase 3: Lint (Knowledge Governance)

**Detailed protocol in `references/lint-protocol.md` (7 checks + health report format).**

Lint has two tiers:

| Tier | Trigger | Checks | Cost |
|------|------|--------|------|
| **Structural** (default) | `lint` / "check the wiki" | Validation, Orphan, Broken Link, Staleness | Full scan, deterministic |
| **Semantic** (on demand) | "deep lint" / "check contradictions" | Contradiction, Duplication, Coverage | Agent semantic understanding, scope-controlled |

1. **Structural tier**: automatically scan all pages; fix formatting, broken links, orphan pages, staleness flags
2. **Semantic tier** (user-triggered): detect contradictions, duplication, coverage gaps. Wiki < 50 pages → full scan; 50-200 pages → only pages touched by ingests in the last 30 days; > 200 pages → user must specify scope
3. **Report health**:
```
Wiki health report: {topic}
- Total pages: 42 (entities: 15, concepts: 10, sources: 12, analyses: 5)
- Health: good
- Structural fixes: fixed 1 broken link, archived 1 stale page
- [Semantic] Pending human confirmation: 2 contradictions (listed)
- Suggestion: domain XX has few source files (only 1); consider adding more
```

### Phase 4: Deep-Dive (Knowledge Completion Pipeline)

**deep-dive = lint (Coverage) + ingest (search-fill)**. Not a standalone mode — a combined pipeline.

**Prerequisite**: requires search tools (active mode). Without search tools, only output the gap report; do not auto-fill. Prompt the user to ingest manually.

**Flow**:

```
1. Run the lint Coverage check (5 gap-detection categories)
   → Output a structured Gap Report (see lint-protocol.md)

2. Show the Gap Report and ask the user to confirm
   → The user may: accept all / pick a subset / narrow the scope / cancel
   → This step cannot be skipped — it prevents unsupervised bulk writes

3. For each confirmed gap, run the from-lint ingest flow
   → Search → user confirms sources → standard ingest
   → See the From-Lint section of ingest-protocol.md

4. Output the completion report: filled / unfilled / suggestions
```

**Trigger words**: `deep-dive`, "deep dive", "fill the gaps", "hunt for gaps", "go hard"

**Example**:
```
User: deep-dive treasury-futures
Agent: [Running Coverage lint...]
Agent: Found 6 knowledge gaps:
       1. [high] page_missing: stock-bond-correlation (referenced by 4 pages)
       2. [high] concept_missing: basis (mentioned in 5 entity pages)
       3. [medium] single_source: treasury-futures-basics (only 1 source)
       ...
       Which should I fill? (all / pick numbers / cancel)

User: 1, 2

Agent: [Searching "stock-bond correlation treasury futures"...]
Agent: Found 2 candidate sources:
       - [authoritative-secondary] CICC fixed-income report "Stock-Bond Correlation Analysis" ← recommended
       - [secondary] a WeChat blog post ← skip (blacklisted channel)
       Confirm using the CICC report?

User: Confirm

Agent: [Running standard ingest → created concepts/stock-bond-correlation.md]
Agent: Completion done. Created 2 pages, updated 0, 1 gap unfilled (suggest providing material manually).
```

---

## Wiki Page Format

See `references/wiki-format.md`. In brief:

- Every page is markdown with frontmatter (title, type, created, updated, sources, confidence; entities additionally have subtype/aliases, mechanisms have durability, events have event_date)
- domain node types: **entities** (subtype institution/instrument/indicator) · **concept-mechanisms** · **events** · **analyses** · **sources** (cognitive wikis additionally have mental-model)
- Numeric values are never nodes (they go into data.db); classification tags are edges, not pages; relations use the controlled relation vocabulary
- Use `[[slug]]` for inter-page links (slug = filename = wikilink = data.db primary key, English slugs)
- The hub page is named after the **domain name in English** (e.g. `Macro.md`) — it is the directory page + graph hub; `log.md` is the operations log

## Ontology Type Reference

When the research object is a **domain**, the authority is that domain's `wiki/{domain}/_ontology.md` contract; collection strategy in `references/ontology-types/domain.md` — nodes emphasize institution/instrument/indicator entities, mechanisms, events, and quantitative indicators (values go into data.db).

When the research object is a **person**, see `references/ontology-types/cognitive.md` — nodes emphasize mental models, heuristics, value systems, expressive style.

Both share the same wiki infrastructure (ingest/query/lint, data.db bitemporal tables, retire-never-delete); they differ only in node taxonomy and collection emphasis.

## Vertical Domain Adaptation

The Skill core is a domain-agnostic compilation engine. Vertical-domain expertise is injected through two plugin layers:

| Layer | Carrier | Role | Required? |
|----|------|------|--------|
| **Seed** | `seeds/{name}.md` | Cold-start vocabulary: standard terms, relation templates, no-confusion rules | Optional |
| **Validator** | `validators/{name}.md` | Runtime logic validation: relation legality, completeness of required relations | Optional |

Without plugins, the wiki grows freely — good for exploratory research. With plugins, the wiki starts from industry standards: normalized concept naming, clear relation structure, detectable logic gaps.

**Community-contributable**: write a seed file (markdown) for your vertical, declaring 20-50 core terms plus no-confusion rules, and wikis in that domain will grow from a normalized starting point.

Currently available:
- `seeds/fibo-pensions.md` — enterprise annuities / pensions (based on the FIBO standard)
- `validators/fibo-mcp.md` — FIBO SPARQL logic validation (627K inferred triples)

## What This Skill Does Not Do

- **No vector retrieval.** Small scale relies on the hub page + grep; large scale relies on SQLite FTS5 + BM25 (see `references/scaling.md`). Vector retrieval is left to platform-level tools.
- **No multi-user collaboration.** The wiki directory is local files — one user, one wiki.
- **No replacement for professional data tools.** Use the corresponding MCP/tools for domain data; this Skill only catches their output and compiles it into the wiki.

## Relationship to Other Tools

This Skill replaces no professional tool — it **chains** them:

```
Any research tool produces analysis → ingest into the matching wiki
Any data tool pulls data            → ingest into the matching wiki
Domain seeds provide a starting line → standard terms + no-confusion rules
External validators correct logic    → lint checks knowledge-structure integrity

Before the next task, the agent reads the relevant wiki first → works with accumulated knowledge
```
