# auto-wiki

[English](README.md) | [中文](README.zh.md)

教你的 AI Agent 构建和维护持久化知识 wiki——让它不再做完就忘。

## 问题

AI Agent 做研究、写报告、拉数据——然后全忘了。下周问同样领域的问题，又从零开始。RAG 能检索，但不能积累——每次都从原始文档重新推导答案。

## 方案

auto-wiki 是一个给 AI Agent（Claude Code、Codex 等）用的 Skill。装上之后，Agent 会自己维护一个 wiki：读到新材料就和已有页面比对，该更新的更新，说法矛盾的标出来，数据变了的记下演化过程。

四个模式：

| 模式 | 触发 | Agent 做什么 |
|------|------|-------------|
| **recall** | `/auto-wiki recall {topic}` | 加载 wiki 上下文，后续所有问题先查 wiki 再回答 |
| **ingest** | `/auto-wiki ingest` 或提供源材料 | 读源文件 → 比较新旧 → 更新/创建页面 → 数据写入 SQLite |
| **query** | `/auto-wiki query` | 单次查询：搜索 wiki → 综合回答并引用来源 → 识别缺口 |
| **lint** | `/auto-wiki lint` | 扫描全部页面 → 修复断链 → 检测矛盾 → 报告健康度 |

Agent 也能从自然语言自动路由——"之前研究过 XX"触发 recall，丢给它一篇文件触发 ingest。

## 快速开始

1. 复制 `skill/auto-wiki-cn/`（中文版）或 `skill/auto-wiki-en/`（英文版）到你的 Agent 工作区
2. 让 Agent 读取 `SKILL.md` 作为指令
3. 先积累，再使用：

**积累：**
```
你：   /auto-wiki ingest
你：   "研究个人养老金制度，帮我建立知识框架"
Agent: [搜索政策文件 → 创建 wiki → ingest 2 个来源 → 构建 6 个概念页面]

你：   "找一些关于参与意愿的研究"
Agent: [搜索 → 找到 3 篇论文 → ingest → 更新已有概念 → 标记 1 处矛盾]
```

**调用：**
```
你：   /auto-wiki recall personal-pension
Agent: 已进入 recall 模式。当前 wiki：22 页 / 8 数据点 / 2 处 contested。

你：   "政策应该怎么设计来提高参与率？"
Agent: 根据 [[enrollment-friction]]、[[tax-incentive-effect]] 和 [[ira-usa]]...
       ⚠️ 注意：税优激励效果存在矛盾（77.8% vs 25%）
       缺口：尚无 35 岁以下群体行为研究，建议补充。
```

## 语言版本

| 版本 | 目录 | 说明 |
|------|------|------|
| 中文 | `skill/auto-wiki-cn/` | Agent 协议为中文，wiki 产出为中文 |
| 英文 | `skill/auto-wiki-en/` | Agent 协议为英文，wiki 产出为英文 |

每个版本完全自包含——复制一个目录即可独立使用。Python 工具（`schema.py`、`store.py`）两个版本相同。

## 架构

```
.wiki/{主题}/
├── data.db              ← 结构化数据（SQLite：数据点、历史、关系）
├── meta.yaml            ← Wiki 元数据
├── index.md             ← 导航（Agent 自动维护）
├── log.md               ← 操作日志（append-only）
├── sources/             ← 源文件摘要（不可变）
├── entities/            ← 实体页面（叙事分析）
├── concepts/            ← 概念页面
└── analyses/            ← 分析归档（query 产出）
```

**两层分离：**

- **Markdown 页面** — 叙事分析、wikilink、人类可读。兼容 [Obsidian](https://obsidian.md/)。
- **SQLite 数据库** — 数值数据、时间序列、关系、历史。可查询。

Agent 在 markdown 中写分析，在 SQLite 中写数据。反过来不行。

## Ingest 怎么工作

Agent 拿到新材料后，会逐页和 wiki 里已有的内容比对，然后做出判断：

| 结果 | 触发条件 | 动作 |
|------|---------|------|
| **强化** | 新信息与已有结论一致 | 追加来源引用，提升 confidence |
| **更新** | 新信息有更新的日期或更权威的来源 | 改写页面，旧结论进 history |
| **冲突** | 来源意见不一致，无法判断谁对 | 并列保留，标记 `contested` |

就是这个比对过程，让 wiki 越用越厚实，不会变成只进不出的文件堆。

## Recall 怎么工作

Recall 是一个持续状态。进入后，这轮对话里的每个问题都先查 wiki：

1. 进入时加载 `index.md` + `data.db` 摘要
2. 每次提问：提取关键词 → 匹配 index 中的页面 → 查询 data.db → 读相关页面
3. 回答时引用页面（`[[slug]]`）、标注 contested、报告知识缺口
4. wiki 里没有的不编造，直接说"没有"并建议 ingest 什么

`exit recall` 或切换到其他模式时退出。

## 领域无关

Skill 核心与领域无关。领域知识通过插件配置：

- **无种子**：wiki 自由生长，Agent 按所见命名概念
- **有种子**：Agent 对齐行业标准术语，遵守防混淆规则
- **有校验器**：lint 检查逻辑一致性（如"这个关系类型对这个实体合法吗？"）

## 可视化

```bash
python references/schema.py --report .wiki/my-topic/
# → 生成 .wiki/my-topic/_report.html
# → 浏览器打开：交互式关系图 + 数据表 + 覆盖度缺口
```

也可用 Obsidian 打开 `.wiki/` 目录，Graph View 自动渲染 wikilink 拓扑。

## 致谢

本项目受以下工作的启发：

- **[LLM Wiki](https://github.com/swyxio/ai-notes/blob/main/Resources/llmwiki.md)** — LLM 维护持久化 wiki 的模式。想法由 [Tobi Lutke](https://x.com/tobi/status/1935967165527437666) 提出，[swyx](https://github.com/swyxio) 整理为可执行的实现文档。auto-wiki 的编译模型从这里发展而来。

- **[autoresearch](https://github.com/karpathy/autoresearch)** by Andrej Karpathy — 让 Agent 自己跑研究循环。autoresearch 用来优化训练指标，auto-wiki 借了同样的思路来做知识积累。

- **[FIBO](https://spec.edmcouncil.org/fibo/)** by EDM Council — 金融行业用得最广的语义本体标准，627K+ 推理三元组。auto-wiki 的种子/校验器就是为了能接上 FIBO 这类本体做逻辑校验。

- **[fibo-mcp](https://github.com/NeurofusionAI/fibo-mcp)** by NeurofusionAI — 将 FIBO 物化为可查询 SPARQL 端点的 MCP 服务器。auto-wiki 的校验器示例（`validators/fibo-mcp.md`）基于这个项目。

- **[Nuwa](https://github.com/hanlinlibham)** — 认知画像方法论，从人的著作和决策中提取心智模型、启发式和决策模式。auto-wiki 的认知本体类型（`ontology-types/cognitive.md`）改编自这套方法。

- **[Obsidian](https://obsidian.md/)** — wiki 格式（YAML frontmatter + `[[wikilinks]]`）刻意兼容 Obsidian，Agent 在后台编译，你用 Obsidian 浏览。

## 许可证

MIT. 见 [LICENSE](LICENSE)。
