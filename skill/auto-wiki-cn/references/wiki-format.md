# Wiki 页面格式

> **本文档是领域无关的引擎规范。** 它定义 wiki 里每一页长什么样、frontmatter 有哪些字段、关系怎么写、数值往哪放。具体某个领域的本体契约(如 `wiki/macro/_ontology.md`)是这套规范的一个实例 —— 引擎规范在前,领域契约在后,两者一致时领域契约优先具体化。
>
> **所有 frontmatter 结构由 `schema.py` 中的 Pydantic 模型定义和校验。** 本文档是人类可读的规范说明,`schema.py` 是机器可执行的校验工具,两者必须一致。
> 校验命令:`python references/schema.py wiki/{领域}/`

---

## 三条总原则(先立规矩)

1. **节点 / 数据 / 边 三分**。
   - **数值绝不是节点** —— `7天逆回购利率=1.40%` 不建页,进 `data.db`。图谱里只有"7天逆回购利率"这条命名序列,没有"1.40%"这个点。frontmatter 里也不放具体数值。
   - **关系是边不是点** —— "央行运行7天逆回购"是一条 `operated_by` 边,不是一个叫"运行"的节点。
   - **分类标签不是节点** —— "数量型/价格型/结构性"这类给一堆东西分桶的标签,是贴在节点上的 `classified_as` 边,不单独建页。
2. **数据放结构(YAML / data.db),分析放正文。** 正文不写数据表格,只写叙事分析。frontmatter 承载结构化事实,data.db 承载数值/状态/事件/关系,正文承载 YAML 无法表达的解读。
3. **编译是单向的**:`Inbox(人写散文)→ ingest → wiki(本体产物)`。wiki 只反向被 `recall` 消费。严谨用在已结晶的知识(wiki),不用在正在结晶的知识(Inbox)。

---

## 目录结构(类型即目录,目录即图谱着色)

wiki 按**领域(domain)** 组织,不按研究课题(topic)。一个领域一个目录,目录下按节点类型分子目录。研究课题降级为 `分析/` 下的一页,不再单独开顶层目录。

```
wiki/{领域}/                 # 如 wiki/macro/
├── _ontology.md            # 本领域的本体契约(人和 Agent ingest/recall 前先读)
├── {领域中文名}.md          # Hub / MOC,图谱导航中心(如 宏观.md)
├── log.md                  # ingest 操作日志(append-only,人类可读)
├── data.db                 # 唯一真相源:数值、状态、事件、关系
├── 机构/   …               # 实体·机构 (红,中心)
├── 工具/   …               # 实体·工具 (蓝)
├── 指标/   …               # 实体·指标 (青)
├── 机制/   …               # 概念·机制 (绿)
├── 事件/   …               # 事件 (黄)
├── 分析/   …               # 分析:研究课题/派生视图归档 (灰)
└── 来源/   …               # 来源:研报/文章原文承载页 (浅灰)
```

**颜色纪律**:Obsidian graph 按 `path:机构/` 等子目录着色。**顶层节点目录 ≤ 6 个 = ≤ 6 色**(9 色肉眼分不清,实体三子目录共用红/蓝/青三色,事件/分析/来源各一色,机制一色)。`graph.json` 里不要放排在最后的 `path:wiki` catch-all 灰色规则,否则会盖掉所有颜色。

> **wiki/ 必须是可见目录** —— 纳入 git、进 Obsidian 图谱、人类可直接浏览。**禁止用 `.wiki/` 点目录**(Obsidian 隐藏 dotfolder,图谱里看不见)。

---

## 节点类型(从 5 种扩展为 7 种)

| 类型 | type 值 | subtype | 子目录 | 判据 | 中文标签 | 图谱色 |
|---|---|---|---|---|---|---|
| **实体·机构** | `entity` | `institution` | `机构/` | 有专名的行为主体 | `实体` `机构` | 红(中心) |
| **实体·工具** | `entity` | `instrument` | `工具/` | 有专名、被某机构创设并运行的工具 | `实体` `工具` | 蓝 |
| **实体·指标** | `entity` | `indicator` | `指标/` | 可反复取数的命名时间序列(身份是序列,不是某天的值) | `实体` `指标` | 青 |
| **概念·机制** | `concept` | — | `机制/` | 必须靠内涵定义才能理解的机理/框架 | `概念` `机制` | 绿 |
| **事件** | `event` | — | `事件/` | 有确定日期+施动者、发生过一次就不再发生 | `事件` | 黄 |
| **分析** | `analysis` | — | `分析/` | 基于上述节点得出的研究判断(派生视图,删了不影响本体) | `分析` | 灰 |
| **来源** | `source` | — | `来源/` | 一篇研报/文章原文的承载页,所有断言可溯源到它 | `来源` | 浅灰 |

