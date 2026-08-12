---
name: auto-wiki
metadata:
  version: "0.4.4+survey.2"
description: |
  把源材料增量编译为持久化 Markdown + SQLite wiki，实现跨会话知识积累。用于建立或使用个人/领域知识库、Obsidian wiki，以及取材、编译、查询和治理已有 wiki。八模式按意图路由：
  survey（我已经有笔记了、勘察存量、冷启动、看看我现有的资料）→ 只读结构扫已有目录，反推 init 提案与种子草案，不建库不写盘；
  init（初始化、从零建库、搭建 Obsidian）→ 访谈真实工作流并创建首个领域；
  source（取材、找资料、按清单搜）→ fan-out 搜集，收口 Inbox/raw，不碰正典；
  recall（打开 wiki、基于积累、之前研究过）→ 持续加载已有知识；
  ingest（整理、消化、归档、加入知识库）→ 比较新旧后编译材料；
  query（根据 wiki 回答、查查看）→ 单次查询；
  lint（检查健康、矛盾、断链、重复）→ 治理知识库；
  deep-dive（查漏补缺、上强度）→ lint 找缺口，经确认后搜索并 ingest。
  无 wiki 且用户要建库时走 init；有新材料走 ingest；人给索引并要求找资料走 source；只提 wiki/既有领域知识走 recall。不确定则询问。
---

# 知识编译器

> Agent 做研究、拉数据、写报告——wiki 把这些产出串起来。Agent 越用越懂你的领域。

## 运行时依赖与权限声明

| 依赖 | 必需？ | 说明 |
|------|--------|------|
| **Python 3.8+** | 必需 | `schema.py`、`store.py`、`precheck.py`、`new_domain.py` 等确定性工具 |
| **pydantic + pyyaml** | 必需 | frontmatter 校验和实例配置解析。`python3 -m pip install pydantic pyyaml` |
| **文件系统写入** | 必需 | 在 `wiki/{domain}/` 下创建 Markdown 与 SQLite；选择 Obsidian 时另写 `.obsidian/`。init 写入前先确认提案 |
| **WebSearch / WebFetch** | 可选 | 主动模式（Agent 自主搜索材料）需要。被动模式（用户提供文件）不需要 |
| **外部校验器（MCP）** | 可选 | 仅当 wiki 声明了 validator 时 lint 会尝试调用。不可达时静默跳过，零影响。**不需要用户提供任何凭证**——`Mcp-Session-Id` 是标准 MCP 协议的会话握手，由 Agent 自动完成 |
| **搜索类 MCP** | 可选 | deep-dive 和主动 ingest 可用域数据 MCP 增强搜索质量。没有时退化为 WebSearch |

> **核心承诺**：被动模式（用户提供文件 → Agent 编译）只需要 Python 3 + 文件读写，零网络依赖。所有网络调用都是可选增强，且会在首次使用时通过环境检查告知用户。

## Quick Start

```
用户: /auto-wiki init
Agent: 你拿到一份新材料后通常怎么处理、最后要产出什么？
       再举三个以后会反复问这个知识库的问题。
用户: 我读书后想沉淀概念和论点，以后会问……
Agent: [再问第一份材料、更新节奏、查看器和数据边界 → 展示提案 → 用户确认]
Agent: 已建库并完成首次 ingest。图谱报告：wiki/books/_report.html
```

## 核心理念

Agent 每天帮你做研究、写报告、拉数据——但做完就忘。下次问同样领域的问题，又从零开始。

这个 Skill 解决一件事：**给 Agent 一个可以持续积累的知识库。**

不是 RAG（每次从文档堆里临时检索），是编译——Agent 读完源文件后，把关键信息写进 wiki 已有页面，和旧知识比较、合并、标注冲突。下次执行任何任务前，先读 wiki，从积累的基础上工作。

## 八个模式

