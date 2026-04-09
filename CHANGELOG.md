# Changelog

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
