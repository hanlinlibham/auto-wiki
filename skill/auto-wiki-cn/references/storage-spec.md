# 存储规格

> 本文件是 auto-wiki **引擎**的存储规格,与领域无关。下文一切以 macro 领域举的例子(央行、7天逆回购、利率走廊……)只是某个领域契约 `wiki/{domain}/_ontology.md` 的具体实例;换一个领域,目录骨架与表结构不变,只是节点内容不同。
>
> **权威真相源是各领域的 `_ontology.md`(本体契约)。** 本规格只回答"东西落在磁盘的哪里、用什么结构存";"一条知识是实体/概念/事件/数值/关系中的哪一种、变多快、被推翻怎么办"由契约定义。两者冲突时以契约为准。

---

## Wiki 根目录

所有 wiki 存储在工作目录下的 `wiki/` 目录中。**wiki 按领域(domain)组织,不按研究课题(topic)。** 每个一级子目录 = 一个领域(如宏观、信用、权益策略),而不是一篇研报、一个专题。

```
{项目根目录}/
└── wiki/
    ├── macro/                  # 一个领域一个目录(宏观)
    ├── credit/                 # 信用
    └── equity-strategy/        # 权益策略
```

> **领域 ≠ 研究课题。** "美联储加息周期与大类资产配置""企业年金市场格局"这类**研究课题(topic)降级为 `{domain}/分析/` 下的一页**(派生视图),不再各自开一个顶层目录。一个领域里所有课题共享同一套实体/概念/事件/指标,跨课题去重、互相链接,知识才能积累而不是碎成一堆孤岛。

**位置选择逻辑**(按优先级):
1. 如果当前目录有 `wiki/` → 使用它
2. 如果当前目录有 `.claude/` → 在同级创建 `wiki/`
3. 如果当前目录是 git repo 根 → 在根目录创建 `wiki/`
4. 否则 → 在当前目录创建 `wiki/`

**与 .gitignore 的关系**:`wiki/` **不要**加入 `.gitignore`——它是知识本体,必须出现在 Obsidian 图谱中、并随 vault 一起纳入 git 版本管理。**禁止使用 `.wiki/`(点前缀目录)**:Obsidian 会隐藏以 `.` 开头的目录,dotfolder 永远不进图谱。一律用可见的 `wiki/`。

> 例外:`wiki/.obsidian/`(Obsidian 自身配置)是唯一允许的点目录,它是 Obsidian 约定的配置位置,不影响图谱里的知识节点;其余一切知识内容(实体/概念/事件/分析/来源/`data.db`)必须在可见目录下。

---

## 单个领域 wiki 的目录结构(类型即目录,目录即图谱着色)

每个领域目录内,**按节点类型分子目录**;子目录名直接用中文(= 节点类型 = Obsidian 图谱着色键)。不再用旧版的 `entities/ concepts/ sources/ analyses/` 英文四目录,也不按研究主题分目录。

```
wiki/{domain}/                         # 如 wiki/macro/
├── _ontology.md                       # 本领域的本体契约(人和 Agent 在 ingest/recall 前先读)
├── {领域中文名}.md                     # Hub / MOC,图谱导航中心(如 宏观.md)
├── log.md                             # ingest 操作日志(append-only)
├── data.db                            # 唯一结构化真相源:数值、状态、事件、关系(SQLite,store.py 管理)
├── _report.html                       # 可视化报告(schema.py --report 生成,可选)
│
├── 机构/   …                          # 实体·机构(有专名的行为主体)         图谱色:红(中心)
├── 工具/   …                          # 实体·工具(被某机构创设并运行的政策工具) 图谱色:蓝
├── 指标/   …                          # 实体·指标(可反复取数的命名时间序列)    图谱色:青
├── 机制/   …                          # 概念·机制(必须靠内涵定义才能理解的机理) 图谱色:绿
├── 事件/   …                          # 事件(有日期+施动者,发生过一次就固定)   图谱色:黄
├── 分析/   …                          # 分析(基于以上节点的研究判断/研究课题页) 图谱色:灰
└── 来源/   …                          # 来源(一篇研报/文章原文的承载页)        图谱色:浅灰
```