### 核心判据:individual vs class

> **「我能不能用手指指向'就是这一个'、而且明年用同一个名字还指同一个东西?」**
> 能 → **实体(individual)**;不能、必须先讲一段"它是怎么运作/怎么定义的"才能让人听懂 → **概念/机制(class)**。

 "有没有数据 / 有没有结构 / 抽象不抽象"会骗你 —— 利率走廊有上下限结构和数值,但它仍是概念(没有"创设它的那一个专名物")。唯一可靠的判据只有"能不能用手指指向那一个"。这取代了旧版"抽象不抽象 / 有没有数据"的判据。

> **注**:旧版有 `mental-model`(心智模型)类型用于 cognitive 类 wiki。在 v2 引擎里,心智模型按 `concept`(机制)建模 —— 它也是"必须先讲定义才懂"的 class。若某领域确实需要单独子类,在该领域 `_ontology.md` 中扩展,不在引擎层默认开。

---

## 页面格式

每个页面分为两部分:**YAML frontmatter(结构化数据)** + **Markdown 正文(叙事分析)**。

---

## Frontmatter Schema

### 基础字段(所有页面必填)

```yaml
---
title: 7天逆回购
type: entity                    # entity | concept | event | analysis | source
created: 2026-06-07
updated: 2026-06-07             # 每次修改必须更新
sources: [2026-05-25-某券商固收报告]   # 引用的 source 页 slug(source 类型填 [])
confidence: high                # high | medium | low | contested
tags: [实体, 工具]              # 必填:中文页面类型标签 + 可选状态标签
aliases: [OMO, 公开市场操作]     # 可选:别名(跨研报去重靠它)
---
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `title` | 是 | 页面标题(= slug = 文件名) |
| `type` | 是 | 节点类型:`entity` / `concept` / `event` / `analysis` / `source` |
| `subtype` | entity 必填 | `institution` / `instrument` / `indicator`(仅 `type: entity`) |
| `created` | 是 | 创建日期 `YYYY-MM-DD` |
| `updated` | 是 | 最后更新日期(每次修改必须更新) |
| `sources` | 是 | 引用的 source 页 slug 列表(source 类型填 `[]`) |
| `confidence` | 是 | 置信度:`high` / `medium` / `low` / `contested` |
| `tags` | 是 | Obsidian 标签列表(中文类型标签 + 可选状态标签) |
| `aliases` | 否 | 别名列表,**跨研报去重的主力**(OMO=7天逆回购、MDS=买断式逆回购、"重启/恢复"国债买卖) |

### 时间档字段(v2 核心:不同时间档,不同字段)

frontmatter 按节点的**时间档**带不同字段。六档时间模型见 `_ontology.md` §4,这里只列对应到 frontmatter 的字段。

**实体的本质归属边 / 状态(T1 状态 / T3 近永久关系)** —— 在 `relations[]` 条目上带时态:

```yaml
relations:
  - {target: 中国人民银行, type: operated_by, valid_from: 1900-01-01, is_current: true}
