---
name: auto-wiki
version: 0.2.0
description: |
  知识编译器：教 Agent 把源文件增量编译进持久化 wiki，实现跨会话知识积累。
  运行时依赖：Python 3.8+（标准库 + pydantic）。可选增强：WebSearch（主动搜索）、外部 MCP 校验器（逻辑校验）。

  五个模式，根据用户意图自动路由：

  recall → 用户想基于已有知识回答问题。
  触发词：recall、知识模式、打开 wiki、带着知识回答、根据 wiki、
  基于积累、查一下 wiki、wiki 里有没有、之前研究过、上次整理的。

  ingest → 用户提供了新材料，想编译进 wiki。
  触发词：ingest、编译、整理这篇、消化这篇、学习这个、归档、
  把这篇加进去、积累、研究一下、帮我整理、加入知识库。

  query → 用户问了一个具体问题，想从 wiki 中找答案（单次）。
  触发词：query、根据 wiki 回答、wiki 里怎么说、查查看。

  lint → 用户想检查 wiki 健康度。
  触发词：lint、检查 wiki、wiki 健康、清理一下、有没有矛盾。

  deep-dive → 用户想让 Agent 自动找出知识缺口并补全。
  触发词：deep-dive、深度研究、补全知识、查漏补缺、上强度、
  自动补全、知识补全、全面补充。
  注意：deep-dive 不是独立模式，是 lint(Coverage) + ingest(搜索填充) 的组合管道。

  路由规则：如果用户没有提供新材料但提到了 wiki 或领域知识 → recall。
  如果用户提供了文件或大段文本 → ingest。
  如果用户说"deep-dive"或"上强度" → 执行 deep-dive 管道。
  如果不确定 → 问用户。
---

# 知识编译器

> Agent 做研究、拉数据、写报告——wiki 把这些产出串起来。Agent 越用越懂你的领域。

## 运行时依赖与权限声明

| 依赖 | 必需？ | 说明 |
|------|--------|------|
| **Python 3.8+** | ✅ 必需 | `schema.py`（frontmatter 校验）、`store.py`（SQLite 数据管理）、`build_index.py`（FTS5 索引）均为 Python 脚本。仅用标准库（`sqlite3`、`json`、`pathlib`）+ `pydantic` |
| **pydantic** | ✅ 必需 | `schema.py` 的 frontmatter 校验依赖。`pip install pydantic` |
| **文件系统写入** | ✅ 必需 | 在 `.wiki/{topic}/` 下创建和编辑 Markdown、SQLite、`.obsidian/` 配置。**首次创建 `.wiki/` 时会向用户确认位置** |
| **WebSearch / WebFetch** | ❌ 可选 | 主动模式（Agent 自主搜索材料）需要。被动模式（用户提供文件）不需要 |
| **外部校验器（MCP）** | ❌ 可选 | 仅当 wiki 声明了 validator 时 lint 会尝试调用。不可达时静默跳过，零影响。**不需要用户提供任何凭证**——`Mcp-Session-Id` 是标准 MCP 协议的会话握手，由 Agent 自动完成 |
| **搜索类 MCP** | ❌ 可选 | deep-dive 和主动 ingest 可用域数据 MCP 增强搜索质量。没有时退化为 WebSearch |

> **核心承诺**：被动模式（用户提供文件 → Agent 编译）只需要 Python 3 + 文件读写，零网络依赖。所有网络调用都是可选增强，且会在首次使用时通过环境检查告知用户。

## Quick Start

```
用户: /auto-wiki recall personal-pension
Agent: [扫描 .wiki/personal-pension/ → 读 index.md → 加载 data.db 摘要]
Agent: 已进入 recall 模式。当前 wiki：22 页 / 8 数据点 / 2 处 contested。
       接下来的问题我会先查 wiki 再回答。

用户: 参与率低的原因是什么？
Agent: [读 wiki 中 enrollment-friction、tax-incentive-effect 等页面]
Agent: 根据 wiki 积累的 6 篇来源...（引用具体页面和数据）
       ⚠️ 注意：税优激励效果存在矛盾（77.8% vs 25%），详见 [[participation-willingness]]
```

## 核心理念

Agent 每天帮你做研究、写报告、拉数据——但做完就忘。下次问同样领域的问题，又从零开始。

这个 Skill 解决一件事：**给 Agent 一个可以持续积累的知识库。**

不是 RAG（每次从文档堆里临时检索），是编译——Agent 读完源文件后，把关键信息写进 wiki 已有页面，和旧知识比较、合并、标注冲突。下次执行任何任务前，先读 wiki，从积累的基础上工作。

## 四个模式