macro 领域的具体落地示例:

```
wiki/macro/
├── _ontology.md
├── 宏观.md
├── log.md
├── data.db
├── 机构/   中国人民银行.md  美联储.md
├── 工具/   7天逆回购.md  MLF.md  SLF.md  降准.md  国债买卖.md  PSL.md
├── 指标/   7天逆回购利率.md  LPR.md  M2.md  DR007.md  10Y国债收益率.md
├── 机制/   利率走廊.md  利率传导机制.md  货币政策工具箱.md
├── 事件/   2025-03-MLF改革.md  2024-10-买断式逆回购推出.md
├── 分析/   央行工具箱全景.md  美联储加息与大类资产.md
└── 来源/   2026-05-25-某券商固收报告.md
```

### 节点类型 → 子目录映射

引擎认这 7 类节点,每类一个子目录。具体哪个名词落哪一类,由契约的"分类决策树"裁定;此处只给映射,不重述判据。

| 节点类型 | 子目录 | 一句话(判据细则见契约 §1) | 图谱色 | `pages.type` |
|---|---|---|---|---|
| 实体·机构 | `机构/` | 有专名的行为主体 | 红(中心) | `entity`(subtype=institution) |
| 实体·工具 | `工具/` | 被某机构创设并运行的政策工具 | 蓝 | `entity`(subtype=instrument) |
| 实体·指标 | `指标/` | 可反复取数的**命名时间序列**(身份是序列,不是某天的值) | 青 | `entity`(subtype=indicator) |
| 概念·机制 | `机制/` | 必须靠内涵定义才能理解的机理/框架 | 绿 | `concept` |
| 事件 | `事件/` | 有确定日期+施动者,发生过一次就不再发生 | 黄 | `event` |
| 分析 | `分析/` | 基于上述节点的研究判断(=派生视图,删了不影响本体);研究课题落这里 | 灰 | `analysis` |
| 来源 | `来源/` | 一篇研报/文章原文的承载页,所有断言可溯源到它 | 浅灰 | `source` |

> **两条不建页的硬规矩(来自契约 §0):**
> - **数值绝不是节点。** `7天逆回购利率=1.40%` 不开页,进 `data.db` 的 `data_points`。图谱里只有"7天逆回购利率"这条序列页,没有"1.40%"这个点。
> - **分类标签不是节点、不建页。** 数量型/价格型/结构性这类分类维度是贴在工具上的多维标签,以 `classified_as` **边**记(写进 `relations`),图谱按它分桶着色,但它本身没有页。

**颜色纪律**:Obsidian graph 按 `path:机构/` 等子目录着色。顶层节点类型 7 个,但实体三类(机构/工具/指标)可视作同一红/蓝/青家族;**graph.json 的颜色分组控制在 ≤ 6~7 个**(再多肉眼分不清)。`graph.json` 里**不要**放排在最后的 `path:wiki` catch-all 灰色规则,否则会盖掉所有按子目录的着色。

**命名纪律**:**单一中文 slug = 文件名 = `[[wikilink]]` = `data.db` 主键**。不另起 PascalCase 英文 id(会造出第二套命名,与 Obsidian 的中文文件名链接打架)。跨研报、跨课题去重靠页面 frontmatter 的 `aliases:` 字段(如 `OMO=7天逆回购`、`MDS=买断式逆回购`、"重启/恢复"国债买卖)。

---

### 数据分层原则

