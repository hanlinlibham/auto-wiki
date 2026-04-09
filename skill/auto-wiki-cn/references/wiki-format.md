# Wiki 页面格式

> **所有 frontmatter 结构由 `schema.py` 中的 Pydantic 模型定义和校验。**
> 本文档是人类可读的规范说明，`schema.py` 是机器可执行的校验工具。两者必须一致。
> 校验命令：`python references/schema.py .wiki/{主题}/`

## 目录结构

每个研究主题一个目录：

```
{主题名}/
├── meta.yaml         # Wiki 元数据（见 storage-spec.md）
├── index.md          # 页面目录（Agent 维护，按类型分组）
├── log.md            # 操作日志（append-only，人类可读）
├── sources/          # 源文件摘要
├── entities/         # 实体页（机构、人物、产品）
├── concepts/         # 概念页（制度、方法、指标）
└── analyses/         # 分析归档（query 产出的有价值分析）
```

cognitive 类型 wiki 的目录变体：
```
{人物名}/
├── mental-models/    # 替代 entities/——每个心智模型一个页面
├── concepts/         # 启发式、价值观、表达风格、矛盾
├── sources/          # 采集来源
└── analyses/         # 分析归档
```

## 页面格式

每个页面分为两部分：**YAML frontmatter（结构化数据）** + **Markdown 正文（叙事分析）**。

**核心原则：数据放 YAML，分析放正文。** 正文不写数据表格。

---

## Frontmatter Schema

### 基础字段（所有页面必填）

```yaml
---
title: 页面标题
type: entity                    # entity | concept | source | analysis | mental-model
created: 2026-04-06
updated: 2026-04-06
sources: [source-slug-1, source-slug-2]
confidence: high                # high | medium | low | contested
tags: [entity]                  # 必填：页面类型 + 可选状态标签
aliases: []                     # 可选：页面别名
---
```

| 字段 | 必填 | 说明 |
|------|------|------|
| title | 是 | 页面标题 |
| type | 是 | 页面类型 |
| created | 是 | 创建日期 YYYY-MM-DD |
| updated | 是 | 最后更新日期（每次修改必须更新） |
| sources | 是 | 引用的 source 页面 slug 列表（source 类型页面填 `[]`） |
| confidence | 是 | 置信度：`high` / `medium` / `low` / `contested` |
| tags | 是 | Obsidian 标签列表，用于搜索过滤和分类浏览 |
| aliases | 否 | 页面别名列表，用于 Obsidian 搜索和链接补全 |

### tags 规则（Obsidian 搜索过滤必需）

`tags` 必须包含页面类型（`source` / `entity` / `concept` / `analysis` / `mental-model`），可追加状态标签：

```yaml
tags:
  - concept                    # 必填：页面类型
  - contested                  # 可选：confidence=contested 时加
  - low-confidence             # 可选：confidence=low 时加
```

source 类型页面额外加来源等级标签：

```yaml
tags:
  - source
  - primary-source             # 一手来源
  # 或 authoritative-secondary / secondary / hearsay / inference
```

这些标签用于 Obsidian 搜索过滤（如在搜索栏输入 `tag:#contested` 快速定位有争议的页面）。图谱着色不依赖 tags——靠 `path:` 规则区分页面类型，靠 `[confidence:contested]` Properties 查询高亮风险节点。

### aliases 规则

标题含括号说明时，拆出短名和括号内容作为别名：

```yaml
title: EET 税收模式（个人养老金税优机制）
aliases:
  - EET 税收模式
  - 个人养老金税优机制
```

### 结构化数据 → data.db

**所有可量化、可查证、可对比的数据写入 `data.db`（SQLite），不放在 frontmatter 中。**

Agent 在 ingest 时调用 `store.py` 的 `WikiStore` 接口：

```python
store.upsert_data("alpha-corp", "管理规模", 1350, "亿元", "2025-Q1", "2026-04-policy-doc", scope="含职业年金")
store.upsert_data("alpha-corp", "市场份额", 12, "%", "2025-Q1", "2026-04-policy-doc", confidence="contested")
```

如果同字段同时段已有旧值，`upsert_data` 自动将旧值写入 `history` 表并返回旧记录。

**数据字段规范**（由 `store.py: data_points` 表约束）：

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `page_slug` | **是** | TEXT | 所属页面的 slug |
| `field` | **是** | TEXT | 数据维度名（如"管理规模"） |
| `value` | **是** | REAL | 数值 |
| `unit` | **是** | TEXT | 单位（亿元、%、万人、家...） |
| `period` | **是** | TEXT | 数据时点（如 "2023-12"、"2025-Q1"） |
| `source_slug` | **是** | TEXT | source 页面 slug |
| `scope` | 否 | TEXT | 统计口径说明 |
| `verified` | 否 | INTEGER | NULL=未知, 0=未验证, 1=已验证 |
| `confidence` | 否 | TEXT | 该数据点的置信度 |

**每个数字都必须有出处。** `source_slug` 指向哪个 source 页面。

**查询示例**：

```python
# 某机构的所有数据
store.query_data(page_slug="alpha-corp")

# 某字段的时间线（含历史值）
store.query_timeline(field="管理规模")

# 所有 contested 数据
store.conn.execute("SELECT * FROM data_points WHERE confidence='contested'").fetchall()
```

### relations 字段（结构化关系）

页面间的语义关系，补充正文中的 `[[wikilink]]`：

```yaml
relations:
  - target: beta-corp
    type: competes_with
  - target: 受托人市场格局
    type: part_of
  - target: national-council-ssf
    type: regulated_by
```

**常用关系类型**：

