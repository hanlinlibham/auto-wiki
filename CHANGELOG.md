# Changelog

## 0.3.0 — 2026-06-11 (CN skill; EN pending re-translation)

### Changed (breaking)
- **Visible `wiki/` replaces `.wiki/`** — dotfolders are hidden by Obsidian and never appear in the graph; knowledge must live in a visible directory (`.obsidian/` config is the only allowed dot-dir)
- **Domain-based organization replaces topic-based** — one top-level dir per domain (macro/credit/…); research topics demote to a page under `{domain}/分析/`, sharing entities/concepts/events across topics
- **Chinese type directories = graph coloring keys** — `机构/ 工具/ 指标/ 机制/ 事件/ 分析/ 来源/` replace the English `sources/ entities/ concepts/ analyses/` four-dir layout
- **Hub page named after the domain** (e.g. `宏观.md`) replaces `index.md`; Chinese slug = filename = wikilink = data.db primary key
- **`facts` + `events` tables replace the old `history` table** — T1/T2 retirement zipper (valid_from/valid_to/is_current/caused_by_event) + T4 event stamps; retire-never-delete enforced at the storage layer

### Added
- **Per-domain ontology contract `wiki/{domain}/_ontology.md`** — authoritative truth source for node types, controlled relation vocabulary, the six-tier time model (T0 observation / T1 state / T2 durable logic / T3 relation / T4 event / T5 type axiom), and the six-step retirement protocol
- `references/new_domain.py` — scaffold a new domain wiki (meta, hub, contract skeleton)
- `references/position_encoding.py` — deterministic graph layout (y = ontology tier, x = Fiedler spectral coordinate)
- recall mode formalized as a persistent session state (vs single-shot query)

### Notes
- `skill/auto-wiki-en/` remains at 0.2.0 pending re-translation of the new protocols
- auto-wiki now also ships bundled as the compilation engine inside [Burrow](https://github.com/abuttoncc/Burrow)

## 0.2.0 — 2026-04-09

### Added
- **deep-dive pipeline**: combined lint(Coverage) + ingest(search-fill) for proactive knowledge gap filling (#1)
  - 5-category gap detection in lint Coverage: page_missing, concept_missing, data_missing, single_source, outdated
  - Structured Gap Report format for deep-dive consumption
  - From-lint ingest flow with search tool integration
  - Anti-expansion mechanisms: max 10 gaps, confidence ceiling, no auto-scope-creep
  - User confirmation gates before search and before ingest
- `deep_dive_meta` field in source summary pages for search provenance tracking
- Scope control for deep-dive: sub-topic limiting, `--max-gaps` parameter
- `version` field in SKILL.md frontmatter

## 0.1.0 — 2026-04-08

Initial open-source release.

- 4 modes: recall, ingest, query, lint
- Two-layer architecture: Markdown (narrative) + SQLite (structured data)
- Obsidian-compatible output (YAML frontmatter + wikilinks)
- Domain-agnostic core with pluggable seeds and validators
- CN + EN bilingual skill definitions