| 层 | 载体 | 存什么 | 为什么 |
|----|------|--------|--------|
| **叙事层** | Markdown 页面 | 分析、上下文、wikilink、机制正文、退役 callout | 人类阅读、Obsidian 浏览 |
| **数据层** | `data.db`(SQLite) | T0 数值、T1 状态、T2 逻辑、T4 事件、关系(全部带时态) | 聚合查询、跨页对比、时间线、退役回溯 |
| **元数据层** | YAML frontmatter | `title`, `type`, `subtype`, `created`, `updated`, `aliases`, `sources`, `confidence`, `relations`,(机制页另有 `durability`/`preconditions`/`falsifiable_by`,事件页另有 `event_date`/`actor`/`retires`/`sets`) | 页面身份标识、Obsidian Properties 过滤 |

**Frontmatter 不存储 `data` 和 `history` 字段。** 所有结构化数据写入 `data.db`。`relations` 在 frontmatter 中保留(Obsidian wikilink 渲染需要),同时写入 `data.db`(查询/校验需要),两者必须一致。

---

## data.db 目标 Schema(v2)

`data.db` 是该领域唯一的结构化真相源。下表是 `store.py` 改造要对齐的**契约**(同 `_ontology.md` §7);引擎据此建表。核心思想:**节点 / 数据 / 边 三分,且数据本身带"何时为真"和"我何时记的"两条时间轴**。

```sql
-- 页面身份表:每个 wiki 节点一行(数值和分类标签不在此表)
CREATE TABLE pages (
    slug        TEXT PRIMARY KEY,          -- 中文 slug = 文件名 = wikilink = 主键
    title       TEXT NOT NULL,
    type        TEXT NOT NULL
        CHECK(type IN ('source','entity','concept','event','analysis')),  -- v2 新增 'event'
    subtype     TEXT                       -- 仅 entity:institution|instrument|indicator
        CHECK(subtype IS NULL OR subtype IN ('institution','instrument','indicator')),
    confidence  TEXT NOT NULL DEFAULT 'medium'
        CHECK(confidence IN ('high','medium','low','contested')),
    created     TEXT NOT NULL,
    updated     TEXT NOT NULL
);

-- T0 观测值:某指标某时点的一次测量,值是数字,逐期一条时序
CREATE TABLE data_points (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    page_slug     TEXT NOT NULL REFERENCES pages(slug),
    field         TEXT NOT NULL,
    value         REAL NOT NULL,
    unit          TEXT NOT NULL,
    period        TEXT NOT NULL,           -- valid-time:这个值对应"世界上的哪个时点/期"
    recorded_at   TEXT NOT NULL,           -- transaction-time:我哪天、从哪份研报记下的    [v2 新增]
    source_slug   TEXT NOT NULL,           -- 来源页 slug                                [v2 新增/必填]
    supersedes_id INTEGER,                 -- 同 period 被新研报修正时,指向被取代的旧行
    scope         TEXT,
    confidence    TEXT DEFAULT 'high'
        CHECK(confidence IN ('high','medium','low','contested'))
    -- 同 period 被新研报修正:保留两行 + 用 recorded_at/supersedes_id 区分,不塞进 history 表
);

-- T1 状态 + T2 耐用逻辑:拉链表。object 是文本/slug(非数值命题),靠事件切换    [v2 新增表]
CREATE TABLE facts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    page_slug      TEXT NOT NULL REFERENCES pages(slug),
    predicate      TEXT NOT NULL,          -- 谓词,如 "政策利率锚是"
    object_text    TEXT,                   -- 文本宾语
    object_slug    TEXT,                   -- 或指向另一节点的 slug
    valid_from     TEXT NOT NULL,          -- valid-time 起:世界上何时起为真
    valid_to       TEXT NOT NULL DEFAULT '9999-12-31',  -- valid-time 止:9999=至今有效
    is_current     INTEGER NOT NULL DEFAULT 1,           -- 1=当前态,0=已退役
    recorded_at    TEXT NOT NULL,          -- transaction-time 起:我何时记下这条
    recorded_until TEXT NOT NULL DEFAULT '9999-12-31',   -- transaction-time 止:勘误时封口
    confidence     TEXT DEFAULT 'medium'
        CHECK(confidence IN ('high','medium','low','contested')),
    source_slug    TEXT NOT NULL,
    supersedes_id  INTEGER,                -- 指向被本行取代的旧 facts 行
    caused_by_event TEXT                   -- 指向盖章的 T4 事件 slug(events.slug)
);

-- T4 事件:append-only,所有 T1/T2 切换的盖章者。只增不改                          [v2 新增表]
CREATE TABLE events (
    slug        TEXT PRIMARY KEY,          -- 事件页 slug,如 2025-03-MLF改革
    event_date  TEXT NOT NULL,             -- 发生日期(或代理桩日期,见契约 §9)
    actor_slug  TEXT,                      -- 施动者(机构 slug)
    description TEXT,
    source_slug TEXT NOT NULL,
    recorded_at TEXT NOT NULL
    -- 事件的 retires[] / sets{} 写在事件页 frontmatter,并通过 facts.caused_by_event 关联
);

-- T3 关系(受控词表的边)+ 时态列:近永久边 valid_to 留 9999,永不硬删          [v2 补时态]
CREATE TABLE relations (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    from_slug         TEXT NOT NULL,
    to_slug           TEXT NOT NULL,
    type              TEXT NOT NULL,       -- 受控词表(见契约 §3),lint 拒绝越界边
    bound_role        TEXT,                -- 仅 bounds 边:upper|lower|center
    valid_from        TEXT,                                   -- [v2 新增]
    valid_to          TEXT NOT NULL DEFAULT '9999-12-31',     -- [v2 新增]
    recorded_at       TEXT,                                   -- [v2 新增]
    retract_event_slug TEXT,              -- 边被某事件收回时,指向该事件         [v2 新增]
    UNIQUE(from_slug, to_slug, type)
);

-- 索引
CREATE INDEX idx_dp_page    ON data_points(page_slug);
CREATE INDEX idx_dp_field   ON data_points(field);
CREATE INDEX idx_dp_period  ON data_points(period);
CREATE INDEX idx_facts_page ON facts(page_slug);
CREATE INDEX idx_facts_cur  ON facts(is_current);
CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_rel_from   ON relations(from_slug);
CREATE INDEX idx_rel_to     ON relations(to_slug);
CREATE INDEX idx_rel_type   ON relations(type);
```

