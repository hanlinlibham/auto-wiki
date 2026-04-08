# 人作为本体：Nuwa 与领域本体的统一视角

> 从 Nuwa（人物认知框架提炼）出发，思考"人"是否构成一种本体，
> 以及它如何与领域本体（如企业年金）统一到同一个知识生命周期中。

## 核心问题

企业年金本体建模的是一个**领域**——实体（机构、计划、产品）、关系（管理、监管）、约束（Plan ≠ PensionProduct）。

Nuwa 建模的是一个**人**——心智模型、决策启发式、表达 DNA、价值体系、内在矛盾。

这两件事看似完全不同。但如果退后一步看结构：

| 维度 | 领域本体（企业年金） | 人物本体（Nuwa） |
|------|---------------------|------------------|
| 实体类型 | Institution, Plan, Fund, Metric | MentalModel, Heuristic, Value, StylePattern |
| 关系 | manages, regulates, belongs_to | influenced_by, contradicts, applies_to, derived_from |
| 约束 | Plan ≠ PensionProduct | "从不对冲语气"、"二元判断系统" |
| 属性 | 净值、规模、成立日期 | 证据域、生成力、排他性、频率 |
| Schema | DDL + 类型定义 | extraction-framework.md + skill-template.md |

**结构上是同构的。** 两者都是：有类型的节点 + 有语义的边 + 结构化约束。区别只是节点和边的语义不同。

## Nuwa 已经在做 Wiki → 本体

更值得注意的是，Nuwa 的工作流已经暗合了 wiki-builder 设计中的知识生命周期：

```
Nuwa 工作流                          Wiki-Builder 对应

30+ 原始来源（书、演讲、访谈、决策）    ──▶  Raw Sources
        │
        ▼
6 份研究文件（writings, conversations,   ──▶  Wiki（软知识层）
  expression, external, decisions,           编译后的结构化理解
  timeline）≈ 2800 行/人
        │
        ▼
三重验证（跨域复现 × 生成力 × 排他性）  ──▶  Lint / 质量门
        │
        ▼
SKILL.md（3-7 心智模型 + 启发式 +       ──▶  Ontology（硬知识层）
  表达 DNA + 价值体系 + 矛盾）               结晶后的可执行框架
  ≈ 320 行/人
```

Nuwa 的 6 份研究文件**就是** wiki 层——跨源综合、交叉引用、矛盾标注。
Nuwa 的 SKILL.md **就是**结晶后的本体——强类型的心智模型、有验证标准的启发式、量化的表达风格。
Nuwa 的三重验证**就是** lint + crystallize 的质量门。

**Nuwa 已经在做本体，只是没有用这个词。**

## "人"是什么类型的本体

领域本体回答的是：**这个世界的某个切面是怎么构成的**（企业年金制度由哪些实体、关系、规则组成）。

人物本体回答的是：**一个认知主体是怎么运作的**（Steve Jobs 的思维由哪些心智模型、决策规则、价值取向、风格模式组成）。

两者的区别不在结构，而在**本体论层次**：

```
┌─────────────────────────────────────────────────┐
│            Meta-Ontology（元本体）                 │
│  "本体有哪些类型？每种类型的 schema 是什么？"       │
│                                                  │
│  ┌──────────────┐  ┌──────────────┐              │
│  │ 领域本体       │  │ 认知本体       │  ...        │
│  │ Domain        │  │ Cognitive     │              │
│  │               │  │               │              │
│  │ 建模对象：     │  │ 建模对象：     │              │
│  │ 世界的结构     │  │ 人的思维结构   │              │
│  │               │  │               │              │
│  │ 节点类型：     │  │ 节点类型：     │              │
│  │ Entity,       │  │ MentalModel,  │              │
│  │ Concept,      │  │ Heuristic,    │              │
│  │ Metric        │  │ Value,        │              │
│  │               │  │ StylePattern, │              │
│  │ 边类型：       │  │ Contradiction │              │
│  │ manages,      │  │               │              │
│  │ regulates,    │  │ 边类型：       │              │
│  │ belongs_to    │  │ influenced_by,│              │
│  │               │  │ contradicts,  │              │
│  │ 验证标准：     │  │ applies_to    │              │
│  │ DDL 一致性，   │  │               │              │
│  │ 禁混规则      │  │ 验证标准：     │              │
│  │               │  │ 三重验证       │              │
│  │ 实例：        │  │ （跨域×生成力  │              │
│  │ 企业年金       │  │  ×排他性）    │              │
│  │ 公募基金       │  │               │              │
│  │ 固收/债券      │  │ 实例：        │              │
│  │ ...           │  │ Steve Jobs    │              │
│  └──────────────┘  │ Charlie Munger│              │
│                     │ Naval Ravikant│              │
│                     │ ...           │              │
│                     └──────────────┘              │
└─────────────────────────────────────────────────┘
```

