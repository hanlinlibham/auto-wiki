# auto-wiki

教你的 AI Agent 构建和维护持久化知识 wiki——让它不再做完就忘。

## 问题

AI Agent 做研究、写报告、拉数据——然后全忘了。下周问同样领域的问题，又从零开始。RAG 能检索，但不能积累——每次都从原始文档重新推导答案。

## 方案

auto-wiki 是面向 AI Agent（Claude Code、Codex 等）的**知识编译器** Skill。Agent 不再每次从原始文档临时检索，而是**增量构建和维护一个结构化 wiki**——把新信息和已有页面对比，更新变化的、标注矛盾的、保留知识演化的轨迹。

三个操作：

| 操作 | Agent 做什么 |
|------|-------------|
| **ingest** | 读源文件 → 搜索已有 wiki → 比较新旧 → 更新/创建页面 → 结构化数据写入 SQLite |
| **query** | 搜索 wiki 索引 → 读取相关页面 → 综合回答并引用来源 → 识别知识缺口 |
| **lint** | 扫描全部页面 → 修复断链 → 检测矛盾 → 报告健康度 |

## 快速开始

1. 复制 `skill/auto-wiki-cn/`（中文版）或 `skill/auto-wiki-en/`（英文版）到你的 Agent 工作区
2. 让 Agent 读取 `SKILL.md` 作为指令
3. 开始积累：

```
你：   "研究个人养老金制度，帮我建立知识框架"
Agent: [搜索政策文件 → 创建 wiki → ingest 2 个来源 → 构建 6 个概念页面]
Agent: "已创建 personal-pension wiki：6 个概念、1 个实体、2 个来源。框架如下..."

你：   "找一些关于参与意愿的研究"
Agent: [搜索 → 找到 3 篇论文 → ingest → 更新已有概念 → 标记 1 处矛盾]
Agent: "更新 wiki：2 个概念更新、1 个新概念、1 处 contested..."

你：   "根据积累的知识，政策应该怎么设计来提高参与率？"
Agent: [读 wiki → 综合 5 个概念页 → 引用来源]
Agent: "根据 [[enrollment-friction]]、[[tax-incentive-effect]] 和 [[ira-usa]]..."
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

## Ingest：核心差异化

Agent ingest 新来源时，不是简单追加——而是**编译**：

| 结果 | 触发条件 | 动作 |
|------|---------|------|
| **强化** | 新信息与已有结论一致 | 追加来源引用，提升 confidence |
| **更新** | 新信息有更新的日期或更权威的来源 | 改写页面，旧结论进 history |
| **冲突** | 来源意见不一致，无法判断谁对 | 并列保留，标记 `contested` |

这个三路比较让 wiki 随时间复合增长，而不是变成垃圾堆。

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

- **[LLM Wiki](https://x.com/toaborern/status/1935967165527437666)** by Tobi Lutke — LLM 维护持久化 wiki 的原始模式，直接启发了 auto-wiki 的编译模型。"知识应该编译一次并保持更新，而非每次查询时重新推导"这一核心洞察是本项目的基石。

- **[autoresearch](https://github.com/karpathy/autoresearch)** by Andrej Karpathy — 证明了 AI Agent 可以自主迭代研究。autoresearch 通过训练循环优化标量指标，auto-wiki 将同样的"Agent 作为自主研究者"理念应用于通过增量编译实现知识积累。

- **[FIBO](https://spec.edmcouncil.org/fibo/)** (Financial Industry Business Ontology) by EDM Council — 金融行业本体的黄金标准。auto-wiki 的种子/校验器架构设计用于利用 FIBO 的 627K+ 推理三元组进行逻辑校验，而不要求用户学习 OWL/RDF。

- **[Obsidian](https://obsidian.md/)** — auto-wiki 的 markdown 格式（YAML frontmatter + `[[wikilinks]]`）有意兼容 Obsidian，用户可以用知识图谱 UI 浏览 wiki，同时 Agent 在后台维护。

## 许可证

MIT. 见 [LICENSE](LICENSE)。
