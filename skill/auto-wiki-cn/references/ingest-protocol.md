# Ingest 协议

> Ingest 不是追加文件,是**编译**——先查 canonical、读旧、比新、按退役协议改旧。
> 本文是**领域无关的引擎规范**;权威契约是各领域的 `_ontology.md`(例:`wiki/macro/_ontology.md`),它是该领域的具体实例,定义了节点类型判据、受控关系词表、6 档时间模型与表结构。**本协议的任何一步遇到判据/词表/时间档/表名,以目标领域的 `_ontology.md` 为准。** 下文举例用 macro 领域的对象,但流程对任何领域通用。

---

## 核心心智(开工前先记住)

1. **节点 / 数据 / 边 三分**:
   - **数值绝不是节点** —— `7天逆回购利率=1.40%` 不建页,进 `data.db`。图谱里只有"7天逆回购利率"这条序列,没有"1.40%"这个点。
   - **关系是边不是节点** —— "央行运行7天逆回购"是一条 `operated_by` 边,不是一个叫"运行"的页。
   - **分类标签不是节点** —— "数量型/价格型"等是贴在节点上的多维标签(`classified_as` 边),不建页。
2. **wiki 按领域(domain)组织,不按研究课题(topic)** —— 落页落在 `wiki/{domain}/{类型子目录}/`(机构/工具/指标/机制/事件/分析/来源)。一篇研报本身是 `分析/` 下的**一页**,不是一个目录;它的研究课题是派生视图,删了不动本体。
3. **编译是单向的** —— `Inbox(人写散文)→ ingest → wiki(本体产物)`。严谨用在已结晶的知识(wiki),不用在正在结晶的知识(Inbox)。
4. **退役不删除** —— T1/T2/T3 的任何变化都是"旧行封 `valid_to` + 插新行",永不 DELETE,且必有一个 T4 事件盖章(见下方退役六步)。

---

## 主流程

```
1. 读取源文件 → 写 来源/{date}-{slug}.md（不可变的忠实摘要）
   ├─ 提取关键信息：节点候选、关系、数值、结论、时间、事件
   └─ frontmatter 记 source_type / source_origin / source_date

2. 逐项抽名词 → 先查 canonical（含 aliases）是否已存在 关键改动
   ├─ 读目标领域 hub（{领域中文名}.md，例 宏观.md）拿全部页面列表
   ├─ 对每个候选名，比对现有页面的「文件名 slug」+「aliases 字段」
   │   （跨研报同物异名靠 aliases 收敛：OMO=7天逆回购、MDS=买断式逆回购、"重启/恢复"国债买卖）
   └─ 命中 → 走分支 A（已存在）；未命中 → 走分支 B（不存在）

   ┌─ A) 已存在 → 合并 / 按退役协议更新
   │   ├─ 该页 sources 列表追加新 source slug
   │   ├─ 新值/新状态：按第 4 步给它定时间档 → 写对应表
   │   │   · T0 数值 → data_points（同 period 纠错才覆盖，否则新增一行）
   │   │   · T1/T2/T3 变化 → 不原地改，走「退役不删除六步」
   │   └─ log: "merged/retired: {page}"
   │
   └─ B) 不存在 → 走目标领域 _ontology.md 的「分类决策树」定类型 → 落对应子目录建页

3. 给每条知识定 6 档时间档 → 写对应表 关键改动
   （档位与判据见 _ontology.md §4；表结构见 §7）
   ├─ T0 观测值（某指标某时点的一次测量，值是数字）        → data_points
   ├─ T1 状态/制度态（一段时间恒为真、被事件一刀切换的命题）→ facts（拉链表）
   ├─ T2 耐用逻辑（跨周期因果链/定义，可证伪）            → facts（拉链表）+ 机制页正文/耐用度字段
   ├─ T3 实体/近永久关系（客观存在物及本质归属）          → 实体页 + relations（带时态）
   ├─ T4 事件（有日期+施动者、发生即固定）                → events（只增不改）+ 事件页
   └─ T5 类型公理（约束别的知识长什么样）                  → 不写记录，写进 _ontology.md / DB CHECK

4. 补 / 退役受控关系边
   ├─ type 必须从目标领域受控词表选（macro：operated_by/implements/transmits_to/
   │   bounds/classified_as/instance_of/part_of/created_by/changed_by/references）
   ├─ 双写：页面 frontmatter.relations[]（给 Obsidian 连边）+ data.db relations 表
   └─ 关系撤销 = 给 relations 行写 valid_to + retract_event_slug，不删行

5. 这篇研报落 分析/ + 更新 hub（{领域中文名}.md） + 追加 log.md
   ├─ 研报本身建 分析/{date}-{slug}.md（type: analysis），用 references 边溯源到它引用的节点
   ├─ hub：新页面加入对应分组，更新计数与 Last updated，不动已有条目描述
   └─ log.md append-only

6. 跑 schema 校验（references/schema.py + data.db 表约束）

7. 刷新位置编码 + 报告（图谱校准布局）
   ├─ python references/position_encoding.py wiki/{domain}   → 重算 _positions.json
   └─ python references/schema.py --report wiki/{domain}     → 重建 _report.html
```

