# AGENTS.md — auto-wiki

> Agent 工作指南。每次会话自动加载。

---

## 项目概述

**auto-wiki** 是一个教 AI Agent 构建和维护持久化知识 wiki 的 Skill（开源，MIT）。

核心理念：**编译而非检索**——Agent 读到新材料后，和 wiki 已有页面做三路比较（强化/更新/冲突），知识持续积累而不是每次从头推导。

七个模式：init（访谈建库）、source（取材，落 Inbox 不碰 wiki）、recall（持续知识回答）、
ingest（编译源文件）、query（单次查询）、lint（健康治理）、deep-dive（lint 找缺口 + 搜索补全）。

**中文版是唯一在维护的版本**（v0.4.4）。英文版已于 2026-08-12 归档在 v0.3.0，
移入 `archive/auto-wiki-en-v0.3.0/`——退役不删除，文件原样保留，仍能跑但不再更新。
改动只落中文版。要复活英文版走贡献流程，先开 issue。

GitHub: https://github.com/hanlinlibham/auto-wiki

## 仓库结构

```
auto-wiki/
├── skill/
│   └── auto-wiki-cn/          # 中文版 Skill v0.4.4（唯一在维护）
│       ├── SKILL.md           #   入口：7 模式路由
│       ├── references/        #   协议文档 + Python 工具（precheck/instance/export_okf）
│       ├── seeds/             #   领域种子（reading-notes / fibo-pensions）
│       ├── validators/        #   逻辑校验器（FIBO SPARQL）
│       ├── examples/          #   可运行示例（bookshelf 最小闭环）
│       └── assets/            #   可选 Obsidian graph.json 模板
├── archive/                   # 退役区（退役不删除，墓碑索引在 archive/README.md）
│   └── auto-wiki-en-v0.3.0/   #   英文版 Skill，2026-08-12 归档
├── docs/                      # 研究文档（tracked）
│   ├── figure/                #   配图（RAG 对比、ingest 流程、架构图）
│   ├── llmwiki-pattern.md     #   LLM Wiki 模式研究
│   ├── person-as-ontology.md  #   人物本体研究
│   └── why-compilation.md     #   编译 vs RAG 论证
├── draft/                     # 文章草稿 & 内部文档（gitignored）
│   ├── article-draft.md       #   公众号文章初稿
│   ├── figure/                #   文章配图（与 docs/figure 同源）
│   ├── archive/               #   早期探索文档
│   └── issue/                 #   行动计划跟踪
├── README.md                  # 双语 README（英文外层 + 中文折叠块，唯一真源）
├── README.zh.md               # 旧链接入口，指向 README.md
├── CHANGELOG.md               # 版本历史
└── requirements.txt           # Python 依赖（pyyaml + pydantic）
```

## 架构要点

- **两层分离**：Markdown 负责叙事分析，SQLite（data.db）负责结构化数据。数值绝不做节点，
  分类标签是边不是页
- **按领域组织**：wiki 按 domain 而非研究课题分目录；课题降级为 `{domain}/分析/` 下一页
- **写入前硬闸**：`precheck.py page` 的 error 必须修完才落库；撞车检测只提示不阻断
- **引擎不改实例契约**：`meta.yaml` 的 `born_of` 记出生版本，升级只给 advisory 迁移提示
- **领域解耦**：Skill core 领域无关，seeds/ 和 validators/ 可插拔
- **Obsidian 兼容**：YAML frontmatter + `[[wikilinks]]`，可用 Obsidian 直接浏览
- **可视化**：`schema.py --report` 生成自包含 HTML（vis-network 关系图 + 数据表）

## 与 AbleMind 的关系

auto-wiki 从 AbleMind Cowork 项目（`able-dpagt`）中孵化。早期开发在 `dpagt/docs/autoresearch/` 下进行，后独立为开源仓库。

- auto-wiki 是独立开源项目，不依赖 AbleMind 任何代码
- AbleMind 产品层未来可能基于 auto-wiki 的编译模型做知识层（加 MCP server 包装 + embedding 索引）
- 知识通路断点 3-4（wiki 作为 MCP server、平台级注入）留给 AbleMind 产品层解决

## Git 规范

### 提交消息格式

```
feat: 简短描述
fix: 简短描述
docs: 简短描述
```

### 禁止跟踪

- `__pycache__/`、`*.pyc`
- `.DS_Store`
- `wiki/`（运行时产物；但 `skill/*/examples/` 下的示例库是 tracked 的）
- `data.db`（运行时产物）
