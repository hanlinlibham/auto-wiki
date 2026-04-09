# Ingest 协议

> Ingest 不是追加文件，是编译——读旧、比新、改旧。

## 流程

```
1. 读取源文件
   ├─ 提取关键信息：实体、概念、数据、结论、时间
   └─ 生成 source 摘要页（sources/{date}-{slug}.md）

2. 搜索已有 wiki
   ├─ 读 index.md 获取全部页面列表
   ├─ 识别与新信息相关的已有页面
   └─ 读取这些页面的当前内容

3. 逐页比较新旧（核心步骤）——三种结果，必须选一个
   │
   ├─ A) 强化：新信息与已有结论一致，提供额外佐证
   │   → 在页面 sources 列表中加入新 source slug
   │   → 如果 confidence 是 medium/low → 升为 high
   │   → 正文不改或仅补充细节
   │   → log: "reinforced: {page}"
   │
   ├─ B) 更新：新信息明确推翻或修正已有结论（有更新数据/更权威来源）
   │   → store.upsert_data() 写入新值（旧值自动进 history 表）
   │   → 改写 Markdown 正文为新结论
   │   → 更新 frontmatter 的 updated 日期和 sources 列表
   │   → log: "updated: {page}, reason: {简述}"
   │
   └─ C) 冲突：新旧信息矛盾，但无法判断谁对（数据口径不同/来源同级）
       → 不改写，在页面中并列两种说法，标注各自来源
       → confidence → contested
       → log: "conflict: {page}, {说法A} vs {说法B}"
   
   判定规则：新信息有更新日期或更权威来源 → B（更新）；
   两者同级、无法分优劣 → C（冲突）；其余 → A（强化）。

4. 结构化数据写入 data.db
   ├─ 数值数据 → store.upsert_data()（自动处理 history）
   ├─ 关系 → store.add_relation()
   └─ 页面元数据 → store.upsert_page()

5. 创建/更新 Markdown 页面
   ├─ 新实体/概念 → 按 wiki-format.md 创建页面（frontmatter 只存元数据）
   ├─ 正文写叙事分析，引述数据结论但不重复具体数值
   ├─ 添加 wikilinks 到已有相关页面
   └─ 在已有相关页面中也加上指向新页面的 wikilink

6. 更新 index.md
   ├─ 新页面加入对应分组
   ├─ 更新页面计数和 Last updated 日期
   └─ 不修改已有条目的描述（除非页面标题变了）

7. 追加 log.md
   ├─ 记录本次 ingest 的所有操作
   └─ 格式见 wiki-format.md
```

## 关键原则

**1. 改旧优先于建新**

搜索 wiki 后发现已有 `entities/alpha-corp.md`，新研报也提到该机构 → 更新已有页面，不要新建 `entities/alpha-corp-2.md`。

**2. 不删除，只归档**

过时的结论不删除，移入 "## 历史" 段落。这样 wiki 保留了知识的演化痕迹。

```markdown
## 管理规模

截至 2025 年底，某机构管理规模达 XXX 亿元。（来源：[[2026-04-06-policy-doc]]）

## 历史

- ~~管理规模约 XXX 亿元~~（来源：[[2024-12-annual-report]]，已被更新数据替代）
```

**3. 冲突不调和**

两个来源说法矛盾时，不要编一个折中解释。并列呈现，标注来源，让用户或后续证据判断。

```markdown
## 市场份额

> ⚠️ contested — 两个来源数据不一致

- 据 [[2026-04-06-policy-doc]]：某机构市场份额约 15%
- 据 [[2025-annual-industry-report]]：某机构市场份额约 12%

差异可能来自统计口径不同（含/不含职业年金）。
```

**4. 一次 ingest 触及多个页面是正常的**

一篇研报可能涉及 5-10 个实体和概念。一次 ingest 更新 8 个页面是正常的。在 log 中完整记录。

**5. Source 页面是不可变的**

`sources/` 目录下的摘要页在创建后不再修改（除非发现摘要有错误）。它是原始材料的忠实记录。其他页面通过 `sources` frontmatter 字段引用它。

---

## Worked Example: 完整 Ingest 流程

> 以企业年金领域为例。实际执行时替换为用户的目标领域。

**场景**：用户 ingest 一篇政策文件到某领域 wiki。wiki 中已有相关实体页面。

### Step 1 — 读取源文件，生成 source 摘要页

新建 `sources/2026-04-06-hrss-policy.md`：

```yaml
---
title: 人社部2025年度企业年金基金统计报告
type: source
created: 2026-04-06
updated: 2026-04-06
sources: []
confidence: high
source_type: 一手
source_origin: 人社部官网
source_date: 2025-12-31
---
```

正文写原文关键信息的忠实摘要。

### Step 2 — 搜索已有 wiki

读 index.md，发现 `entities/alpha-corp.md` 与新文件相关。查询 data.db 中该页面的当前数据：

```python
store.query_data(page_slug="alpha-corp")
# → [{ field: "管理规模", value: 800, unit: "亿元", period: "2024-12", source_slug: "2024-12-annual-report" }]
```