```

| 字段 | 用在 | 说明 |
|------|------|------|
| `valid_from` | relations 条目 / 状态 | 这条关系/状态**在世界上何时开始为真**(valid-time) |
| `valid_to` | relations 条目 / 状态 | 何时失效;近永久边留空或 `9999-12-31` |
| `is_current` | relations 条目 / 状态 | 当前是否仍成立;退役时改 `false` |

> **数值绝不进 frontmatter**(T0 观测值进 `data.db data_points`)。frontmatter 里的"状态"只承载**文本命题**(如"当前政策利率=7天逆回购"),不承载数字。状态变化主要落 `data.db facts` 拉链表,页面顶部用 callout 标注退役(见下方"退役")。

**机制(概念,T2 耐用逻辑)** —— 带耐用度与可证伪条件:

```yaml
durability: high                # T2 耐用度:high(定义性) | medium(因果传导) | low(经验规律)
preconditions: [短端利率由央行主导]        # 这条逻辑成立的前提
falsifiable_by: [若放弃走廊调控转向单一政策利率]  # 什么情况下它会被证伪/失效
```

**事件(T4)** —— 带日期、施动者,以及它退役/设定了什么:

```yaml
event_date: 2025-03-01          # 事件发生日期
actor: 中国人民银行             # 施动者(机构 slug)
retires: [MLF是政策利率锚]       # 这个事件让哪些旧命题失效
sets: {政策利率锚: 7天逆回购}    # 这个事件把哪个状态设成了什么
```

### tags 规则(Obsidian 搜索过滤必需)

`tags` 必须包含页面类型标签,可追加状态标签。**中文 wiki 用中文标签**:

```yaml
tags:
  - 实体                       # 必填:节点类型
  - 工具                       # 实体的 subtype 也加一个标签(机构/工具/指标)
  - 争议                       # 可选:confidence=contested 时加
  - 已退役                     # 可选:状态被事件退役时加
```

类型标签对照:

| type | subtype | 中文标签 |
|------|---------|---------|
| entity | institution | `实体` `机构` |
| entity | instrument | `实体` `工具` |
| entity | indicator | `实体` `指标` |
| concept | — | `概念` `机制` |
| event | — | `事件` |
| analysis | — | `分析` |
| source | — | `来源` |

状态标签:`争议`(contested)、`低置信`(low)、`已退役`(状态被事件封口)。

source 类型页面额外加来源等级标签:`一手来源` / `权威二手` / `二手` / `转述` / `推断`。

来源等级对照:

| source_type | 中文标签 |
|-------------|---------|
| 一手 | `一手来源` |
| 二手·权威 | `权威二手` |
| 二手 | `二手` |
| 转述 | `转述` |
| 推断 | `推断` |

这些标签用于 Obsidian 搜索过滤(如搜索栏输入 `tag:#争议` 快速定位有争议的页面)。图谱着色不依赖 tags —— 靠 `path:` 子目录规则区分页面类型,靠 `[confidence:contested]` Properties 查询高亮风险节点。

### aliases 规则

aliases 是**跨研报去重的主力**:不同研报对同一物用不同叫法,全部塞进 `aliases`,ingest 时先查 aliases 命中已有页就不重复建页。

标题含括号说明时,也拆出短名和括号内容作为别名:

```yaml
title: 买断式逆回购
aliases:
  - MDS
  - 买断式逆回购操作
title: 国债买卖
aliases:
  - 重启国债买卖
  - 恢复国债买卖
```

---

## 结构化数据 → data.db(数值绝不进 frontmatter)

**所有可量化、可查证、可对比的数据写入 `data.db`(SQLite),不放在 frontmatter,也不放正文表格里。**

data.db 不止存数值,而是按时间档分表(完整 schema 见 `_ontology.md` §7):

| 表 | 存什么 | 时间档 | 关键列 |
|----|--------|--------|--------|
| `data_points` | 数值观测(逐期时序,值是数字) | T0 | `value REAL, unit, period, recorded_at, source_slug, supersedes_id` |
| `facts` | 状态/逻辑命题(object 是文本/slug,非数值) | T1 状态 / T2 逻辑 | `predicate, object_text, object_slug, valid_from, valid_to, is_current, recorded_at, caused_by_event, supersedes_id` |
| `events` | 事件(切换的盖章者,append-only) | T4 | `slug, event_date, actor_slug, description, source_slug, recorded_at` |
| `relations` | 关系边(带时态) | T3 | `from_slug, to_slug, type, bound_role, valid_from, valid_to, recorded_at, retract_event_slug` |