| 模式 | 触发 | Agent 做什么 |
|------|------|-------------|
| **recall** | `recall` / `recall {topic}` | 加载 wiki 上下文，后续所有问题先查 wiki 再回答 |
| **ingest** | 用户提供源文件或文本 | 读源文件 → 搜索已有 wiki → 比较新旧 → 更新/创建页面 → 更新索引 |
| **query** | 用户提问（单次） | 读 index → 找相关页面 → 综合回答 → 有价值的分析可归档 |
| **lint** | 用户说"检查 wiki" | 扫描全部页面 → 合并重复 → 归档过时 → 报告矛盾和健康度 |
| **deep-dive** | `deep-dive` / "上强度" | 运行 Coverage lint → 展示缺口报告 → 用户确认 → 搜索 + ingest 填补缺口 |

> deep-dive 不是第五个独立模式——它是 lint（Coverage）和 ingest（带搜索工具）的组合管道。需要搜索工具（主动模式）。

recall 模式 vs query 的区别：query 是单次操作（问一个问题，查一次 wiki）。recall 模式是持续状态——进入后，这轮对话里的每个问题都先过 wiki。

---

## recall 模式

### 进入

用户说 `/auto-wiki recall` 或 `/auto-wiki recall {topic}` 时触发。

Agent 执行：

1. **扫描 `.wiki/` 目录**，列出可用的 wiki 主题
2. 如果用户指定了主题 → 加载该 wiki；如果没指定 → 列出可选主题让用户选
3. **读 index.md** → 获取全部页面列表和结构
4. **读 data.db 摘要** → `python references/store.py dump .wiki/{topic}/`，获取数据点数、关系数、contested 数
5. **向用户报告**：
   ```
   已进入recall 模式：{主题}
   - 页面：{N}（sources: X, entities: Y, concepts: Z）
   - 数据点：{N} | 关系：{N} | Contested：{N}
   接下来的问题我会先查 wiki 再回答。说"退出recall 模式"恢复正常。
   ```

### 回答流程

进入recall 模式后，每次收到用户问题：

1. **从问题中提取关键词**（实体名、概念名、指标名）
2. **在 index.md 中匹配**相关页面（标题 + 描述）
3. **在 data.db 中查询**相关数据点：
   ```sql
   SELECT * FROM data_points WHERE field LIKE '%关键词%' OR page_slug LIKE '%关键词%'
   ```
4. **读取匹配的 wiki 页面**（通常 2-5 个），沿 wikilink 展开一层
5. **综合回答**，必须：
   - 引用具体页面：`[[slug]]`
   - 引用具体数据：值 + 单位 + 时段 + 来源
   - 如果涉及 contested 信息，主动标注
   - 如果 wiki 中信息不足，明确说"wiki 中没有这方面的积累，建议 ingest XX"
6. **不编造 wiki 中没有的信息**。宁可说"不知道"也不要假装 wiki 里有

### 退出

用户说 `exit recall`、切换到其他操作（ingest/lint）、或开始新话题时退出。

---

## 执行流程

### Phase 0: 识别研究主题与本体类型

收到用户输入后，判断三件事：**操作类型**、**目标 wiki**、**本体类型**。

| 用户输入 | 操作 | 目标 wiki | 本体类型 |
|---------|------|-----------|---------|
| "帮我整理这篇研报" + 文件 | ingest | 从内容推断，或问用户 | domain |
| "ingest 到个人养老金" + 文件 | ingest | personal-pension | domain |
| "研究一下 Charlie Munger" + 材料 | ingest | charlie-munger | cognitive |
| "个人养老金参与率怎么样" | query | 从问题推断，或问用户 | — |
| "检查一下养老金 wiki" | lint | personal-pension | — |

**本体类型**决定 wiki 的页面结构和采集策略：

| 本体类型 | 研究对象 | 页面侧重 | 参考 |
|---------|---------|---------|------|
| **cognitive** | 人（思维模型、决策方式） | MentalModel, Heuristic, Value, StylePattern | `references/ontology-types/cognitive.md` |
| **domain** | 领域（机构、制度、指标） | Entity, Concept, Metric | `references/ontology-types/domain.md` |
| **general** | 以上都不是 | 默认 entity/concept 结构 | — |

**一个 wiki 只有一种类型。** 如果研究横跨人和领域（如"Munger 的投资框架在企业年金中的应用"），分属两个 wiki，用跨 wiki query 综合回答。不要在一个 wiki 里混用 cognitive 和 domain 页面结构。

**如果 wiki 目录不存在**，先向用户确认创建位置（默认 `.wiki/{topic}/`，在当前仓库根目录下），然后按 `references/storage-spec.md` 创建初始结构（含 meta.yaml、index.md 模板、log.md 模板）。建议用户将 `.wiki/` 加入 `.gitignore`（如尚未添加）。