### Step 3 — 比较新旧，判定结果

新文件说："截至 2025 年底，某机构管理规模达 1200 亿元。"

判定：新数据时点更新（2025 vs 2024）→ 选 **B) 更新**。

Agent 执行两步操作：

**a) 结构化数据写入 data.db**（自动记录 history）：

```python
old = store.upsert_data("alpha-corp", "管理规模", 1200, "亿元", "2025-12", "2026-04-06-policy-doc")
# old = { value: 800, unit: "亿元", source_slug: "2024-12-annual-report" }
# → history 表自动写入旧值
store.add_relation("alpha-corp", "受托人市场格局", "part_of")
```

**b) 更新 Markdown 页面**（frontmatter 只留元数据）：

```yaml
---
title: Alpha Corp 养老金业务
type: entity
created: 2026-04-01
updated: 2026-04-06
sources: [2024-12-annual-report, 2026-04-06-policy-doc]
confidence: high
relations:
  - target: 受托人市场格局
    type: part_of
---
```

正文更新分析内容（引述数据结论，不写具体数值——数值在 data.db 中）。

### Step 4-7 — 新建页面、写 DB、更新 index、追加 log

新文件还提到"可携带企业年金"概念（wiki 中不存在）→ 新建 `concepts/portable-annuity.md`：

```yaml
---
title: 可携带企业年金
type: concept
created: 2026-04-06
updated: 2026-04-06
sources: [2026-04-06-hrss-policy]
confidence: medium  # 仅单一来源首次提及
relations:
  - target: 企业年金制度
    type: part_of
---
```

log.md 追加：
```
## 2026-04-06 14:30 — ingest
- Source: 2026-04-06-policy-doc
- Updated: entities/alpha-corp (data.管理规模 800→1200亿)
- Created: concepts/portable-annuity
- Conflicts: none
```

---

## From-Lint 流程（deep-dive 管道的 ingest 阶段）

当 ingest 由 deep-dive 管道触发时，输入不是用户提供的源文件，而是 lint Coverage 输出的缺口报告（Gap Report）。

### 与标准 ingest 的区别

| 方面 | 标准 ingest | from-lint ingest |
|------|------------|------------------|
| 输入 | 用户提供的源文件 | Gap Report 中的缺口条目 |
| 来源获取 | 用户已提供 | Agent 通过搜索工具获取 |
| 批量操作 | 通常 1 个源文件 | 可能 N 个缺口，逐个处理 |
| 用户确认 | 不需要（用户已主动提供） | 需要（搜索前确认范围，搜索后确认质量） |

### 流程

```
输入：Gap Report（来自 lint Coverage）

For each confirmed gap:

1. 制定搜索计划
   ├─ page_missing → 搜索该实体/概念的基本信息
   ├─ concept_missing → 搜索该术语的定义和解释
   ├─ data_missing → 搜索该指标的最新数据
   ├─ single_source → 搜索额外来源以交叉验证
   └─ outdated → 搜索该指标/实体的最新信息

2. 执行搜索（需要搜索工具——主动模式）
   ├─ 使用 WebSearch / 搜索类 MCP 获取候选来源
   ├─ 搜索工具优先级：领域专业工具 > 通用搜索
   ├─ 按 source-validation.md 分级筛选
   └─ 排除黑名单渠道，取 top 1-3 个可信来源

3. 展示搜索结果，请用户确认
   ├─ 展示每个来源的标题、URL、可信度分级
   ├─ 用户选择：接受 / 跳过 / 替换
   └─ 搜索结果质量不够 → 标注"未能补全"，跳过

4. 对确认的每个来源，执行标准 ingest 流程
   ├─ Step 1-7 与普通 ingest 完全一致
   └─ source 摘要页额外记录 deep-dive 元数据（见 source-validation.md）
```

### 防扩散机制

- 每个 gap 最多搜索 3 次（换关键词）。3 次搜不到可信来源 → 标注"未能补全"
- 单次 deep-dive 最多处理 10 个 gap（可通过 `--max-gaps` 调整）
- 搜索到的来源如果引入了 wiki 中完全不存在的新实体，**不自动创建页面**——只填补已知缺口，不主动扩展 wiki 范围
- 所有搜索来源的 confidence 上限为 medium（除非来源是一手/权威二手）

### 补全报告

```
## Deep-Dive 补全报告：{topic}
执行时间：{date}

### 已补全：{N} / {total} 个缺口
| # | Gap | Action | Source | Confidence |
|---|-----|--------|--------|------------|
| 1 | page_missing: portable-annuity | 新建页面 | [二手·权威] 财新报道 | medium |
| 2 | single_source: alpha-corp | 增加 1 个来源 | [二手] 行业研报 | medium |

### 未能补全：{M} 个缺口
| # | Gap | Reason |
|---|-----|--------|
| 3 | data_missing: beta-corp/市场份额 | 搜索 3 次未找到可信来源 |

### 建议
- beta-corp 市场份额数据建议用户手动提供行业报告
```
