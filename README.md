# auto-wiki

[English](README.md) | [中文](README.zh.md)

Teach your AI agent to build and maintain a persistent knowledge wiki — so it stops forgetting what it learned yesterday.

![RAG vs Compilation](docs/figure/01ragen.jpg)

## The Problem

AI agents do research, write reports, pull data — then forget everything. Ask the same domain question next week, and the agent starts from scratch. RAG helps with retrieval, but it doesn't *accumulate* — it re-derives answers from raw documents every time.

## The Solution

auto-wiki is a **knowledge compiler** skill for AI agents (Claude Code, Codex, etc.). Instead of retrieving from raw documents at query time, the agent incrementally builds and maintains a structured wiki — comparing new information against existing pages, updating what changed, flagging contradictions, and preserving the evolution of knowledge.

Four modes:

| Mode | Trigger | What the Agent Does |
|------|---------|-------------------|
| **recall** | `/auto-wiki recall {topic}` | Load wiki context, answer all subsequent questions from accumulated knowledge |
| **ingest** | `/auto-wiki ingest` or provide source material | Read source → compare old vs new → update/create pages → write data to SQLite |
| **query** | `/auto-wiki query` | One-shot: search wiki → synthesize answer with citations → identify gaps |
| **lint** | `/auto-wiki lint` | Scan all pages → fix broken links → detect contradictions → report health |

The agent also auto-routes from natural language — "what did we learn about X" triggers recall, handing it a file triggers ingest.

## Quick Start

1. Copy `skill/auto-wiki-en/` (English) or `skill/auto-wiki-cn/` (Chinese) into your agent's workspace
2. Point your agent to `SKILL.md` as its instruction file
3. Build knowledge, then use it:

**Accumulate:**
```
You:   /auto-wiki ingest
You:   "Research personal pension policy, build me a knowledge framework"
Agent: [searches policy docs → creates wiki → ingests 2 sources → builds 6 concept pages]

You:   "Now find academic research on participation willingness"
Agent: [searches → finds 3 papers → ingests → updates existing concepts → flags 1 contradiction]
```

**Recall:**
```
You:   /auto-wiki recall personal-pension
Agent: Recall mode active. Wiki: 22 pages / 8 data points / 2 contested.

You:   "How should policy be designed to increase participation?"
Agent: Based on [[enrollment-friction]], [[tax-incentive-effect]], and [[ira-usa]]...
       ⚠️ Note: tax incentive effectiveness is contested (77.8% vs 25%)
       Gap: no research on under-35 demographics yet — suggest ingesting more.
```

## Language Versions

| Version | Directory | Description |
|---------|-----------|-------------|
| Chinese | `skill/auto-wiki-cn/` | Agent protocols in Chinese. Wiki output in Chinese. |
| English | `skill/auto-wiki-en/` | Agent protocols in English. Wiki output in English. |

Each version is fully self-contained — copy one directory and it works standalone. Python tools (`schema.py`, `store.py`) are identical in both.

## Architecture

```
.wiki/{topic}/
├── data.db              ← Structured data (SQLite: data points, history, relations)
├── meta.yaml            ← Wiki metadata
├── index.md             ← Navigation (Agent-maintained)
├── log.md               ← Operation log (append-only)
├── sources/             ← Source summaries (immutable)
├── entities/            ← Entity pages (narrative analysis)
├── concepts/            ← Concept pages
└── analyses/            ← Archived query outputs
```

**Two layers, clean separation:**