**领域种子（seed）**：如果目标领域有对应的种子文件（`seeds/{name}.md`），在 meta.yaml 中声明 `seed: {name}`。种子提供标准术语词表、关系模板和禁混规则，让 wiki 从规范化的起点开始生长。没有种子的领域，wiki 自由生长——两种路径都能跑。种子是社区可贡献的插件，任何人可以为自己的垂直领域写一个 markdown 文件。详见 `references/seed-ontologies.md`。

**首次使用时**，执行环境检查（见 `references/source-validation.md`），告知用户当前可用的能力（被动模式 vs 主动模式）。

### Reference 加载策略

不要一次读完所有 reference。按操作类型按需加载：

| 操作 | 必读 | 首次时读 | 有工具时读 |
|------|------|---------|-----------|
| **ingest** | `ingest-protocol.md`, `wiki-format.md`, `schema.py` | `storage-spec.md`（wiki 不存在时）, `seed-ontologies.md` + `seeds/{name}.md`（meta.yaml 声明了 seed 时） | `fact-check.md`, `source-validation.md` |
| **query** | `query-protocol.md` | — | — |
| **lint** | `lint-protocol.md`, `schema.py` | — | `validators/{name}.md`（seed 声明了 validator 时） |
| **deep-dive** | `lint-protocol.md`, `ingest-protocol.md`, `source-validation.md`, `wiki-format.md`, `schema.py` | `storage-spec.md`（wiki 不存在时） | `fact-check.md` |

**不需要读的**：`scaling.md` 仅当页面数 > 500 时才相关；`ontology-types/` 仅当新建 wiki 需判断类型时。

### Phase 1: Ingest（知识编译）

**这是核心操作。** 详细协议见 `references/ingest-protocol.md`。

简要流程：

1. **读取源文件**，提取关键信息
2. **校验关键数据**（如有可用工具）— 详见 `references/fact-check.md`
3. **写 source 摘要页**（`sources/{date}-{slug}.md`）
4. **搜索 wiki 中已有的相关页面**（读 index.md，grep 关键实体名）
5. **逐页比较新旧信息**：
   - 新信息**支持**已有结论 → 加引用，提升 confidence
   - 新信息**推翻**已有结论 → 数值写入 data.db（旧值自动进 history 表），改写正文分析
   - 新信息**矛盾**且无法判断 → 并列两种说法，confidence → `contested`
6. **创建新页面**（仅当涉及 wiki 中没有的实体/概念）
7. **更新 index.md + 追加 log.md**
8. **Schema 校验**——对本次创建/修改的所有页面运行 `python references/schema.py {page.md}`，确保 frontmatter 符合规范。不通过则立即修复再继续

Ingest 完成后向用户报告：
```
已 ingest 到 {主题} wiki：
- 新建：{N} 页（列出）
- 更新：{N} 页（列出 + 简述变更原因）
- 冲突：{N} 处（列出矛盾点）
- 校验：{N} 页全部通过 / {M} 页有问题（列出）
```

### Phase 2: Query（知识查询）

**详细协议见 `references/query-protocol.md`。**

1. 读 index.md，识别与问题相关的页面
2. 读取匹配页面 + 沿 wikilink 展开一层关联页面
3. 基于页面内容综合回答，**引用来源页面**：
   ```
   根据 wiki 中 5 篇源文件的积累：
   ... 分析内容 ...
   来源：[[alpha-corp]]、[[2026-policy-doc]]
   ```
4. 如果涉及 contested 信息，明确标注矛盾
5. 如果回答中包含有价值的新分析，提示用户归档

**如果 wiki 中信息不足以回答**，明确说明缺口：
```
wiki 中关于 XX 的信息不足，目前只有 2 篇相关源文件。
建议 ingest 更多关于 XX 的材料。
```

### Phase 3: Lint（知识治理）

**详细协议见 `references/lint-protocol.md`（7 项检查 + 健康报告格式）。**

Lint 分两档：

| 档位 | 触发 | 检查项 | 代价 |
|------|------|--------|------|
| **结构档**（默认） | `lint` / `检查 wiki` | Validation, Orphan, Broken Link, Staleness | 全量扫描，确定性 |
| **语义档**（按需） | `深度 lint` / `检查矛盾` | Contradiction, Duplication, Coverage | Agent 语义理解，按范围控制 |

1. **结构档**：自动扫描全部页面，修复格式、断链、孤页、过时标注
2. **语义档**（用户触发时）：检测矛盾、重复、覆盖度缺口。wiki < 50 页全量扫描，50-200 页只扫最近 30 天 ingest 触及的页面，> 200 页须用户指定范围
3. **报告健康度**：
```
Wiki 健康报告：{主题}
- 页面总数：42（entities: 15, concepts: 10, sources: 12, analyses: 5）
- 健康度：良好
- 结构修复：修复 1 个断链，归档 1 个过时页面
- [语义] 待人工确认：2 处矛盾（列出）
- 建议：XX 领域源文件较少（仅 1 篇），建议补充
```

