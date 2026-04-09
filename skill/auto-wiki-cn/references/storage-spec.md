# 存储规格

## Wiki 根目录

所有 wiki 存储在工作目录下的 `.wiki/` 目录中：

```
{项目根目录}/
└── .wiki/
    ├── enterprise-annuity/      # 一个研究主题一个目录
    ├── charlie-munger/
    └── public-fund/
```

**位置选择逻辑**（按优先级）：
1. 如果当前目录有 `.wiki/` → 使用它
2. 如果当前目录有 `.claude/` → 在同级创建 `.wiki/`
3. 如果当前目录是 git repo 根 → 在根目录创建 `.wiki/`
4. 否则 → 在当前目录创建 `.wiki/`

**与 .gitignore 的关系**：建议将 `.wiki/` 加入 `.gitignore`（wiki 是个人知识库，不应随项目代码提交）。如果用户希望版本管理 wiki，可以在 `.wiki/` 内单独 `git init`。

### Obsidian 兼容

`.wiki/` 目录可直接作为 Obsidian vault 打开（`Open folder as vault`）：

- `[[slug]]` / `[[slug|display]]` → Obsidian Graph View 自动渲染拓扑
- YAML frontmatter → Obsidian Properties 面板，可按 confidence、type 等字段过滤
- `sources/`、`entities/`、`concepts/` 目录 → Obsidian 文件夹视图

**首次创建 `.wiki/` 时**，Agent 应初始化 `.obsidian/` 配置目录，启用图谱着色：

```
.wiki/.obsidian/
├── graph.json       # 图谱配色方案（按 path 和 tag 分组着色）
├── app.json         # {}
├── appearance.json  # {}
└── core-plugins.json # 启用 graph、backlink、properties、tag-pane
```

`graph.json` 预设 5 个颜色分组：

| 分组规则 | 颜色 | 说明 |
|---------|------|------|
| `path:sources/` | 蓝灰 | 源文件 |
| `path:entities/` | 青绿 | 实体 |
| `path:concepts/` | 翠绿 | 概念 |
| `path:analyses/` | 紫色 | 分析 |
| `tag:#contested` | 红色 | 有争议的节点（高亮风险） |

同时设置 `showArrow: true`（显示关系方向）和 `textFadeMultiplier: -1.5`（默认显示节点标签）。

如果需要排除 `_report.html` 等生成文件，在 Obsidian Settings → Files & Links → Excluded files 中添加 `_*`。

### 可视化报告

运行 `python schema.py --report .wiki/{主题}/` 生成 `_report.html`，浏览器打开即可查看：

- 统计面板：页面数、类型分布、contested 数
- 交互式关系图：vis-network.js 渲染，可拖拽、缩放
- 数据表：所有结构化数据点（value + unit + period + confidence）
- Freshness：按更新日期排序
- Coverage Gaps：孤页、缺失页面

## 单个 Wiki 的目录结构

```
.wiki/{主题名}/
├── data.db                  # 结构化数据（SQLite，store.py 管理）
├── meta.yaml                # Wiki 元数据（本体类型、创建时间、描述）
├── index.md                 # 页面目录（Agent 自动维护）
├── log.md                   # 操作日志（append-only）
├── _report.html             # 可视化报告（schema.py --report 生成）
├── sources/                 # 源文件摘要页（不可变）
│   ├── 2026-04-06-policy-doc.md
│   └── 2026-04-03-annual-report.md
├── entities/                # 实体页（叙事分析）
│   ├── alpha-corp.md
│   └── regulatory-agency.md
├── concepts/                # 概念页
│   ├── fiduciary-responsibility.md
│   └── portable-annuity.md
└── analyses/                # 分析归档页（query 产出）
    └── market-comparison.md
```

### 数据分层原则

| 层 | 载体 | 存什么 | 为什么 |
|----|------|--------|--------|
| **叙事层** | Markdown 页面 | 分析、上下文、wikilink | 人类阅读、Obsidian 浏览 |
| **数据层** | data.db (SQLite) | 数值、时序、关系、history | 聚合查询、跨页面对比、时间线 |
| **元数据层** | YAML frontmatter | title, type, created, updated, sources, confidence | 页面身份标识 |

