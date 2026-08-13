# Changelog
## 0.4.4+survey.2.scaling.1 — 2026-08-13

来源：真实使用反馈（个人阅读库 713 页，hub 涨到 104 KB / 700+ 行）。
根因是引擎把「hub = 全量页面清单」当默认契约，而没有任何一层在规模增长时自动收敛——
recall/ingest 每次整读 hub，**上下文随库大小线性膨胀且无上限**。

### Added
- `references/regen_index.py` —— L1 分层索引重建：各类型 `_index.md` + 顶层导航计数。
  保留 hub 里人写的「知识结构」块；contested 页面顶到导航层单列；
  `--check` 只体检不写盘（ingest 收尾调用），超阈值打 WARN 不阻断。
- `references/fts_index.py` —— L2 全文索引，FTS5 + BM25，零额外依赖。
  CJK 按字建索引、展示层还原成人话，`--type` 可限定类型。
  取代 `scaling.md` 里原来的粘贴式代码片段。
- `new_domain.py --graph` —— 幂等重放 Obsidian 图谱配置。

### Changed
- **`new_domain.py` 改生成 L1 骨架**：顶层 hub 只有类型/计数/入口（导航页），
  建域时同时在各类型目录铺 `_index.md`。新库从第一天就没有「全量 hub」这条膨胀路径。
- **协议口径统一为「hub = 导航，不是清单」**：`SKILL.md` 的 recall/query/ingest 三段、
  `query-protocol.md`、`ingest-protocol.md` 全部改为「读 hub 定位类型 → 只读该类型子索引 →
  页数 > 500 走 `fts_index.py`」，并加入一条上下文纪律：任何时候不把整库清单读进上下文。
  ingest 收尾由「更新 hub 页面」改为「跑 `regen_index.py` 重建索引」。
- `assets/obsidian/graph.json`：过滤补 `-tag:#hub -file:_index`（否则 hub 与子索引会成为
  链接全库的超级中心节点，把真实结构压平），新增 `contested` 高亮组。
- `init-protocol.md`：明写 **Obsidian 在图谱面板改任何设置都会回写覆盖 graph.json**，
  失效时重跑 `--graph`。
- `README`：新增「设计依据与参考文献」（中英双语，IEEE 著录）。**编译论题标明为本项目
  自有命题、无外部出处、不冒充经典**，并列出计算机领域同源的既有工作。

### 实测
| 页面数 | 顶层 hub 体量 |
|---|---|
| 4（bookshelf 示例） | 1.0 KB |
| 60 | 1.1 KB |
| 520 | 1.1 KB |

页面数涨 130 倍，顶层 hub 体量不变。`precheck page --strict` 与 `schema` 在含 `_index.md`
的库上照常全过——索引页不会被当作知识页校验。

### 版本号说明
沿用本仓「基线 0.4.4 + 本仓增量」的口径：`+survey.2` 之后追加 `+scaling.1`，
不冒充上游版本号。本次改动的协议面与母本 0.4.10 一致；`references/*.py` 中
`precheck/schema/store/instance/position_encoding` 仍是本仓的独立实现
（母本那几个依赖未公开的 `src/` 内核，直接照搬会让本仓无法独立运行）。

## 0.4.4+survey.2 — 2026-08-12

### Fixed
- **清 pre-0.3 目录名残留**：`seeds/fibo-pensions.md`、`references/seed-ontologies.md`、
  `seeds/README.md` 仍把标准概念映射到 `entities/`／`concepts/` 四目录布局，而 0.3.0 起
  已改为中文类型目录——三处文档比代码落后两个版本。改为 `机构/` `工具/` `机制/` 等，
  例子改用中文 slug，并补上「同一机构可同时任受托人与账管人，拆页会把实体打碎」这条
  禁混后果（原文只说不该拆，没说拆了会怎样）。