| 模式 | 触发 | Agent 做什么 |
|------|------|-------------|
| **survey** | `survey` / “我已经有笔记了” / “勘察存量” / “冷启动” | 只读结构扫已有目录 → 反推提案 → 问出禁混规则 → 出报告+提案草案+种子草案，**不建库、不写用户任何文件** |
| **init** | `init` / “从零建库” / “搭建 Obsidian” | 访谈真实工作流 → 展示提案 → 建领域与契约 → 首次 ingest → 用真实问题验收 |
| **source** | `source` / "根据索引找资料" / "取材" | 解析索引/钩子清单 → 动用全部取材通道 fan-out 搜原料 → 整合带溯源 → **落 Inbox/raw（不碰 wiki）** |
| **recall** | `recall` / `recall {topic}` | 加载 wiki 上下文，后续所有问题先查 wiki 再回答 |
| **ingest** | 用户提供源文件或文本 | 读源文件 → 搜索已有 wiki → 比较新旧 → 更新/创建页面 → 更新索引 |
| **query** | 用户提问（单次） | 读 hub 页面 → 找相关页面 → 综合回答 → 有价值的分析可归档 |
| **lint** | 用户说"检查 wiki" | 扫描全部页面 → 合并重复 → 归档过时 → 报告矛盾和健康度 |
| **deep-dive** | `deep-dive` / "上强度" | 运行 Coverage lint → 展示缺口报告 → 用户确认 → 搜索 + ingest 填补缺口 |

> **source 与 deep-dive 都涉及向外搜索，但方向相反**：deep-dive 由 `lint(Coverage)` 自动找 wiki **内部缺口**、搜回来**直接 ingest**；source 由**人给的索引**驱动、向外 fan-out 取材、**停在 Inbox/raw 闸前**。source 的产出正是 ingest / deep-dive 的输入。deep-dive 不是独立模式（= lint+ingest 组合管道）；source 是独立模式（管道最前端的取材相）。

recall 模式 vs query 的区别：query 是单次操作（问一个问题，查一次 wiki）。recall 模式是持续状态——进入后，这轮对话里的每个问题都先过 wiki。

---

## survey 模式（存量勘察）

**详细协议见 `references/survey-protocol.md`。**

站在 `init` 之前的取证相：人指一个**已经存在的**笔记库或工作目录，Agent
**只读结构不读正文**地扫一遍，反推出 init 提案草案与种子草案，**不建库、
不写用户任何文件**。

有存量的人是多数，而 init 第一轮要人凭空说出领域、节点类型、路由词和三个
反复问的问题——冷着答只能给场面话。他已有的目录名就是他的分类学，文件名
高频词就是他的路由词，改动时间分布就区分了动态与稳定知识。先扫再问，提案
质量不是一个量级。

```bash
python references/survey.py <目录> [--frontmatter] [--top 30]
```

三条硬边界：**不读正文**（默认零内容暴露，要读须逐次授权）、**不导入存量**
（守 init「不导入整批历史资料」那条，读结构不是导入）、**不写用户既有目录**
（一个字节都不写）。

上下文纪律：存量库动辄上万文件，**一次扫全库灌满上下文就没有下一步了**。
`survey.py` 各节按 `--top` 截断，输出长度不随语料规模增长；绝不打印文件清单，
只出聚合量；下钻按用户点名，一次一个子目录重跑，不要拉进来再筛。

**禁混规则挖不到**——产物是收敛后的结果，混淆痕迹已被抹掉。那只能问人，而且
要问对：**「你带新人时反复纠正过哪几组概念？」** 这比问「有哪些容易混的概念」
好答十倍。

---

## init 模式（首次建库）

**详细协议见 `references/init-protocol.md`。**

init 不让用户先学本体术语，而是从真实工作流和反复问题反推第一个领域、节点类型与关系。写入前只做一次提案确认；确认后复用 `new_domain.py`，按需应用 seed，完成首份材料 ingest，并用一个真实问题验收。实例约束落在 `{ops_dir}/onboarding.md`，供后续 source/ingest 读取。

若用户只是想体验，使用 `examples/bookshelf/`；若用户要建立自己的库，不把示例知识混入用户数据。

---

## source 模式（取材 / 采集）

**详细协议见 `references/source-protocol.md`。**

管道最前端的取材相：人给一份**索引/钩子清单**，Agent 动用**全部取材通道** fan-out 搜原料，整合带溯源后**落 `Inbox/raw/`，不碰 wiki**（守 ingest 闸）。产出正是 ingest / deep-dive 的输入。

简要流程：

