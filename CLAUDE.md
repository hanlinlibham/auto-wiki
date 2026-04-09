# CLAUDE.md — auto-wiki

> Claude Code 工作指南。每次会话自动加载。

---

## 项目概述

**auto-wiki** 是一个教 AI Agent 构建和维护持久化知识 wiki 的 Skill（开源，MIT）。

核心理念：**编译而非检索**——Agent 读到新材料后，和 wiki 已有页面做三路比较（强化/更新/冲突），知识持续积累而不是每次从头推导。

四个模式：recall（持续知识回答）、ingest（编译源文件）、query（单次查询）、lint（健康治理）。

GitHub: https://github.com/hanlinlibham/auto-wiki

## 仓库结构

```
auto-wiki/
├── skill/
│   ├── auto-wiki-cn/          # 中文版 Skill（完整，已测试）
│   │   ├── SKILL.md           #   入口：4 模式路由
│   │   ├── references/        #   协议文档 + Python 工具
│   │   ├── seeds/             #   领域种子（冷启动词表）
│   │   └── validators/        #   逻辑校验器（FIBO SPARQL）
│   └── auto-wiki-en/          # 英文版 Skill（已翻译）
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
├── README.md                  # 英文 README
├── README.zh.md               # 中文 README
└── requirements.txt           # Python 依赖（pydantic）
```

## 架构要点

- **两层分离**：Markdown 负责叙事分析，SQLite（data.db）负责结构化数据
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
- `.wiki/`（运行时产物）
- `data.db`（运行时产物）
