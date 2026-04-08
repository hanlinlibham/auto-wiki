---
name: knowledge-compiler
description: |
  知识编译器：教 Agent 把源文件增量编译进持久化 wiki，实现跨会话知识积累。
  三个操作：ingest（投入源文件）、query（基于 wiki 回答）、lint（治理 wiki 健康度）。
  触发词：「ingest」「编译」「整理这篇」「wiki」「知识库」「lint」「检查 wiki」
  「研究一下」「积累」「归档」「消化这篇」「学习这个」「研究 XX 这个人」。
---

# 知识编译器

> Agent 做研究、拉数据、写报告——wiki 把这些产出串起来。Agent 越用越懂你的领域。

## Quick Start

```
用户: ingest 这篇行业报告到 XX wiki
Agent: [读取报告 → 搜索已有 wiki → 比较新旧 → 更新 3 页、新建 1 页]
Agent: 已 ingest 到 XX wiki：更新 3 页（列出），新建 1 页（列出）
```

## 核心理念

Agent 每天帮你做研究、写报告、拉数据——但做完就忘。下次问同样领域的问题，又从零开始。

这个 Skill 解决一件事：**给 Agent 一个可以持续积累的知识库。**

不是 RAG（每次从文档堆里临时检索），是编译——Agent 读完源文件后，把关键信息**写进 wiki 已有页面**，和旧知识比较、合并、标注冲突。下次执行任何任务前，先读 wiki，从积累的基础上工作。

## 三个操作

| 操作 | 触发 | Agent 做什么 |
|------|------|-------------|
| **ingest** | 用户提供源文件或文本 | 读源文件 → 搜索已有 wiki → 比较新旧 → 更新/创建页面 → 更新索引 |
| **query** | 用户提问 | 读 index → 找相关页面 → 综合回答 → 有价值的分析可归档 |
| **lint** | 用户说"检查 wiki" | 扫描全部页面 → 合并重复 → 归档过时 → 报告矛盾和健康度 |

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

**如果 wiki 目录不存在**，按 `references/storage-spec.md` 创建初始结构（含 meta.yaml、index.md 模板、log.md 模板）。

**首次使用时**，执行环境检查（见 `references/source-validation.md`），告知用户当前可用的能力（被动模式 vs 主动模式）。

### Reference 加载策略

不要一次读完所有 reference。按操作类型按需加载：

| 操作 | 必读 | 首次时读 | 有工具时读 |
|------|------|---------|-----------|
| **ingest** | `ingest-protocol.md`, `wiki-format.md`, `schema.py` | `storage-spec.md`（wiki 不存在时）, `seed-ontologies.md` + `seeds/{name}.md`（meta.yaml 声明了 seed 时） | `fact-check.md`, `source-validation.md` |
| **query** | `query-protocol.md` | — | — |
| **lint** | `lint-protocol.md`, `schema.py` | — | `validators/{name}.md`（seed 声明了 validator 时） |

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

## 不做什么

- **不做向量检索**。小规模靠 index + grep，大规模靠 SQLite FTS5 + BM25（见 `references/scaling.md`）。向量检索留给平台级工具。
- **不做多用户协作**。wiki 目录是本地文件，一个用户一个 wiki。
- **不替代专业数据工具**。领域数据获取用对应的 MCP/工具，本 Skill 只接住它们的产出并编译进 wiki。

## 与其他工具的关系

本 Skill 不替代任何专业工具，它**串联**它们：

```
任意研究工具产出分析 → ingest 进对应 wiki
任意数据工具拉数据   → ingest 进对应 wiki

下次执行任务时，Agent 先读相关 wiki → 带着积累的知识工作
```