**Frontmatter 不再存储 `data` 和 `history` 字段。** 所有结构化数据写入 `data.db`。
Frontmatter 只保留：`title`, `type`, `created`, `updated`, `sources`, `confidence`。
`relations` 在 frontmatter 中保留（Obsidian wikilink 渲染需要），同时写入 `data.db`（查询需要）。

### data.db 初始化

Wiki 创建时，Agent 运行 `python store.py init .wiki/{主题}/` 初始化数据库。
表结构见 `store.py`，包含：`pages`, `data_points`, `history`, `relations`。

## meta.yaml

每个 wiki 的元信息，创建时写入，后续 lint 时更新统计：

```yaml
name: my-research-topic
ontology_type: domain           # domain | cognitive | general
description: 研究主题描述
seed: fibo-pensions             # 可选，引用 seeds/ 下的种子文件名
created: 2026-04-06
last_ingest: 2026-04-06
stats:
  sources: 3
  entities: 8
  concepts: 5
  analyses: 1
  total_pages: 17
  contested_count: 1
```

| 字段 | 必填 | 说明 |
|------|------|------|
| name | 是 | wiki 目录名 |
| ontology_type | 是 | domain / cognitive / general |
| description | 是 | 一句话描述研究主题 |
| seed | 否 | 种子配置名，对应 `seeds/{name}.md`。不设则无种子，wiki 自由生长 |
| created | 是 | 创建日期 |
| last_ingest | 是 | 最近 ingest 日期（Agent 更新） |
| stats | 是 | 页面统计（Agent / lint 更新） |

## 初始化模板

### 新建 Wiki 时创建的 index.md

```markdown
# {主题名} Wiki Index

> 0 pages | Created: {日期} | Type: {ontology_type}

## Sources (0)

## Entities (0)

## Concepts (0)

## Analyses (0)
```

### 新建 Wiki 时创建的 log.md

```markdown
# {主题名} Wiki Log

## {日期} — init
- Created wiki: {主题名}
- Ontology type: {ontology_type}
- Description: {描述}
```

## 文件大小预期

| Wiki 规模 | 源文件数 | 总页面数 | 磁盘占用 | 适用检索方式 |
|-----------|---------|---------|---------|------------|
| 小 | 1-10 | 5-30 | < 1 MB | grep + 读 index |
| 中 | 10-50 | 30-150 | 1-10 MB | grep + 读 index |
| 大 | 50-200 | 150-500 | 10-50 MB | 需要升级到索引检索（超出 Skill 范围） |

**默认模式上限：~500 页。** 超过后启用 SQLite FTS5 索引（零依赖，Python 自带），支持 BM25 排序和反向链接查询。详见 `scaling.md`。

> 再往上（需要向量检索 / 多用户协作），迁移到外部平台。

## 跨 Wiki 操作

`query` 默认在单个 wiki 内搜索。如果用户问的问题跨越多个 wiki：

```
用户：Munger 的投资框架和企业年金领域有什么交叉？

Agent：
1. 读 .wiki/ 下的目录列表，识别相关 wiki
2. 分别读 charlie-munger/index.md 和 enterprise-annuity/index.md
3. 在两个 wiki 中搜索相关页面
4. 综合回答，标注来源属于哪个 wiki
```

## 源文件处理

不同格式的源文件，ingest 时的处理方式：

| 格式 | 处理方式 | 说明 |
|------|---------|------|
| 文本 / Markdown | 直接读取 | 最理想的输入格式 |
| PDF | 读取文本内容（Agent 能力范围内） | 复杂排版可能丢失结构 |
| Excel / CSV | 读取数据，提取关键指标 | 数值数据写入实体页的"关键数据"段落 |
| 用户口述 / 对话文本 | 作为文本 ingest | 标注来源为"口述"，confidence 默认 medium |
| URL / 网页 | 用 WebFetch 获取内容后 ingest | 标注来源 URL |

**Agent 不存储源文件原件**——只存储 source 摘要页。原件由用户自行管理。