| type | 含义 | 示例 |
|------|------|------|
| `part_of` | 属于 | 某机构 part_of 受托人市场 |
| `manages` | 管理 | 受托人 manages 年金基金 |
| `regulated_by` | 受监管 | 机构 regulated_by 人社部 |
| `competes_with` | 竞争 | 机构A competes_with 机构B |
| `implements` | 实施 | 机构 implements 受托责任 |
| `derived_from` | 来源于 | 概念 B derived_from 概念 A |
| `contradicts` | 矛盾 | 数据 A contradicts 数据 B |
| `influenced_by` | 受影响（cognitive 类型） | 心智模型 influenced_by 人物 |
| `applies_to` | 适用于 | 心智模型 applies_to 领域 |

**relations 规范**：
- `target` 填 slug（不加路径前缀）
- `type` 从上表选取，或自定义（但保持项目内一致）
- relations 是 frontmatter 中的结构化声明，正文中的 `[[wikilink]]` 是人类可读的引用——两者互补

### source 类型页面的额外字段

```yaml
---
title: 人社部2024年度企业年金基金统计报告
type: source
created: 2026-04-06
updated: 2026-04-06
sources: []
confidence: high
source_type: 一手               # 一手 | 二手·权威 | 二手 | 转述 | 推断 | 口述
source_origin: 人社部官网
source_date: 2024-12-31         # 原始材料的日期（不是 ingest 日期）
source_url: ""                  # 来源 URL（如有）
---
```

### cognitive 类型（心智模型页）的额外字段

```yaml
---
title: 能力圈
type: mental-model
created: 2026-04-06
updated: 2026-04-06
sources: [poor-charlies-almanack]
confidence: high
verification:
  cross_domain: true            # 跨域复现
  generative: true              # 有生成力
  exclusive: true               # 有排他性
  domains: [投资, 商业决策, 人生选择]  # 出现过的领域
---
```

---

## 正文约定

**正文只写叙事分析和上下文解读，不写数据表格。**

以下为示例（以金融领域为例）：

```markdown
# 某机构业务概况

该机构是行业规模最大的参与者之一。2025年Q1管理规模增至 XXX 亿元，
但市场份额数据因统计口径变更与上期报告不可直接比较。

[[competitor-a|竞争对手 A]]同期增速行业第一，正在缩小差距。
详见 [[市场格局]]。
```

**正文规则**：
- 用 `[[slug]]` 或 `[[slug|显示名]]` 做页面链接
- 提到数据时引述结论，不重复 frontmatter 中的具体数值（避免不一致）
- 可以用 `> ⚠️` blockquote 标注重要警告（如口径差异）
- 分析性内容是正文的核心价值——这是 YAML 无法承载的部分

---

## 文件命名

- slug 格式：小写字母 + 连字符，如 `alpha-corp.md`
- 中文概念用中文 slug：`受托人市场格局.md`（Obsidian 友好）或拼音 slug
- source 页面加日期前缀：`2026-04-06-hrss-report.md`（连字符分隔）

## index.md 格式

index 只做导航，不内联数据：

```markdown
# {主题名} Wiki Index

> {N} pages | Last updated: {日期} | Type: {ontology_type}

## Entities ({N})
- [[alpha-corp]] — 机构 A 养老金业务
- [[beta-corp]] — 机构 B 养老保险

## Concepts ({N})
- [[受托人市场格局]] — 受托人竞争格局与份额
- [[企业年金制度]] — 政策法规与制度框架

## Sources ({N})
- [[2026-04-06-hrss-report]] — 人社部2024年度报告
- [[2026-04-06-q1-briefing]] — 2025年一季度市场简报

## Analyses ({N})
- [[trustee-comparison]] — 受托人市场格局对比分析
```

**index 规则**：每个条目一行，`[[slug]] — 一句话描述`。不放表格、不放统计数据。

## log.md 格式

```markdown
# {主题名} Wiki Log

## 2026-04-06 14:30 — ingest
- Source: 2026-04-06-hrss-report
- Created: entities/alpha-corp, concepts/受托人市场格局
- Updated: (无)
- Conflicts: (无)

## 2026-04-06 15:00 — ingest
- Source: 2026-04-06-q1-briefing
- Updated: entities/alpha-corp (管理规模 1200→1350亿，份额 contested)
- Created: entities/beta-corp
- Conflicts: alpha-corp.市场份额 (15% vs 12%，口径不同)
```

## Validation Rules

| 规则 | 要求 |
|------|------|
| frontmatter 完整 | `title`, `type`, `created`, `updated`, `sources`, `confidence` 六字段必须存在 |
| type 值合法 | `source` / `entity` / `concept` / `analysis` / `mental-model` |
| data 字段规范 | 每个数据点必须有 `value`, `unit`, `period`, `source` |
| history 有 reason | 每条历史记录必须有 `reason` 字段 |
| relations 有 type | 每条关系必须有 `target` 和 `type` |
| sources 非空 | 除 source 类型外，`sources` 列表至少一个 slug |
| 日期格式 | `YYYY-MM-DD` |
| slug 与文件名一致 | 文件名（去 `.md`）= slug |

## 置信度更新规则

| 事件 | 置信度变化 |
|------|-----------|
| 新 source 印证已有数据（data 字段一致） | → `high` |
| 新 source 更新已有数据（有更新时点/更权威来源） | 更新 data，旧值进 history |
| 新 source 与已有数据矛盾且无法判断 | data 中该字段 confidence → `contested` |
| lint 发现 data 中有无 source 的字段 | → `low` |
| 页面 6 个月未被 ingest 触及 | lint 建议标注"待验证" |