**领域本体和认知本体是同级的本体类型**，都可以被同一套基础设施（Schema Registry + Edge Store + 约束规则）承载。它们的 meta-schema 不同（节点类型和边类型的定义不同），但底层机制相同。

## 交叉点：人 × 领域

更有趣的是，人物本体和领域本体之间存在交叉：

**Charlie Munger 的心智模型中有"多元思维模型"**，其中包含会计学、心理学、工程学等领域的概念。这些概念可以链接到对应的领域本体。

**一个企业年金领域的分析师**，他的认知本体中包含"受托责任"、"组合分类"等概念，这些正是企业年金领域本体中的实体。

```
认知本体（Munger）                    领域本体（价值投资）
┌──────────────┐                    ┌──────────────┐
│ MentalModel:  │                    │ Entity:       │
│ "护城河分析"   │───applies_to──────▶│ "经济护城河"   │
│               │                    │               │
│ Heuristic:    │                    │ Concept:      │
│ "能力圈"      │───constrains──────▶│ "投资范围"     │
└──────────────┘                    └──────────────┘
```

**人物本体提供了"用谁的视角看"，领域本体提供了"看的是什么"。** 两者的交叉就是：用 Munger 的思维框架分析企业年金领域的问题。

## 对 Nuwa 的启示：引入本体思想后会怎样

### 现状的局限

当前 Nuwa 的人物建模是**扁平的 markdown**——心智模型、启发式、表达 DNA 都是文本段落。没有显式的类型系统、没有边的定义、没有跨人物的关系。

这意味着：
- **无法跨人物比较**：Jobs 和 Musk 都有"第一性原理"，但两人的理解不同。当前格式下这种区别只能靠文本描述，无法结构化查询
- **无法追踪影响链**：Munger 影响了 Buffett 影响了 Naval，这条链在当前格式下散落在各自的 "Intelligence Genealogy" 段落中
- **无法与领域本体联动**：Munger 的 "护城河" 概念和商业分析领域的 "Economic Moat" 实体之间没有显式链接

### 引入本体后的可能性

如果把 Nuwa 的提炼框架映射为一个 Cognitive Ontology Schema：

```
# cognitive_ontology_schema

NodeTypes:
  - MentalModel:
      fields: [name, definition, evidence_domains[], generative_power, exclusivity]
      validation: three_fold_verification
  - DecisionHeuristic:
      fields: [name, rule, trigger_scenario, scope, counterexample]
  - Value:
      fields: [name, priority_rank, type(pursue|refuse|unresolved)]
  - StylePattern:
      fields: [dimension, value, evidence]
  - Person:
      fields: [name, era, domains[], research_date, source_count]

EdgeTypes:
  - influenced_by: Person → Person (weight, evidence)
  - holds: Person → MentalModel
  - applies_to: MentalModel → DomainConcept  # 跨本体链接
  - contradicts: MentalModel → MentalModel (within same person = 内在矛盾)
  - derived_from: MentalModel → MentalModel (across persons = 思想传承)
  - evolved_to: MentalModel → MentalModel (same person, different era = 思想演化)

Constraints:
  - MentalModel must pass three_fold_verification (跨域 × 生成力 × 排他性)
  - Each Person must have 3-7 MentalModels (fewer = insufficient, more = diluted)
  - contradicts edges require evidence from both sides
  - influenced_by must have directional evidence (not just co-occurrence)
```

这样就能做到：

1. **跨人物查询**："谁持有'第一性原理'类心智模型？他们的理解有什么不同？"
2. **影响链追踪**："从 Taleb 到 Naval 的思想传播路径是什么？哪些模型被保留，哪些被变异？"
3. **认知 × 领域联动**："用 Munger 的心智模型集合分析企业年金领域，哪些模型适用？"
4. **矛盾网络**："Jobs 和 Musk 在'控制力 vs 开放性'上各自怎么处理？他们的矛盾结构是否同构？"