### Phase 4: Deep-Dive（知识补全管道）

**deep-dive = lint(Coverage) + ingest(搜索填充)**。不是独立模式，是组合管道。

**前提条件**：需要搜索工具（主动模式）。无搜索工具时，只输出缺口报告，不执行自动填充。提示用户手动 ingest。

**流程**：

```
1. 运行 lint Coverage 检查（5 类缺口检测）
   → 输出结构化 Gap Report（见 lint-protocol.md）

2. 展示 Gap Report，请用户确认
   → 用户可以：全部接受 / 选择子集 / 限定范围 / 取消
   → 这一步不可跳过——防止无监督的批量写入

3. 对确认的每个缺口，执行 from-lint ingest 流程
   → 搜索 → 用户确认来源 → 标准 ingest
   → 详见 ingest-protocol.md 的 From-Lint 章节

4. 输出补全报告：已补全 / 未能补全 / 建议
```

**触发词**：`deep-dive`、`深度研究`、`补全知识`、`查漏补缺`、`上强度`

**示例**：
```
用户: deep-dive treasury-futures
Agent: [运行 Coverage lint...]
Agent: 发现 6 个知识缺口：
       1. [high] page_missing: stock-bond-correlation（被 4 个页面引用）
       2. [high] concept_missing: 基差（在 5 个实体页中提到）
       3. [medium] single_source: treasury-futures-basics（仅 1 个来源）
       ...
       要补全哪些？(all / 选序号 / cancel)

用户: 1, 2

Agent: [搜索"股债联动 国债期货"...]
Agent: 找到 2 个候选来源：
       - [二手·权威] 中金固收报告《股债联动分析》 ← 推荐
       - [二手] 某公众号文章 ← 跳过（黑名单渠道）
       确认使用中金报告？

用户: 确认

Agent: [执行标准 ingest → 新建 concepts/stock-bond-correlation.md]
Agent: 补全完成。新建 2 页，更新 0 页，1 个缺口未能补全（建议手动提供材料）。
```

---

## Wiki 页面格式

详见 `references/wiki-format.md`。简要：

- 每个页面是带 frontmatter 的 markdown（title, type, created, updated, sources, confidence）
- 5 种页面类型：source / entity / concept / analysis / mental-model
- 用 `[[slug]]` 做页面间链接
- index.md 是目录，log.md 是操作日志

## 本体类型参考

当研究对象是**人**时，参见 `references/ontology-types/cognitive.md` 的采集策略——页面类型侧重心智模型、启发式、价值体系、表达风格。

当研究对象是**领域**时，参见 `references/ontology-types/domain.md` 的采集策略——页面类型侧重机构实体、制度概念、量化指标。

两者共用同一套 wiki 基础设施（ingest/query/lint），区别仅在页面分类和采集侧重。

## 垂直领域适配

Skill 核心是领域无关的编译引擎。垂直领域的专业性通过两层插件注入：

| 层 | 载体 | 作用 | 必须？ |
|----|------|------|--------|
| **种子（seed）** | `seeds/{name}.md` | 冷启动词表：标准术语、关系模板、禁混规则 | 可选 |
| **校验器（validator）** | `validators/{name}.md` | 运行时逻辑校验：关系合法性、必要关系完整性 | 可选 |

没有插件，wiki 自由生长，适合探索性研究。有了插件，wiki 从行业标准起步，概念命名规范、关系结构清晰、逻辑缺口可检测。

**社区可贡献**：为你的垂直领域写一个 seed 文件（markdown），声明 20-50 个核心术语和禁混规则，就能让该领域的 wiki 从规范化起点生长。

当前可用：
- `seeds/fibo-pensions.md` — 企业年金/养老金（基于 FIBO 标准）
- `validators/fibo-mcp.md` — FIBO SPARQL 逻辑校验（627K 推理三元组）

## 不做什么

- **不做向量检索**。小规模靠 index + grep，大规模靠 SQLite FTS5 + BM25（见 `references/scaling.md`）。向量检索留给平台级工具。
- **不做多用户协作**。wiki 目录是本地文件，一个用户一个 wiki。
- **不替代专业数据工具**。领域数据获取用对应的 MCP/工具，本 Skill 只接住它们的产出并编译进 wiki。

## 与其他工具的关系

本 Skill 不替代任何专业工具，它**串联**它们：

```
任意研究工具产出分析 → ingest 进对应 wiki
任意数据工具拉数据   → ingest 进对应 wiki
领域种子提供起跑线   → 标准术语 + 禁混规则
外部校验器纠逻辑     → lint 时检查知识结构完整性

下次执行任务时，Agent 先读相关 wiki → 带着积累的知识工作
```