**T0 数值字段规范**(`data_points` 表约束):

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `page_slug` | 是 | TEXT | 所属页面 slug |
| `field` | 是 | TEXT | 数据维度名(如"7天逆回购利率") |
| `value` | 是 | REAL | 数值 |
| `unit` | 是 | TEXT | 单位(%、BP、亿元、万亿…) |
| `period` | 是 | TEXT | 数据时点(如 `2026-05`、`2025-Q1`)= valid-time |
| `recorded_at` | 是 | TEXT | 哪份研报哪天记的 = transaction-time |
| `source_slug` | 是 | TEXT | source 页 slug(每个数字都必须有出处) |
| `supersedes_id` | 否 | INTEGER | 同 period 被新研报修正时指向旧行 |
| `confidence` | 否 | TEXT | 该数据点置信度 |
| `scope` | 否 | TEXT | 统计口径说明 |

**关键裁决**:
- `7天逆回购利率=1.40%` → **T0**,进 `data_points`,值是数字,逐月一条。
- `当前政策利率=7天逆回购` → **T1 状态**,进 `facts`,object 是文本,靠事件切换。
- 两种物,记录方式必须不同。

Agent ingest 时调用 `store.py` 的 `WikiStore` 接口写各表(`upsert_data` 写 T0,状态/关系变化走退役协议)。

---

## 受控关系词表(关系是一等公民,但仍是边)

`relations[].type` **不允许自由文本**,必须从下表选。每条边有 `source→target` 类型约束,`lint` 拒绝越界边。关系**双写**:页面 `frontmatter.relations[]`(给 Obsidian 连边)+ `data.db relations 表`(给查询/校验),两者一致。

| type | source → target | 含义 | 例 |
|---|---|---|---|
| `operated_by` | 工具 → 机构 | 工具由谁运行 | 7天逆回购 → 中国人民银行 |
| `transmits_to` | 指标/工具 → 指标 | 利率传导(有向) | 7天逆回购利率 → DR007 |
| `bounds` | 指标 → 机制(边属性 `bound_role=upper/lower/center`) | 构成走廊上/下限/中枢 | SLF利率 →(upper) 利率走廊 |
| `classified_as` | 工具 → 分类标签 | 贴分类维度(可多维并列,标签不建页) | 7天逆回购 → 价格型 |
| `implements` | 机构 → 机制 | 机构实施某机制 | 中国人民银行 → 利率走廊 |
| `instance_of` | 工具/指标 → 机制 | 个体属于某类 | MLF → 货币政策工具箱 |
| `part_of` | 机制 → 机制 | 机制内部包含 | 利率走廊 → 利率传导机制 |
| `created_by` / `changed_by` | 工具/机制 → 事件 | 个体的创设/变更挂到事件 | MLF利率锚地位 →(changed_by) 2025-03-MLF改革 |
| `references` | 分析/来源 → 任意 | 引用(只溯源,不进语义图) | 央行工具箱全景 → 7天逆回购 |

**relations 写法规范**:

```yaml
relations:
  - {target: 中国人民银行, type: operated_by}
  - {target: 价格型, type: classified_as}
  - {target: 利率走廊, type: bounds, bound_role: center}   # bounds 必带 bound_role
  - {target: 7天逆回购, type: operated_by, valid_from: 1900-01-01, is_current: true}  # 可带时态
```

- `target` 填 slug(不加路径前缀)
- `type` 必须从上表选,越界由 lint 拒绝
- `bounds` 边必带 `bound_role`(`upper` / `lower` / `center`)
- T3 近永久边可带 `valid_from` / `valid_to` / `is_current`;退役边不删,封 `valid_to` + 写 `retract_event_slug`

---

## source 类型页面的额外字段

```yaml
---
title: 2026-05-25-某券商固收报告
type: source
created: 2026-06-07
updated: 2026-06-07
sources: []
confidence: high
source_type: 二手·权威          # 一手 | 二手·权威 | 二手 | 转述 | 推断 | 口述
source_origin: 某券商固收团队
source_date: 2026-05-25         # 原始材料的日期(不是 ingest 日期)
source_url: ""                  # 来源 URL(如有)
tags: [来源, 权威二手]
---
```

---

## 各类型 frontmatter 模板

### 实体·机构

```yaml
---
title: 中国人民银行
type: entity
subtype: institution
created: 2026-06-07
updated: 2026-06-07
aliases: [央行, PBoC, 人民银行]
sources: [2026-05-25-某券商固收报告]
confidence: high
relations:
  - {target: 利率走廊, type: implements}
tags: [实体, 机构]
---
```