> **从 v1 迁移的关键变化(给读旧 store.py 的人对照):**
> - `pages.type` 的 CHECK 由 `(source/entity/concept/analysis/mental-model)` 改为 `(source/entity/concept/event/analysis)`——**新增 `event`,去掉 `mental-model`**(心智模型这一独立类型在领域 wiki 里并入 `concept`/机制)。新增可选 `subtype` 区分机构/工具/指标。
> - `data_points` **补 `recorded_at`、`source_slug`(必填)、`supersedes_id`**;同 period 纠错不再走旧的 `history` 表,而是"保留两行 + recorded_at 区分"。
> - **旧 `history` 表退场**,被职责更清晰的两张表取代:`facts`(T1 状态 / T2 逻辑的退役拉链)+ `events`(T4 盖章)。
> - `relations` **补 `bound_role` 和四个时态列**(valid_from/valid_to/recorded_at/retract_event_slug)。

### 六档时间模型 → 落表对照

哪种知识进哪张表,由契约 §4 的 6 档时间模型决定。引擎据此分流:

| 档 | 是什么 | 落在哪 | 一句记录方式 |
|---|---|---|---|
| **T0** 观测值 | 某指标某时点的一次测量(值是数字) | `data_points` | 逐期一条;同 period 纠错保留两行,recorded_at 区分 |
| **T1** 状态/制度态 | 一段时间恒为真、被事件一刀切换的命题 | `facts`(拉链) | 变化=旧行封 valid_to + 插新行,挂 caused_by_event |
| **T2** 耐用逻辑 | 跨周期的因果链/定义(可证伪) | 机制页正文 + `facts`(带 confidence/durability) | 被证伪时同样走退役拉链 |
| **T3** 实体/近永久关系 | 客观存在物及本质归属 | 实体页 + `relations`(带时态) | 近永久边 valid_to 留 9999 |
| **T4** 事件 | 有日期+施动者,发生即固定 | `events` 表 + 事件页 | append-only,只增不改 |
| **T5** 类型公理 | 约束"别的知识长什么样" | `_ontology.md` + 表 CHECK 约束 | 不进数据行,进 schema |