0. **路由**：读 `wiki/_index.md`，把索引每条钩子命中到域，按库配置决定取材通道。
1. **拆索引**为原子查询（可检索的具体问题），列给用户过目可增删。
2. **fan-out 取材**：按钩子命中选通道并行检索——**取材通道按库配置，见库内 CLAUDE.md「取材通道」节**；无库配置时用通用通道（WebSearch/WebFetch 等）兜底。一条查询尽量交叉 2+ 通道互证；数值走数据源工具不凭记忆。
3. **收口整合**：每条原子查询一段「发现 + 溯源(标题+机构/作者+日期+链接) + 渠道可信度档」；多源冲突并列标 `contested`，**不在此裁决**。
4. **落 Inbox/raw**：追加到来源笔记，或新建 `{date}-{slug}-取材.md`，frontmatter `compiled: false` + `取材通道` + `索引来源`。
5. **报告**：每条钩子找到几条材料、覆盖/缺口、哪几条够 ingest 了。

**纪律**：不碰 wiki、不动 data.db；溯源以「标题+机构+日期」为准（链接会过期）；渠道分档（一手 > 二手·权威 > 二手，黑名单跳过；库特有分档纪律见库内 CLAUDE.md）；不裁决分歧。

---

## recall 模式

### 进入

用户说 `/auto-wiki recall` 或 `/auto-wiki recall {topic}` 时触发。

Agent 执行：

1. **扫描 `wiki/` 目录**，列出可用的 wiki 主题
2. 如果用户指定了主题 → 加载该 wiki；如果没指定 → 列出可选主题让用户选
3. **读 hub 页面**（`{主题中文名}.md`，即 wiki 根目录下与 meta.yaml `name` 对应的主页面）→ 获取全部页面列表和结构
4. **读 data.db 摘要** → `python references/store.py dump wiki/{topic}/`，获取数据点数、关系数、contested 数
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
2. **在 hub 页面中匹配**相关页面（标题 + 描述）
3. **在 data.db 中查询**相关数据点：
   ```sql
   SELECT * FROM data_points WHERE field LIKE '%关键词%' OR page_slug LIKE '%关键词%'
   ```
4. **读取匹配的 wiki 页面**（通常 2-5 个），沿 wikilink 展开一层
5. **综合回答**，必须：
   - 引用具体页面：`[[slug]]`
   - 引用具体数据：值 + 单位 + 时段 + 来源
   - 如果涉及 contested 信息，主动标注
   - 如果 wiki 中信息不足，明确说"wiki 中没有这方面的积累，建议 ingest XX"，
     并**登记 query-miss**（见 `query-protocol.md`「query-miss 登记」——误拒侧唯一观测点，漏记 = 检索质量永远无法度量）
6. **不编造 wiki 中没有的信息**。宁可说"不知道"也不要假装 wiki 里有

### 退出

用户说 `exit recall`、切换到其他操作（ingest/lint）、或开始新话题时退出。

---

## 执行流程

### Phase 0: 识别目标领域与本体类型

收到用户输入后，判断三件事：**操作类型**、**目标领域 wiki**、**本体类型**。

> **wiki 按领域(domain)组织，不按研究课题(topic)。** 研究课题（如"美联储加息周期"）降级为 `{domain}/分析/` 下一页，不再各自开 wiki。先识别这条知识属于哪个领域（macro / credit / …），再落到该领域目录。详见 `references/storage-spec.md`。

| 用户输入 | 操作 | 目标领域 wiki | 本体类型 |
|---------|------|-----------|---------|
| "帮我整理这篇货币政策研报" + 文件 | ingest | macro | domain |
| "ingest 到宏观" + 文件 | ingest | macro | domain |
| "研究一下 Charlie Munger" + 材料 | ingest | charlie-munger | cognitive |
| "央行降准空间还有多少" | query | macro | — |
| "检查一下 macro wiki" | lint | macro | — |

**本体类型**决定 wiki 的节点类型与采集策略：

| 本体类型 | 研究对象 | 节点类型 | 权威契约 / 参考 |
|---------|---------|---------|------|
| **domain** | 领域（机构、工具、指标、机制、事件） | 实体(机构/工具/指标) · 概念-机制 · 事件 · 分析 · 来源 | 各领域 `wiki/{domain}/_ontology.md` + `references/ontology-types/domain.md` |
| **cognitive** | 人（思维模型、决策方式） | mental-model · 概念 · 来源 · 分析 | `references/ontology-types/cognitive.md` |