---

## 关键原则

**1. 先查 canonical，改旧优先于建新**

抽到一个名词,**第一件事是查它是否已经是 canonical 页(比对文件名 slug + aliases),而不是直接建页**。命中已有 `工具/7天逆回购.md`、新研报也提到它(哪怕用的是 "OMO"/"公开市场操作" 这种别名)→ 在已有页上合并,**绝不**新建 `工具/7天逆回购-2.md`。新发现的别名追加进该页 `aliases:` 字段,让下一次 ingest 也能命中。

**2. 单一中文 slug,不造第二套命名**

**文件名(去 .md)= `[[wikilink]]` 目标 = `data.db` 主键 = relations 两端 slug**,全系统只有这一套中文 slug。**不**另起 PascalCase 英文 id(那会和 Obsidian 的中文文件名链接打架,造出第二套命名)。跨研报去重只靠 `aliases:`,不靠英文 id。

**3. 数值绝不进页,进 data.db**

页面正文写叙事分析,**引述数据结论但不重复具体数值**(如写"政策利率维持低位",不写"=1.40%")。具体数字进 `data_points`。数据密集页可加 `## 关键数据` 段落,列该页在 data.db 中的数据点摘要(摘要,非真值源)。

**4. 退役不删除(T1/T2/T3 变化时走六步)**

过时的 T1/T2 结论**不删、不原地改**——它当年是 high、不是错的,是过期的。任何变化都 append-only,原始记录一字节不丢。详见下方「退役不删除六步协议」。
（**唯一例外**:T0 同 `period` 的纯纠错可覆盖,但要保留两行 + 用 `recorded_at` 区分,不塞 history。）

**5. 双时态,两条轴绝不混**

每条断言记两条时间轴:`valid_from/valid_to`(世界上何时为真,valid-time)+ `recorded_at`(我哪份研报记的,transaction-time)。
- **`valid_from` 变 = 世界变了**(制度演进,如政策锚切换)→ 走退役协议、盖事件章。
- **只动 `recorded_at` = 我自己勘误**(同一事实换了来源/订正录入)→ 不算世界变化,不盖事件章。
这俩绝不能混。

**6. 一切"当前态"的改变都要有 T4 事件盖章**

任何 T1/T2 当前态的翻转,都要追溯到一个 T4 事件页(`caused_by_event`)。没有事件就先建事件(渐变迁移取代理事件打桩,见 _ontology.md §9)。

**7. 一次 ingest 触及多个页面是正常的**

一篇研报可能涉及 5-10 个节点。一次 ingest 更新 8 个页面是正常的,log 里完整记录。

**8. Source 页面不可变**

`来源/` 下的摘要页创建后不再修改(除非摘要本身有错)。它是原始材料的忠实记录,其他页通过 `sources` frontmatter 字段引用它。

---

## 退役不删除六步协议 —— 旧逻辑被 T4 事件推翻时