> **关键裁决(契约 §4):** "当前政策利率=7天逆回购"是 **T1 状态**(进 `facts`,object 是文本,靠事件切换);"7天逆回购利率=1.40%"是 **T0 测量**(进 `data_points`,value 是数字,逐月一条)。两种物,记录方式必须不同——这正是 `facts` 和 `data_points` 分两张表的原因。

### 记录三铁律(为什么是这套表结构)

表结构是为了让契约 §5 的三铁律可执行:

1. **退役不删除**:T0 同 period 纠错才允许覆盖;一旦跨到 T1/T2/T3,任何"变化"都是"旧行封 `valid_to` / `is_current=0` + 插新行",**永不 DELETE**。这要求每张可变表都带 `valid_from/valid_to`(+`is_current`/`supersedes_id`)。
2. **双时态分轴**:每条断言两条时间轴——`valid_from/valid_to`(世界上何时为真)+ `recorded_at`(我哪份研报记的)。**改 `valid_from`=世界变了;只改 `recorded_at`/封 `recorded_until`=我自己勘误。** 这俩绝不能混,所以每张表都同时有这两组列。
3. **事件盖章**:一切 T1/T2 当前态的改变都要追溯到一个 T4 事件——`facts.caused_by_event` 指向 `events.slug`,`relations.retract_event_slug` 指向收回它的事件。

> 退役协议六步(写事件页 → 给旧行盖 valid 章 → 连因果指针 → 插继任新行 → 页面层加退役 callout)的完整范例见契约 §6。引擎只需保证上述列存在、且封章只改 `valid_to`/`is_current`/`recorded_until` 三列。

### data.db 初始化

领域 wiki 创建时,Agent 运行 `python store.py init wiki/{domain}/` 初始化数据库。表结构以本节 v2 schema 为准(`store.py` 据此实现/改造),包含:`pages`, `data_points`, `facts`, `events`, `relations`。

> **基础设施纪律(契约 §7):** 全部在现有 SQLite 内,**不引入任何外部时序数据库**。用户体量几千行,缺的是双时态拉链表结构,不是新产品。海量行情数据走 juzi/ablemind 等数据 MCP,不进 wiki。

---

## Obsidian 兼容

`wiki/` 目录(及其下每个领域目录)可直接作为 Obsidian vault 打开(`Open folder as vault`):

- `[[slug]]` / `[[slug|display]]` → Obsidian Graph View 自动渲染拓扑(slug 是中文文件名,直接可读)
- YAML frontmatter → Obsidian Properties 面板,可按 `confidence`、`type`、`subtype`、`is_current` 等字段过滤
- `机构/`、`工具/`、`指标/`、`机制/`、`事件/`、`分析/`、`来源/` 子目录 → Obsidian 文件夹视图

> **不再需要英文目录 + 中文 Folder Note 的别名层。** v2 子目录名本身就是中文(机构/工具/指标/机制/事件/分析/来源),Obsidian 文件夹视图直接显示中文含义,无需为弥合"英文目录名/中文显示"而维护 folder note。若要给某子目录加一段导航说明,可放一个同名 folder note(如 `机构/机构.md`)并启用 Folder notes 插件,但这是可选项,不是必需的别名机制。

**首次创建某领域 wiki 时**,Agent 应初始化 `.obsidian/` 配置目录(注意:这是 Obsidian 约定的配置目录,是唯一允许的点目录,不放知识节点),启用图谱着色:

```
wiki/.obsidian/             # 或 wiki/{domain}/.obsidian/,取决于把哪一层当 vault 根
├── graph.json       # 图谱配色方案(按 path 子目录和 Properties 分组着色)
├── app.json         # {}
├── appearance.json  # {}
└── core-plugins.json # 启用 graph、backlink、properties、tag-pane(folder-note 可选)
```

`graph.json` 按**节点类型子目录**预设颜色分组(对齐契约 §2 的图谱色;实体三类用同一暖色家族,控制总色数 ≤ 7):

| 分组规则 | 颜色 | 说明 |
|---------|------|------|
| `path:机构/` | 红 | 实体·机构(中心) |
| `path:工具/` | 蓝 | 实体·工具 |
| `path:指标/` | 青 | 实体·指标 |
| `path:机制/` | 绿 | 概念·机制 |
| `path:事件/` | 黄 | 事件 |
| `path:分析/` | 灰 | 分析 / 研究课题 |
| `path:来源/` | 浅灰 | 来源 |
| `[confidence:contested]` | 红描边 | 有争议的节点(Obsidian Properties 语法匹配 frontmatter) |

> **切忌**在 `graph.json` 末尾放 `path:wiki` 这类 catch-all 灰色规则——它会盖掉上面所有按子目录的着色。也不要把 9 种以上颜色塞进去(肉眼分不清)。

同时设置:
- `showTags: false`(不在图谱中显示 tag 节点——着色靠 `path:` 和 Properties 查询,tag 仅用于搜索过滤)
- `showArrow: true`(显示关系方向;受控词表的边是有向的)
- `textFadeMultiplier: -1.5`(默认显示节点标签)
- `search: "-path:log -path:_ontology"`(排除 log 与契约等元文件,让图谱只剩知识节点)

如果需要排除 `_report.html` 等生成文件,在 Obsidian Settings → Files & Links → Excluded files 中添加 `_*`。

### 可视化报告

运行 `python schema.py --report wiki/{domain}/` 生成 `_report.html`,浏览器打开即可查看:

- 统计面板:页面数、按类型分布(机构/工具/指标/机制/事件/分析/来源)、contested 数
- 交互式关系图:vis-network.js 渲染受控词表的边,可拖拽、缩放
- 数据表:`data_points`(value + unit + period + recorded_at + confidence)
- 状态拉链:`facts` 的当前态与已退役行(valid_from/valid_to/caused_by_event)
- Freshness:按 `updated` / `recorded_at` 排序
- Coverage Gaps:孤页、缺失页面、缺事件盖章的状态变化

---

## 初始化模板

### 新建领域 wiki 时创建的子目录

按节点类型建 7 个中文子目录(`机构/ 工具/ 指标/ 机制/ 事件/ 分析/ 来源/`)。子目录可懒创建(首次有该类节点时才建),也可一次性建齐;名称固定,不随领域变化。

### 新建领域 wiki 时创建的 Hub 页面

Hub 页面以**领域中文名**命名(如 `宏观.md`),不用 `index.md`。

原因:Obsidian 图谱中节点显示文件名,多个领域都用 `index` 无法区分,且失去了作为中心节点(MOC)的导航意义。

```markdown
# {领域中文名} · Hub

> 0 pages | Created: {日期} | Domain: {domain}
> 本体契约见 [[_ontology]]

## 机构 (0)

## 工具 (0)

## 指标 (0)

## 机制 (0)

## 事件 (0)

## 分析 (0)

## 来源 (0)
```

### 新建领域 wiki 时创建的 log.md

```markdown
# {领域中文名} Wiki Log

## {日期} — init
- Created domain wiki: {domain}
- Ontology contract: _ontology.md
- Description: {描述}
```

> **`_ontology.md` 是领域 wiki 的一等公民。** 每个领域目录都有自己的本体契约;它不是模板自动生成的空壳,而是人和 Agent 在 ingest/recall 前必读的权威说明。新建领域时若无契约,应先依本规格 + 引擎通用本体起草一份,再开始 ingest。

---