**每个领域 wiki 的本体由它自己的 `wiki/{domain}/_ontology.md` 契约定义**（节点类型、受控关系词表、6 档时间模型、退役协议）；ingest/recall 前先读它。一个领域只用一种本体类型，不在同一领域里混用 cognitive 与 domain 结构。

**如果 wiki 目录不存在**，切换到 init，按 `references/init-protocol.md` 先访谈、展示提案并确认，再创建初始结构。不得跳过 init 直接猜用户的领域与关系。

**领域种子（seed）**：如果目标领域有对应的种子文件（`seeds/{name}.md`），在 meta.yaml 中声明 `seed: {name}`。种子提供标准术语词表、关系模板和禁混规则，让 wiki 从规范化的起点开始生长。没有种子的领域，wiki 自由生长——两种路径都能跑。种子是社区可贡献的插件，任何人可以为自己的垂直领域写一个 markdown 文件。详见 `references/seed-ontologies.md`。

**首次使用时**，执行环境检查（见 `references/source-validation.md`），告知用户当前可用的能力（被动模式 vs 主动模式）。

### Reference 加载策略

不要一次读完所有 reference。按操作类型按需加载：

| 操作 | 必读 | 首次时读 | 有工具时读 |
|------|------|---------|-----------|
| **survey** | `survey-protocol.md`, `survey.py`（跑，不必读） | `init-protocol.md`（要出提案草案时）, `seed-ontologies.md`（要起草种子时） | — |
| **init** | `init-protocol.md`, `storage-spec.md` | `seed-ontologies.md` + 适用的 `seeds/{name}.md` | — |
| **source** | `source-protocol.md` | — | `source-validation.md`（渠道分档/黑名单） |
| **ingest** | `ingest-protocol.md`, `wiki-format.md`, `schema.py`, `precheck.py`（跑，不必读） | `storage-spec.md`（wiki 不存在时）, `seed-ontologies.md` + `seeds/{name}.md`（meta.yaml 声明了 seed 时） | `fact-check.md`, `source-validation.md` |
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
4. **搜索 wiki 中已有的相关页面**（读 hub 页面，grep 关键实体名；机器辅助：`python references/precheck.py dup "{候选名}" --wiki wiki/{domain}` 输出同类型撞车候选——命中后建新页须在 log 写明不合并理由）
5. **逐页比较新旧信息**：
   - 新信息**支持**已有结论 → 加引用，提升 confidence
   - 新信息**推翻**已有结论 → 数值写入 data.db（旧值自动进 history 表），改写正文分析
   - 新信息**矛盾**且无法判断 → 并列两种说法，confidence → `contested`
6. **创建新页面**（仅当涉及 wiki 中没有的实体/概念）
7. **更新 hub 页面 + 追加 log.md**
8. **五试预检**——对本次创建/修改的所有页面运行 `python references/precheck.py page {page.md}`（镜头S = schema 硬闸 + R11 四病根：双 yaml 块/枚举夹注/relations 键名/必填缺失）。error 必须修复再落库；镜头D 的撞车提示是 advisory，不拦截，但要回到第 5 步复核是否该合并

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

1. 读 hub 页面，识别与问题相关的页面
2. 读取匹配页面 + 沿 wikilink 展开一层关联页面
3. 基于页面内容综合回答，**引用来源页面**：
   ```
   根据 wiki 中 5 篇源文件的积累：
   ... 分析内容 ...
   来源：[[alpha-corp]]、[[2026-policy-doc]]
   ```
4. 如果涉及 contested 信息，明确标注矛盾
5. 如果回答中包含有价值的新分析，提示用户归档

**如果 wiki 中信息不足以回答**，明确说明缺口，并按 `query-protocol.md`「query-miss 登记」在 ops 目录记一行（路径经 `python references/instance.py .` 解析，不要猜）：
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

- 每个页面是带 frontmatter 的 markdown（title, type, created, updated, sources, confidence；实体另有 subtype/aliases，机制有 durability，事件有 event_date）
- domain 节点类型：**实体**（subtype 机构/工具/指标）· **概念-机制** · **事件** · **分析** · **来源**（cognitive wiki 另有 mental-model）
- 数值绝不是节点（进 data.db）；分类标签是边不是页；关系用受控词表
- 用 `[[slug]]` 做页面间链接（中文 slug = 文件名 = wikilink = data.db 主键）
- hub 页面以**领域中文名**命名（如 `宏观.md`），是目录页 + 图谱中心；`log.md` 是操作日志