> **标准范例**:`MLF利率=政策利率锚`(T1 状态)被 `2025-03 MLF美式招标改革`(T4 事件)推翻。全程 append-only,原始记录一字节不丢。换领域时把对象替换成你的领域即可。

1. **先写事件页** `事件/2025-03-MLF改革.md`(`type: event`),frontmatter 声明 `event_date`、`actor`、`retires: [[MLF是政策利率锚]]`、`sets: {政策利率锚: 7天逆回购}`。同步 INSERT `events` 表。
2. **给旧 facts 行盖 valid 章**(唯一允许的原地写,只动一列):`valid_to: 9999 → 2025-03`、`is_current: 0`。旧结论**一字不改**。
3. **连因果指针**:旧 facts 行补 `caused_by_event → [[2025-03-MLF改革]]`。
4. **插继任新行**:`政策利率锚=7天逆回购, valid_from=2025-03, is_current=1, supersedes_id=旧行id`。
5. **页面层历史化**:相关机制/实体页正文**不删**,顶部加 callout:
   `> [!warning] 已退役(2025-03起失效):MLF 不再是政策利率锚,7天逆回购成为唯一政策利率锚。见 [[2025-03-MLF改革]]`。frontmatter 改 `is_current: false`、`valid_to: 2025-03`。
6. **关系层(如涉及 T3 边变化)**:对被推翻的 relations 行写 `valid_to` + `retract_event_slug`,插新边,不删旧边。

**效果**:查"当前锚"→7天逆回购;查"2024 年我以为锚是啥"→MLF;问"为啥变"→沿 `caused_by_event` 跳到事件页。曾为真、何时起为假、被谁改 —— 三件事全可回溯。

---

## 同来源、同级、无法判优劣时 → 冲突并列

当新旧说法矛盾、但来源同级且无更新日期、无法判断谁对(典型:统计口径不同)时,**不调和、不编折中**。在页面里并列两种说法、各标来源,frontmatter `confidence: contested`,log 记 `conflict`。

```markdown
## 市场份额

> [!warning] contested — 两个来源数据不一致

- 据 [[2026-04-06-policy-doc]]：某机构市场份额约 15%
- 据 [[2025-annual-industry-report]]：某机构市场份额约 12%

差异可能来自统计口径不同（含/不含某分项）。
```

> 注意区分:**有更新日期或更权威来源** → 这是世界演进或勘误,走退役协议(不是冲突);**同级无法判优劣** → 才是 contested 并列。

---

## Worked Example: 完整 Ingest 流程

> 用 macro 领域举例,实际执行时换成用户的目标领域与其 `_ontology.md`。

**场景**:用户 ingest 一篇固收研报到 `wiki/macro/`。wiki 中已有部分页面。

### Step 1 — 读源文件,生成 source 摘要页

新建 `来源/2026-05-25-某券商固收报告.md`:

```yaml
---
title: 某券商固收报告（2026-05-25）
type: source
created: 2026-05-25
updated: 2026-05-25
sources: []
confidence: high
source_type: 二手·券商
source_origin: 某券商研究所
source_date: 2026-05-25
---
```

正文写原文关键信息的忠实摘要。

### Step 2 — 抽名词,先查 canonical(含 aliases)

研报提到 "OMO 利率维持 1.40%"、"MLF 不再是政策利率锚"、"重启国债买卖"。

读 hub `宏观.md` 拿页面列表,逐个比对 slug + aliases:

- "OMO" → 命中 `指标/7天逆回购利率.md`(其 `aliases:` 含 OMO 利率)→ **分支 A 已存在**。
- "MLF 政策利率锚" → 命中机制页里的 T1 状态 `MLF是政策利率锚` → **分支 A,且是状态被推翻 → 退役协议**。
- "国债买卖" → 命中 `工具/国债买卖.md`(aliases 含 "重启国债买卖")→ **分支 A**。

查 data.db 该指标当前值:

```python
store.query_data(page_slug="7天逆回购利率")
# → [{ field:"利率", value:1.40, unit:"%", period:"2026-05",
#      recorded_at:"2026-04-...", source_slug:"..." }]
```