## 统一的 AutoResearch 框架

将 LLM Wiki + 领域本体 + 人物本体统一起来，得到一个通用的 AutoResearch 框架：

```
┌─────────────────────────────────────────────────────────────┐
│                     AutoResearch 框架                        │
│                                                              │
│  输入层：  Raw Sources（文档、数据、书籍、演讲、访谈...）       │
│                          │                                   │
│                          ▼                                   │
│  编译层：  Wiki-Builder 子 Agent                              │
│           - ingest: 源文件 → wiki 页面                        │
│           - query: wiki 检索 → 综合回答                       │
│           - lint: 一致性检查 + 模式检测                        │
│                          │                                   │
│                          ▼ (模式稳定时)                       │
│  结晶层：  Crystallize                                        │
│           - 从 wiki 中提炼 typed schema                      │
│           - 人工审核 → Schema Registry                        │
│                          │                                   │
│                          ▼                                   │
│  运营层：  Typed Ontology                                     │
│           - 语义检索注入 Agent                                │
│           - 约束校验反哺 wiki                                 │
│           - 跨本体链接（人×领域）                              │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │ 本体类型注册表                                        │     │
│  │                                                      │     │
│  │ DomainOntology    认知本体 (Cognitive)                │     │
│  │  ├ 企业年金         ├ Steve Jobs                      │     │
│  │  ├ 公募基金         ├ Charlie Munger                  │     │
│  │  ├ 固收/债券        ├ Naval Ravikant                  │     │
│  │  └ ...             └ ...                             │     │
│  │                                                      │     │
│  │ 未来可能的本体类型：                                    │     │
│  │  - 组织本体 (Organizational): 公司文化、决策流程         │     │
│  │  - 事件本体 (Event): 金融危机、政策变迁的结构化叙事      │     │
│  │  - 方法论本体 (Methodological): 研究方法、分析框架       │     │
│  └─────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

**Wiki-Builder 是通用的**——它不关心你研究的是一个领域还是一个人。它只做：ingest 源文件 → 积累结构化页面 → 检测模式 → 触发结晶。

**本体 Schema 是特化的**——领域本体的 schema（Entity, Concept, Metric）和认知本体的 schema（MentalModel, Heuristic, Value）不同，但它们注册在同一个 Schema Registry 里，通过跨本体边连接。

**Nuwa 的提炼框架（extraction-framework.md）本质上就是认知本体的 crystallize 规则**——三重验证、3-7 模型约束、表达 DNA 量化标准。它可以直接注册为 cognitive ontology 的 schema 定义。

## 对实现的影响

1. **Wiki-Builder 的 schema.md 需要支持多种本体类型**。当用户开始研究一个人时，wiki 的约定应该切换到 cognitive ontology 的页面格式（实体页变成心智模型页，概念页变成启发式页）

2. **Nuwa 的 extraction-framework.md 可以直接作为 cognitive ontology 的 schema 注册进 Schema Registry**，和 base_domain.json（领域本体 schema）并列

3. **跨本体边是未来的高价值功能**。"用 Munger 视角分析企业年金"需要 cognitive ontology 和 domain ontology 之间的 applies_to 边

4. **Wiki-Builder 的 crystallize 操作需要知道当前研究的本体类型**，才能选择正确的验证标准（领域本体用 DDL 一致性，认知本体用三重验证）

## 开放问题

1. **本体类型是固定枚举还是用户可扩展的？** 如果用户想研究一个组织（不是人也不是领域），需要定义新的本体类型
2. **Nuwa 的 6 个并行 Agent 研究框架如何映射到 wiki-builder 的 ingest 操作？** 是一次 ingest 触发 6 路并行，还是 6 次独立 ingest？
3. **人物本体的"时效性"问题**：领域本体相对稳定（企业年金制度不会每天变），但人是活的——一个人的心智模型会演化。wiki 层如何追踪这种演化？
4. **SKILL.md 是本体的"可执行投影"**：本体是结构化数据，SKILL.md 是从本体生成的、Agent 可直接执行的 prompt。这种"本体 → 可执行 prompt"的生成是否应该是框架的标准操作？