### 上游收口
- `survey` 模式已回流作者母本并发布为 **0.4.9**；本仓不再是母本旁支。本次三个修正文件
  与母本逐字节一致。本仓版本仍标 `0.4.4+survey.x`：基线是 0.4.4，与 0.4.9 的差异在
  `references/*.py` 与内核适配（`src/`、`INVARIANTS.md`），协议面则一致。

## 0.4.4+survey.1 — 2026-08-12

公开版在 0.4.4 基线上增加一个模式。版本号写成 `0.4.4+survey.1` 而不是 0.5.0：
基线仍是 0.4.4，`+survey.1` 是本仓的增量，不冒充上游更高版本。

### Added
- **`survey` 模式（存量勘察）** —— 站在 `init` 之前的取证相。人指一个**已经存在的**
  笔记库或工作目录，Agent **只读结构不读正文**地扫一遍，反推出 init 提案草案与种子
  草案，**不建库、不写用户任何文件**。
  - 动机：`init` 第一轮要人凭空说出领域、节点类型、路由词和三个反复问的问题，冷着答
    只能给场面话。而已有的目录名就是用户的分类学，文件名高频词就是路由词，改动时间
    分布就区分了动态与稳定知识——先扫再问，提案质量不是一个量级。
  - 三条硬边界：不读正文（默认零内容暴露，要读须逐次授权；`--frontmatter` 只读 YAML
    头的键与标签）、不导入存量（守 `init` 的「不导入整批历史资料」，读结构不是导入）、
    不写用户既有目录。
  - `references/survey.py` 承担确定性半边：目录树、文件名 n-gram 高频词（中文按字
    n-gram，不引分词依赖）、扩展名分布、修改时间分桶、可选 frontmatter 键与标签。
    **输出长度不随语料规模增长**——各节按 `--top` 截断，扫 100 个文件和扫 10 万个
    文件报告都是一页，且绝不打印文件清单。计数一律由脚本给出，Agent 不许自己数。
  - 禁混规则**刻意不做自动生成**：产物是收敛后的结果，混淆痕迹已被抹掉，从结构里挖
    不出来。协议规定只能问人，并给出问法——「你带新人时反复纠正过哪几组概念？」

## 0.4.4 — 2026-08-12

The public edition jumps 0.3.1 → 0.4.4. Engine development continued on a private
repository between 2026-06 and 2026-08; the intermediate releases (0.3.0 `source`
mode, 0.4.0–0.4.4) are consolidated into this entry rather than backfilled as
separate dated tags here. The Chinese edition is the reference implementation —
the English edition remains at 0.3.0 and does not yet carry the additions below.

### Added
- **`init` mode** — build a wiki from scratch through an interview instead of making
  the user learn ontology jargon first. Infers the first domain, node types and
  relations from the user's actual workflow and their three recurring questions;
  shows one proposal before writing; verifies the finished wiki with a real question.
  Instance constraints land in `{ops_dir}/onboarding.md` for later `source`/`ingest`.
- **`source` mode** — the collection phase at the front of the pipeline. Splits a
  user-supplied index into atomic queries, fans out across channels, integrates with
  provenance and channel-credibility grading, and lands in `Inbox/raw/` **without
  touching the wiki**. Contested findings are recorded side by side, never adjudicated
  at this stage. Brings the mode count to seven.
- **Five-check precheck** (`precheck.py`) — a pre-write hard gate: schema validation
  plus the four highest-frequency defect classes (double YAML blocks, enum inline
  comments, relation key names, missing required fields). Errors block the write.
  `precheck.py dup/sweep` adds same-type collision detection as non-blocking advice,
  and `precheck.py stamp` emits a stampable version fingerprint.
- **Instance configuration decoupling** (`instance.py`) — resolves settings from
  defaults ← `wiki/_config.yaml` ← `.burrow/config.json`, making `ops_dir` configurable
  so the engine runs standalone or embedded. `meta.yaml` records a `born_of` birth
  version stamp, and `precheck.py contract` reports advisory migration hints on engine
  upgrade — **the engine never silently rewrites an instance contract**.