### 实体·工具

```yaml
---
title: 7天逆回购
type: entity
subtype: instrument
created: 2026-06-07
updated: 2026-06-07
aliases: [OMO, 公开市场操作, 7天逆回购操作]
sources: [2026-05-25-某券商固收报告]
confidence: high
relations:
  - {target: 中国人民银行, type: operated_by, valid_from: 1900-01-01, is_current: true}
  - {target: 价格型, type: classified_as}
  - {target: 货币政策工具箱, type: instance_of}
tags: [实体, 工具]
---
```

### 实体·指标

```yaml
---
title: 7天逆回购利率
type: entity
subtype: indicator
created: 2026-06-07
updated: 2026-06-07
aliases: [OMO利率, 7天逆回购操作利率]
sources: [2026-05-25-某券商固收报告]
confidence: high
relations:
  - {target: DR007, type: transmits_to}
  - {target: 利率走廊, type: bounds, bound_role: center}
tags: [实体, 指标]
# 注意:具体数值(如 1.40%)不写这里,进 data.db data_points
---
```

### 概念·机制

```yaml
---
title: 利率走廊
type: concept
created: 2026-06-07
updated: 2026-06-07
sources: [2026-05-25-某券商固收报告]
confidence: high
durability: medium              # T2 耐用度:high / medium / low
preconditions: [短端利率由央行主导]
falsifiable_by: [若放弃走廊调控转向单一政策利率]
relations:
  - {target: SLF利率, type: bounds, bound_role: upper}
  - {target: 超额准备金利率, type: bounds, bound_role: lower}
  - {target: 7天逆回购利率, type: bounds, bound_role: center}
  - {target: 利率传导机制, type: part_of}
tags: [概念, 机制]
---
```

### 事件

```yaml
---
title: 2025-03 MLF美式招标改革
type: event
event_date: 2025-03-01
actor: 中国人民银行
created: 2026-06-07
updated: 2026-06-07
sources: [2026-05-25-某券商固收报告]
confidence: high
retires: [MLF是政策利率锚]
sets: {政策利率锚: 7天逆回购}
tags: [事件]
---
```

### 来源

```yaml
---
title: 2026-05-25-某券商固收报告
type: source
created: 2026-06-07
updated: 2026-06-07
sources: []
confidence: high
source_type: 二手·权威
source_origin: 某券商固收团队
source_date: 2026-05-25
source_url: ""
tags: [来源, 权威二手]
---
```

### 分析

```yaml
---
title: 央行工具箱全景
type: analysis
created: 2026-06-07
updated: 2026-06-07
sources: [2026-05-25-某券商固收报告]
confidence: medium
relations:
  - {target: 7天逆回购, type: references}
  - {target: MLF, type: references}
  - {target: 货币政策工具箱, type: references}
tags: [分析]
# 研究课题降级为分析页;它是派生视图,删了不影响本体
---
```

---

## 正文约定

**正文只写叙事分析和上下文解读,不写数据表格。**

```markdown
# 7天逆回购

2025-03 起,7天逆回购成为央行唯一的政策利率锚(此前为 [[MLF]]),
通过 [[7天逆回购利率]] 向 [[DR007]] 传导,构成 [[利率走廊]] 的中枢。
工具属性上它是价格型,详见 [[货币政策工具箱]]。

>  政策范式 2014→2025 从数量型漂移到价格型,无单一切换日,见 [[利率传导机制]]。
```

**正文规则**:
- 用 `[[slug]]` 或 `[[slug|显示名]]` 做页面链接
- 提到数据时引述结论,**不重复 frontmatter / data.db 中的具体数值**(避免不一致)
- 可以用 `> ` callout 标注重要警告(如口径差异、退役)
- 分析性内容是正文的核心价值 —— 这是 YAML 无法承载的部分

### 退役标注(状态/机制被事件推翻时)

T1 状态或 T2 机制被事件封口后,**页面正文一字不删**(它当年为真,是过期不是错),只在顶部加 callout 并改 frontmatter:

```markdown
> [!warning] 已退役(2025-03 起失效):MLF 不再是政策利率锚,
> 7天逆回购成为唯一政策利率锚。见 [[2025-03-MLF改革]]。
```

```yaml
is_current: false
valid_to: 2025-03
tags: [概念, 机制, 已退役]
```

退役全流程(写事件页 → 给旧 facts 行盖 valid 章 → 连 `caused_by_event` 指针 → 插继任新行 → 页面历史化)见 `_ontology.md` §6。**核心铁律:永不 DELETE,旧行封 `valid_to` + 插新行,变化必有 T4 事件盖章,valid-time 与 transaction-time 分开记。**

### 页面末尾:`## 关联`(推荐)

把 frontmatter `relations` 用自然语言显式化,让 Agent 读正文时就获得结构上下文,不需额外解析 YAML。

```markdown
## 关联

- **运行机构**:[[中国人民银行]](operated_by)
- **传导至**:[[DR007]](transmits_to)
- **构成走廊中枢**:[[利率走廊]](bounds · center)
- **分类**:价格型(classified_as)
```

### 数据密集页面:`## 关键数据`(推荐)

当页面在 data.db 中有对应数据点时,加一个轻量段落告知 Agent "这里有结构化数据可查"。**不是数据库回显,而是数据锚点;具体数值以 data.db 为准。**

```markdown
## 关键数据

| 指标 | 时点 | 来源 |
|------|------|------|
| 7天逆回购利率 | 2026-05 | [[2026-05-25-某券商固收报告]] |
| 与上期变动(BP) | 2026-05 | [[2026-05-25-某券商固收报告]] |

完整数值、历史变更与双时态记录见 `data.db`。
```

---

## 文件命名与 Slug 统一(关键)

**一个页面只有一个 canonical slug,所有层必须使用同一个。单一中文 slug = 文件名 = `[[wikilink]]` = `data.db` 主键。**

| 层 | 用同一个 slug | 反例(split-brain) |
|----|-------------|-------------------|
| 文件名 | `7天逆回购.md` | 文件名中文,DB 里 `reverse-repo-7d` |
| frontmatter `sources` | `["2026-05-25-某券商固收报告"]` | 写英文 slug 而文件名中文 |
| `data.db` `page_slug` | `7天逆回购` | 英文 canonical slug |
| `data.db` `relations` | `from: 7天逆回购` | 英文 slug |
| `[[wikilink]]` | `[[7天逆回购]]` | 写英文 slug |

**规则**:
- slug = 文件名去 `.md` = `data.db` 中的 `page_slug` = `relations` 中的 `from_slug`/`to_slug` = `[[wikilink]]` 目标
- **中文 wiki 用中文 slug**,Obsidian 友好、人类可读
- **不另起 PascalCase / 英文 id** —— 会造出第二套命名,和 Obsidian 的中文文件名链接打架。跨研报的别名归一靠 `aliases:` 字段,不靠英文 id
- source 页面加日期前缀:`2026-05-25-某券商固收报告.md`(连字符分隔日期)
- 事件页用 `日期-事件名` 命名:`2025-03-MLF改革.md`
- **ingest 时 Agent 必须用同一个 slug 同时操作文件和 data.db,不允许出现两套命名**

---

## Hub 页面格式

Hub 页面以**领域中文名**命名(如 `宏观.md`),不用 `index.md`。

**命名原因**:Obsidian 图谱中节点显示文件名,多个 wiki 都用 `index` 无法区分。用领域中文名作为 hub 文件名,图谱中心节点即显示为可辨识的领域名。

Hub 是 Agent 进入 recall 时读的**第一个文件**,需要同时提供导航和结构感。