- **Markdown pages** — narrative analysis, wikilinks, human-readable. Compatible with [Obsidian](https://obsidian.md/).
- **SQLite database** — numeric data, time series, relations, history. Queryable.

The agent writes analysis in markdown and data in SQLite. Never the other way around.

## How Ingest Works

![Ingest Flow](docs/figure/02ingest-en.jpg)

When the agent gets a new source, it compares against every relevant wiki page and decides:

| Result | When | Action |
|--------|------|--------|
| **Reinforce** | New info matches existing conclusion | Add source citation, raise confidence |
| **Update** | New info has newer date or better source | Rewrite page, move old conclusion to history |
| **Conflict** | Sources disagree, can't determine which is right | Keep both, mark as `contested` |

This comparison loop is what keeps the wiki useful as it grows.

## How Recall Works

Recall is a persistent mode for the conversation. Once entered, every question consults the wiki first:

1. Agent loads `index.md` + `data.db` summary on entry
2. For each question: extract keywords → match pages in index → query data.db → read relevant pages
3. Answer with citations (`[[page-slug]]`), flag contested info, report knowledge gaps
4. Never fabricate — if the wiki doesn't have it, say so and suggest what to ingest

Exit with `exit recall` or by switching to another mode.

## Domain Independence

![Architecture](docs/figure/03core_en.jpg)

The skill core is domain-agnostic. Domain knowledge is pluggable:

```
auto-wiki-cn/                      (or auto-wiki-en/)
├── SKILL.md                        # Compilation engine (domain-agnostic)
├── references/                     # Core protocols (domain-agnostic)
│   ├── schema.py                   #   Page validation + HTML report
│   ├── store.py                    #   SQLite data layer
│   ├── ingest-protocol.md          #   Three-way comparison
│   ├── wiki-format.md              #   Page structure
│   └── ...                         #   (12 protocol files total)
├── seeds/                          # Domain vocabulary (pluggable)
│   └── fibo-pensions.md            #   Example: pension domain (FIBO standard)
└── validators/                     # External validators (pluggable)
    └── fibo-mcp.md                 #   Example: FIBO SPARQL logical validation
```

- **Without a seed**: wiki grows freely, agent names concepts as it sees fit
- **With a seed**: agent aligns naming to industry standards, follows anti-confusion rules
- **With a validator**: lint checks logical consistency against external ontology

## Visualization

```bash
python references/schema.py --report .wiki/my-topic/
# → generates .wiki/my-topic/_report.html
# → open in browser: interactive relation graph + data table + coverage gaps
```

Also works with Obsidian — open `.wiki/` as a vault, graph view renders the wikilink topology automatically.

## Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `schema.py` | Validate page frontmatter | `python schema.py .wiki/topic/` |
| `schema.py --report` | Generate visual HTML report | `python schema.py --report .wiki/topic/` |
| `store.py init` | Initialize data.db | `python store.py init .wiki/topic/` |
| `store.py dump` | Print database summary | `python store.py dump .wiki/topic/` |

## Requirements

- Python 3.10+ (standard library `sqlite3` — no external DB needed)
- `pyyaml` and `pydantic` for schema validation (`pip install -r requirements.txt`)
- An AI agent that can read/write files (Claude Code, Codex, etc.)
- Optional: WebSearch capability for autonomous research mode

## Acknowledgements

This project builds on ideas and inspiration from:

- **[LLM Wiki](https://github.com/swyxio/ai-notes/blob/main/Resources/llmwiki.md)** — the pattern of LLM-maintained persistent wikis. The idea was [proposed by Tobi Lutke](https://x.com/tobi/status/1935967165527437666) and formalized into the implementation document by [swyx](https://github.com/swyxio). auto-wiki's compilation model grew out of this.

- **[autoresearch](https://github.com/karpathy/autoresearch)** by Andrej Karpathy — showed that agents can run their own research loops. autoresearch optimizes training metrics; auto-wiki borrows the same "agent as researcher" idea for knowledge accumulation.

- **[FIBO](https://spec.edmcouncil.org/fibo/)** by EDM Council — the most widely adopted semantic ontology for finance (627K+ inferred triples). auto-wiki's seed/validator system was built to plug into standards like FIBO for logical validation.

- **[fibo-mcp](https://github.com/NeurofusionAI/fibo-mcp)** by NeurofusionAI — the MCP server that materializes FIBO into a queryable SPARQL endpoint. auto-wiki's validator example (`validators/fibo-mcp.md`) is built on top of this project.

- **[Nuwa](https://github.com/hanlinlibham)** — a cognitive profiling methodology for extracting mental models, heuristics, and decision patterns from a person's writings and decisions. auto-wiki's cognitive ontology type (`ontology-types/cognitive.md`) was adapted from this approach.

- **[Obsidian](https://obsidian.md/)** — wiki format (YAML frontmatter + `[[wikilinks]]`) is Obsidian-compatible by design. The agent compiles in the background; you browse with Obsidian.

## License

MIT. See [LICENSE](LICENSE).