- **`reading-notes` seed** — general-purpose cold start for books, courses, papers and
  podcasts, encoding the distinctions that beginners get wrong: a work is not a source,
  an excerpt is not knowledge, the original author's argument is not your analysis.
- **Runnable example** `examples/bookshelf/` — a minimal closed loop covering
  raw → source → concept/analysis → report.
- **OKF export** (`export_okf.py`) — one-way projection of a domain into an
  [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog) bundle for
  vendor-neutral exchange. Lossy by design (the bitemporal layer and typed edges get
  flattened), so it is an interchange port, never primary storage.
- **R9 anchor gate** — institutional entity pages must declare `anchor:` (why this kind
  of thing exists) and `ground:` (why this particular one holds that status). Driven by
  instance config `anchor_required: {subtypes, since}` with zero hardcoding; only applies
  to pages created on or after the configured date, so existing content is not retroactively
  blocked.
- Optional Obsidian `graph.json` template under `assets/obsidian/`.

### Changed
- **Central installation model** — the engine became a standalone repository with a single
  master; libraries no longer embed a copy of it. Install once per machine at the user level;
  pinning an older engine is the documented exception, not the default.
- **Obsidian demoted to an optional adapter** — removed all "must appear in the Obsidian
  graph" / "must initialize `.obsidian/`" requirements. `.obsidian/` is created only when the
  instance actually uses Obsidian; `_report.html` is the zero-dependency default visualization.
- `new_domain.py` gained `--seed`, rejects non-existent seeds, and records the seed at domain
  birth. The template file was eliminated in favour of a single source.
- The version field moved to the standard `metadata.version` key; birth stamps and policy
  stamps stay compatible with the old top-level format.
- `query`/`recall` protocols gained **query-miss logging** — the only observation point on the
  false-rejection side. Without it, retrieval quality can never be measured.

### Archived
- **The English edition is archived at v0.3.0** and moved to `archive/auto-wiki-en-v0.3.0/`.
  It documents five modes against an engine that now has eight, and the 0.4.x port was never
  scheduled — left in place beside the maintained edition it read as an equal option. Nothing
  was deleted: all 19 files are kept byte-for-byte, git records the move as renames, and
  `archive/README.md` carries the tombstone (date, reason, successor). It still runs; it just
  will not be updated. An English port of 0.4.x is welcome as a contribution.
- The Chinese edition is now the only maintained one. The Python tools under `references/`
  are language-neutral, so English readers who want the current feature set can use it
  directly — only the protocol prose is Chinese.

### Fixed
- README declared a Python floor of 3.10+; the actual floor is 3.8 (every module carries
  `from __future__ import annotations`, verified by AST parse at `feature_version=(3,8)`).
- The `Architecture` section still showed the pre-0.3 `.wiki/{topic}/` layout with
  `sources/entities/concepts/analyses`; it now shows the domain-based layout that has been
  in effect since 0.3.0.
- Install instructions pointed at a decommissioned host; they now point at this repository.

## 0.3.1 — 2026-06-11

### Fixed
- `scaling.md` L2 index-builder example still iterated the pre-0.3 four-directory layout (`sources/entities/concepts/analyses`); now iterates the 0.3 type directories in both editions
- `ingest-protocol.md` (CN) used `source_type: 二手·券商`, which is outside the `schema.py` enum; normalized to `二手` with an inline note (EN edition was already normalized)
- Examples referencing a specific broker by name are now anonymized in both editions

## 0.3.0 — 2026-06-11

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
- `skill/auto-wiki-en/` fully re-translated and localized to 0.3.0: English type directories (`institutions/ instruments/ indicators/ mechanisms/ events/ analyses/ sources/`), natural-language English slugs (slug = filename = wikilink = data.db key), English trigger words, source-grade vocabulary aligned with `schema.py` enums
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