## 各类型页面 frontmatter 模板

frontmatter 只存身份与关系,不存数据(数据进 `data.db`)。模板与契约附录一致:

```yaml
# 实体(机构 / 工具 / 指标)
title: 7天逆回购
type: entity
subtype: instrument        # institution | instrument | indicator
created: 2026-06-07
updated: 2026-06-07
aliases: [OMO, 公开市场操作, 7天逆回购操作]   # 跨研报/跨课题去重靠这个
sources: [2026-05-25-某券商固收报告]
confidence: high
relations:
  - {target: 中国人民银行, type: operated_by}
  - {target: 价格型, type: classified_as}      # 分类标签是边,不是页
tags: [实体, 工具]

# 机制(概念)
title: 利率走廊
type: concept
created: 2026-06-07
updated: 2026-06-07
sources: [...]
confidence: high
durability: medium          # T2 耐用度: high/medium/low
preconditions: [短端利率由央行主导]
falsifiable_by: [若放弃走廊调控转向单一政策利率]
relations:
  - {target: SLF利率, type: bounds, bound_role: upper}
  - {target: 超额准备金利率, type: bounds, bound_role: lower}
  - {target: 7天逆回购利率, type: bounds, bound_role: center}
tags: [概念, 机制]

# 事件
title: 2025-03 MLF美式招标改革
type: event
event_date: 2025-03-01
actor: 中国人民银行
created: 2026-06-07
updated: 2026-06-07
sources: [...]
retires: [MLF是政策利率锚]            # 退役了哪条 T1/T2 断言
sets: {政策利率锚: 7天逆回购}          # 设置了哪个新当前态
tags: [事件]
```

---

## 文件大小预期

| Wiki 规模 | 源文件数 | 总页面数 | 磁盘占用 | 适用检索方式 |
|-----------|---------|---------|---------|------------|
| 小 | 1-10 | 5-30 | < 1 MB | grep + 读 hub 页面 |
| 中 | 10-50 | 30-150 | 1-10 MB | grep + 读 hub 页面 |
| 大 | 50-200 | 150-500 | 10-50 MB | 需要升级到索引检索(超出 Skill 范围) |

**默认模式上限:~500 页。** 超过后启用 SQLite FTS5 索引(零依赖,Python 自带),支持 BM25 排序和反向链接查询。详见 `scaling.md`。

> 再往上(需要向量检索 / 多用户协作),迁移到外部平台。

---

## 跨领域操作

`query` 默认在单个领域 wiki 内搜索。如果用户问的问题跨越多个领域:

```
用户:货币政策传导和信用利差之间有什么联系?

Agent:
1. 读 wiki/ 下的领域目录列表,识别相关领域
2. 分别读 macro/ 和 credit/ 的 Hub 页面(及各自 _ontology.md)
3. 在两个领域中搜索相关节点(指标/机制/事件)
4. 综合回答,标注来源属于哪个领域
```

> 同一研究课题若横跨两个领域,它的"分析页"放在主领域的 `分析/` 下,通过 `[[wikilink]]` 引用另一领域的节点;**不**为它新开顶层目录。

---

## 源文件处理

不同格式的源文件,ingest 时的处理方式:

| 格式 | 处理方式 | 说明 |
|------|---------|------|
| 文本 / Markdown | 直接读取 | 最理想的输入格式 |
| PDF | 读取文本内容(Agent 能力范围内) | 复杂排版可能丢失结构 |
| Excel / CSV | 读取数据,提取关键指标 | 数值数据写入 `data.db` 的 `data_points`(进对应指标页的 T0 时序),不堆在页面正文 |
| 用户口述 / 对话文本 | 作为文本 ingest | 标注来源为"口述",confidence 默认 medium |
| URL / 网页 | 用 WebFetch 获取内容后 ingest | 标注来源 URL |

**Agent 不存储源文件原件**——只存储 `来源/` 下的 source 摘要页(不可变),所有断言可溯源到它。原件由用户自行管理。