## 本体类型参考

当研究对象是**领域**时，权威是该领域的 `wiki/{domain}/_ontology.md` 契约，采集策略见 `references/ontology-types/domain.md`——节点侧重机构/工具/指标实体、机制、事件、量化指标（数值入 data.db）。

当研究对象是**人**时，参见 `references/ontology-types/cognitive.md`——节点侧重心智模型、启发式、价值体系、表达风格。

两者共用同一套 wiki 基础设施（ingest/query/lint、data.db 双时态表、退役不删除），区别仅在节点分类和采集侧重。

## 垂直领域适配

Skill 核心是领域无关的编译引擎。垂直领域的专业性通过两层插件注入：

| 层 | 载体 | 作用 | 必须？ |
|----|------|------|--------|
| **种子（seed）** | `seeds/{name}.md` | 冷启动词表：标准术语、关系模板、禁混规则 | 可选 |
| **校验器（validator）** | `validators/{name}.md` | 运行时逻辑校验：关系合法性、必要关系完整性 | 可选 |

没有插件，wiki 自由生长，适合探索性研究。有了插件，wiki 从行业标准起步，概念命名规范、关系结构清晰、逻辑缺口可检测。

**社区可贡献**：为你的垂直领域写一个 seed 文件（markdown），声明 20-50 个核心术语和禁混规则，就能让该领域的 wiki 从规范化起点生长。

当前可用：
- `seeds/reading-notes.md` — 读书、课程、论文、播客与通用学习
- `seeds/fibo-pensions.md` — 企业年金/养老金（基于 FIBO 标准）
- `validators/fibo-mcp.md` — FIBO SPARQL 逻辑校验（627K 推理三元组）

## 不做什么

- **不深度依赖任何查看器**。产物是纯 markdown + SQLite；`_report.html`（`schema.py --report`）提供零依赖可视化。Obsidian / IDE / 文件管理器都是可选适配器（适配约定见 `storage-spec.md`「Obsidian 兼容」），引擎不要求任何查看器存在。
- **不做向量检索**。小规模靠 hub 页面 + grep，大规模靠 SQLite FTS5 + BM25（见 `references/scaling.md`）。向量检索留给平台级工具。
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

## 导出：OKF 交换层（对外，单向）

把某个领域投影成一个 **OKF v0.1 bundle**（Open Knowledge Format，
GoogleCloudPlatform/knowledge-catalog）——markdown + frontmatter 目录的厂商中立
最小知识交换格式，唯一必填项是 frontmatter 的 `type`。给非 Obsidian 工具、外部
消费者、或想 `git` 交换知识时用。

```
python references/export_okf.py wiki/{domain}            # 默认输出到 <vault>/okf/{domain}/（wiki 树外，不进 Obsidian 图谱）
python references/export_okf.py wiki/{domain} --out <dir> --name "<显示名>"
```

触发词：`导出 okf` / `export okf` / `生成交换包` / `对外交换格式`。

**这是单向投影，不是平级存储**。本库的页面天生已满足 OKF（已带 `type`/`title`/
`relations`），导出几乎无损：节点页 → concept 文档、目录类型 → OKF type、`[[wikilink]]`
→ bundle 相对链接 `/dir/x.md`、Hub/类型目录 → `index.md`、`log.md` 原样合规。

**会被压平的（OKF 没有它们的结构位置）**——导出脚本把这些标 ⚠️ 后做有损投影：
- `data.db` 双时态层（T0 观测 / T1+T2 facts 拉链）→ 压成快照 markdown 表，丢 valid/
  transaction 两轴、supersedes 链、退役历史；
- 受控关系边的**类型**（`operated_by`/`bounds` 等）→ 链接本身无类型，类型降级进 prose；
  `bound_role`(upper/lower/center) 等边属性丢失。

**铁律：绝不反向以 OKF 为主存**——那会丢掉时间模型、类型边、可查询性这三样本库核心
价值。严格内核（data.db + 受控词表 + 6 档时间模型）只在库内享用，OKF 只是「出入境
口岸」。分类标签（`classified_as` 的 `价格型` 等，本库边非页）渲染成文字而非链接，
脚本从 `.burrow/config.json` 的 `dashboard.labels` 读取这份清单。