```markdown
# 宏观 Wiki Index

> {N} pages | Last updated: {日期} | Domain: macro
>  Contested: [[页面A]]、[[页面B]]
>  已退役: [[MLF是政策利率锚]](2025-03 起)

## 知识结构

核心拓扑(只展示 hub 节点和关键边,不 dump 全图):

中国人民银行 ── implements ──→ 利率走廊
  ├── 7天逆回购 ── operated_by ──→ 中国人民银行
  ├── 7天逆回购利率 ── bounds(center) ──→ 利率走廊
  ├── SLF利率 ── bounds(upper) ──→ 利率走廊
  └── 货币政策工具箱 ←── instance_of ── MLF / SLF / 降准 …

## 机构 ({N})
- [[中国人民银行]] — 货币政策决策与执行主体

## 工具 ({N})
- [[7天逆回购]] — 价格型,当前政策利率锚
- [[MLF]] — 数量型  锚地位已退役(2025-03)

## 指标 ({N})
- [[7天逆回购利率]] — 政策利率序列
- [[DR007]] — 银行间质押式回购加权利率

## 机制 ({N})
- [[利率走廊]] — 上下限调控框架
- [[利率传导机制]] — 政策利率向市场利率的传导链

## 事件 ({N})
- [[2025-03-MLF改革]] — MLF 美式招标改革,政策锚切换

## 分析 ({N})
- [[央行工具箱全景]] — 工具分类与传导全景

## 来源 ({N})
- [[2026-05-25-某券商固收报告]] — 某券商固收团队报告
```

**hub 页面规则**:
- 顶部 header 含 contested 与已退役页面列表(如有),Agent 进入 recall 第一眼就知道哪些知识不可靠/已过期
- `## 知识结构` 用文本树展示 5-8 个 hub 节点 + 关键关系边 + 状态标记,让 Agent 一读就建立全局结构感
- 分类清单按节点类型分组(机构/工具/指标/机制/事件/分析/来源),每条目一行 `[[slug]] — 一句话描述`

---

## log.md 格式

```markdown
# 宏观 Wiki Log

## 2026-06-07 14:30 — ingest
- Source: 2026-05-25-某券商固收报告
- Created: 机构/中国人民银行, 工具/7天逆回购, 指标/7天逆回购利率, 机制/利率走廊
- Updated: (无)
- Conflicts: (无)

## 2026-06-07 15:00 — ingest(退役协议)
- Source: 2026-05-25-某券商固收报告
- Created: 事件/2025-03-MLF改革
- Retired: facts「MLF是政策利率锚」封 valid_to=2025-03, is_current=0, caused_by_event=2025-03-MLF改革
- Set: facts「政策利率锚=7天逆回购」valid_from=2025-03, is_current=1
- Conflicts: (无,旧行保留未删)
```

---

## Validation Rules

| 规则 | 要求 |
|------|------|
| frontmatter 完整 | `title` `type` `created` `updated` `sources` `confidence` 六字段必须存在 |
| type 值合法 | `entity` / `concept` / `event` / `analysis` / `source` |
| subtype 合法 | `type: entity` 必须有 `subtype ∈ {institution, instrument, indicator}` |
| 事件字段完整 | `type: event` 必须有 `event_date` + `actor` |
| 机制时间档字段 | `type: concept` 建议有 `durability`(T2 耐用度) |
| 数值不在 frontmatter | frontmatter 不出现具体数值,数值进 `data.db data_points` |
| data 字段规范 | 每个 T0 数据点必须有 `value` `unit` `period` `recorded_at` `source_slug` |
| 退役 append-only | T1/T2 任何变化:旧行封 `valid_to` + 插新行,永不 DELETE;变化必有 `caused_by_event` |
| relations 受控 | 每条关系有 `target` + `type`,`type` 必属受控词表;`bounds` 必带 `bound_role` |
| sources 非空 | 除 source 类型外,`sources` 至少一个 slug |
| 日期格式 | `YYYY-MM-DD` |
| slug 与文件名一致 | 文件名(去 `.md`)= slug = `page_slug` = `[[wikilink]]` 目标;无英文 id 副本 |

---

## 置信度更新规则

| 事件 | 置信度变化 |
|------|-----------|
| 新 source 印证已有数据(data 一致) | → `high` |
| 新 source 更新已有 T0 数据(更新时点/更权威来源) | upsert 新行,旧行靠 `recorded_at` / `supersedes_id` 保留 |
| 新 source 与已有数据矛盾且无法判断 | 该字段 confidence → `contested` |
| T1/T2 状态被事件推翻 | 走退役协议(封 `valid_to`+插新行+`caused_by_event`),不改置信度,改 `is_current` |
| lint 发现 data 中有无 source 的字段 | → `low` |
| 页面 6 个月未被 ingest 触及 | lint 建议标注"待验证" |