### Step 3 — 给每条知识定时间档,写对应表

- **`7天逆回购利率=1.40%`** → **T0 观测值**。新 period(2026-05)→ `data_points` 新增一行,带 `recorded_at`、`source_slug`;不覆盖旧 period。

  ```python
  store.upsert_data(
      page_slug="7天逆回购利率", field="利率", value=1.40, unit="%",
      period="2026-05", recorded_at="2026-05-25",
      source_slug="2026-05-25-某券商固收报告")
  ```

- **`MLF是政策利率锚` 被推翻** → 这是 **T1 状态被 T4 事件切换** → 走「退役不删除六步」:
  1. 建 `事件/2025-03-MLF改革.md`(`type: event`, `retires`, `sets`)+ INSERT `events`。
  2. 旧 facts 行盖章:`valid_to=2025-03, is_current=0`(`object_text` 一字不改)。
  3. 旧行补 `caused_by_event = 2025-03-MLF改革`。
  4. 插新行:`政策利率锚=7天逆回购, valid_from=2025-03, is_current=1, supersedes_id=旧行id`。
  5. 机制页顶部加 `[!warning]` callout,frontmatter `is_current: false`。

  ```python
  store.insert_event(slug="2025-03-MLF改革", event_date="2025-03-01",
                     actor_slug="中国人民银行",
                     description="MLF 改美式招标，退出政策利率锚",
                     source_slug="2026-05-25-某券商固收报告")
  store.retire_fact(old_fact_id, valid_to="2025-03",
                    caused_by_event="2025-03-MLF改革")
  store.insert_fact(page_slug="货币政策工具箱", predicate="政策利率锚",
                    object_slug="7天逆回购", valid_from="2025-03",
                    is_current=1, supersedes_id=old_fact_id,
                    caused_by_event="2025-03-MLF改革",
                    source_slug="2026-05-25-某券商固收报告")
  ```

### Step 4 — 受控关系边(双写)

```python
# 工具 → 机构（T3，近永久边，valid_to 留 9999）
store.add_relation("国债买卖", "中国人民银行", "operated_by")
# 工具 → 分类标签（不建页，只是边）
store.add_relation("7天逆回购", "价格型", "classified_as")
```

页面 frontmatter 同步写 `relations:`,两侧一致。

### Step 5 — 落分析页 + 更新 hub + log

研报本身建 `分析/2026-05-25-固收观点.md`(`type: analysis`),用 `references` 边溯源到它引用的节点(不进语义图)。更新 `宏观.md` hub 分组与计数。

`log.md` 追加:

```
## 2026-05-25 14:30 — ingest
- Source: 来源/2026-05-25-某券商固收报告
- Merged: 指标/7天逆回购利率（data_points +1 行，period 2026-05，值 1.40%）
- Retired: 货币政策工具箱「政策利率锚」MLF→7天逆回购（事件 2025-03-MLF改革）
- Created: 事件/2025-03-MLF改革
- Relations: 国债买卖→中国人民银行 operated_by
- Conflicts: none
```

### Step 6 — schema 校验

跑 `references/schema.py`(frontmatter 校验)+ data.db 表约束(`pages.type` 含 `event`、facts 拉链列完整、relations 时态列完整)。

### Step 7 — 位置编码刷新（图谱校准布局）

节点/关系有任何增删改后，坐标已过期，必须重算：

```bash
python references/position_encoding.py wiki/{domain}   # y=本体层级, x=拉普拉斯谱坐标, pe=sin/cos 向量 → _positions.json
python references/schema.py --report wiki/{domain}     # _report.html 自动启用校准布局
```

`_positions.json` 是派生产物（如 `_report.html`），可随时重算，删了不影响本体；勿手改。

---

## frontmatter 速查(写页时对照)

> 完整模板见目标领域 `_ontology.md` 附录。下面是 ingest 时最常落的几类。

```yaml
# 实体（机构/工具/指标，subtype 三选一）
type: entity
subtype: instrument        # institution | instrument | indicator
aliases: [OMO, 公开市场操作]   # 跨研报去重靠这里，不造英文 id
sources: [2026-05-25-某券商固收报告]
relations:
  - {target: 中国人民银行, type: operated_by}
  - {target: 价格型, type: classified_as}

# 概念·机制（带 T2 耐用度与证伪条件）
type: concept
durability: medium          # high/medium/low
preconditions: [短端利率由央行主导]
falsifiable_by: [若放弃走廊调控转向单一政策利率]

# 事件（T4，append-only）
type: event
event_date: 2025-03-01
actor: 中国人民银行
retires: [MLF是政策利率锚]
sets: {政策利率锚: 7天逆回购}
```

---

## From-Lint 流程（deep-dive 管道的 ingest 阶段）

当 ingest 由 deep-dive 管道触发时,输入不是用户提供的源文件,而是 lint Coverage 输出的缺口报告(Gap Report)。

### 与标准 ingest 的区别

| 方面 | 标准 ingest | from-lint ingest |
|------|------------|------------------|
| 输入 | 用户提供的源文件 | Gap Report 中的缺口条目 |
| 来源获取 | 用户已提供 | Agent 通过搜索工具获取 |
| 批量操作 | 通常 1 个源文件 | 可能 N 个缺口,逐个处理 |
| 用户确认 | 不需要(用户已主动提供) | 需要(搜索前确认范围,搜索后确认质量) |

### 流程

```
输入：Gap Report（来自 lint Coverage）

For each confirmed gap:

1. 制定搜索计划
   ├─ page_missing → 搜索该节点（机构/工具/指标/机制）的基本信息
   ├─ concept_missing → 搜索该机制的定义和机理
   ├─ data_missing → 搜索该指标的最新数据（落 T0 / data_points）
   ├─ event_missing → 搜索某切换是否对应一个有日期+施动者的事件（落 T4）
   ├─ single_source → 搜索额外来源以交叉验证
   └─ outdated → 搜索该指标/状态的最新信息（可能触发退役协议）

2. 执行搜索（需要搜索工具——主动模式）
   ├─ 使用 WebSearch / 搜索类 MCP 获取候选来源
   ├─ 搜索工具优先级：领域专业工具 > 通用搜索
   ├─ 按 source-validation.md 分级筛选
   └─ 排除黑名单渠道，取 top 1-3 个可信来源

3. 展示搜索结果，请用户确认
   ├─ 展示每个来源的标题、URL、可信度分级
   ├─ 用户选择：接受 / 跳过 / 替换
   └─ 搜索结果质量不够 → 标注"未能补全"，跳过

4. 对确认的每个来源，执行标准 ingest 主流程
   ├─ 第 1-6 步与普通 ingest 完全一致（含先查 canonical、定时间档、退役协议）
   └─ source 摘要页额外记录 deep-dive 元数据（见 source-validation.md）
```

### 防扩散机制

- 每个 gap 最多搜索 3 次(换关键词)。3 次搜不到可信来源 → 标注"未能补全"。
- 单次 deep-dive 最多处理 10 个 gap(可通过 `--max-gaps` 调整)。
- 搜索到的来源若引入 wiki 中完全不存在的新节点,**不自动建页**——只填已知缺口,不主动扩展 wiki 范围。
- 所有搜索来源的 `confidence` 上限为 medium(除非来源是一手/权威二手)。

### 补全报告

```
## Deep-Dive 补全报告：{domain}
执行时间：{date}

### 已补全：{N} / {total} 个缺口
| # | Gap | Action | Source | Confidence |
|---|-----|--------|--------|------------|
| 1 | page_missing: SLF | 新建 工具/SLF.md | [二手·权威] 央行官网 | medium |
| 2 | single_source: 利率走廊 | 增加 1 个来源 | [二手] 行业研报 | medium |

### 未能补全：{M} 个缺口
| # | Gap | Reason |
|---|-----|--------|
| 3 | data_missing: DR007/最新值 | 搜索 3 次未找到可信来源 |

### 建议
- DR007 最新数据建议用户手动提供或接入数据 MCP（海量行情不进 wiki）。
```
