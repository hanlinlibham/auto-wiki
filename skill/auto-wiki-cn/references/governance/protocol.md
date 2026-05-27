# Governance Protocol — 写入前治理扩展点

> auto-wiki 可选的**第三个**插件层。Seed 提供词汇,validator 提供 lint
> 时的检查;governance 模块提供**运行时规则:决定什么内容允许进入 wiki**。

本文件定义 auto-wiki 如何接入外部 governance 模块。第一个具体模块是
[`ontology-mem`](ontology-mem.md);未来其它模块也走同一套协议接入。

## 何时启用 governance

| 应该加 governance 的场景 | 不应该加的场景 |
|---|---|
| 你的 wiki 是研究产出，错了有真实下游成本（金融、医疗、合规） | 你的 wiki 是探索性的，错了重做成本低 |
| Agent 自创的内容不断污染 wiki | 所有输入都由用户精挑细选 |
| 你想要"agent 提议"和"wiki 接受"之间有一个 review 队列 | 你希望每次 ingest 立即生效 |
| 多租户:多人共享一个 wiki | 单用户单工作站 |

不确定的时候，**不加**。auto-wiki 默认的 ingest 协议已经对 merge /
update / conflict 有自己的判断 —— governance 是给"默认不够"的场景准
备的。

## 启用方式

在 `meta.yaml` 里声明：

```yaml
name: personal-pension
ontology_type: domain
seed: fibo-pensions
governance: ontology-mem    # ← 引用 governance/ontology-mem.md
```

`seed` 和 `governance` 两个字段**互相独立**。一个 wiki 可以两个都有、
有一个、两个都没有。它们工作在不同的层：

| 层 | 用途 | 触及范围 |
|---|---|---|
| **Seed** | 词汇标准化 | 页面命名、防混淆规则、实体模板 |
| **Validator** | Lint 时检查完整性 | `/auto-wiki lint` 运行时生成健康报告 |
| **Governance** | Ingest 前置门 | `/auto-wiki ingest` 运行时可以**阻断**写入 |

三个里只有 governance 能**阻止**写入 wiki。Seed 和 validator 是建议
性的；governance 是承重的。

## Governance 模块需要提供什么

每个 governance 模块包含：

1. **协议文档**位于
   `references/governance/{name}.md`，定义：

   - 模块接受的 candidate 格式
   - 模块能给出的判定（如 `verified` / `needs_review` / `rejected`）
   - 如何接入 ingest 流程（写入前钩子）
   - 如何把结果呈现给用户（review 卡片、状态报告）
   - 模块运行时需要的服务（MCP server、库等），以及如何启动

2. **wiki 目录里需要的状态文件**（如 ontology-mem 的
   `wiki/{topic}/governance.db`）。

3. **可选的 UX 扩展** —— 多数 governance 模块会加 review 卡片、
   recall 时的来源徽章、或通知流程。

## 与 ingest 协议的接入

当 `meta.yaml` 声明了 `governance: <name>`，ingest 流程多一个**强
制**的写入前步骤：

```
1. 读源文件                       ┐ 不变
2. 抽取 candidate 列表             ┘
3. ★ governance.gate(candidate)   ← 新增：route-before-write
   ├─ verified         → 进入 step 4
   ├─ needs_review     → 显示 review 卡片，不写入
   ├─ conflict_checked → 显示 review 卡片（含冲突详情）
   └─ rejected         → 记日志，不写入
4. 比对新旧                        ┐ 只对 verified 项执行
5. 写入 data.db                    │
6. 创建/更新 Markdown 页面          │
7. 更新 index.md 和 log.md         ┘
8. ★ 把非 verified 的项作为 review 卡片呈现
```

完整集成后的流程见
[`../ingest-protocol.md` § Governance 钩子](../ingest-protocol.md#governance-hook).

## 与 recall 协议的接入

当 `meta.yaml` 声明了 `governance: <name>`，recall 模式多两件事：

- **来源徽章**：从 wiki 引用的每条结论都应该标注它的 `origin_role`
  (`user` / `agent` / `extractor` / `system`)。用户一眼就能看到这条
  内容是自己输入的还是 agent 推断的。

- **review 队列感知**：作答前，agent 应该顺便查 governance 模块的
  review 队列里有没有与提问相关的待审项；如果有，要么提一句（"还有 3
  条待审项提到了 X，要不要先看？"），要么经用户同意后跑一段
  `/auto-wiki review` 子流程。

## 接入新 governance 模块的方法

1. 在 `references/governance/{your-name}.md` 写协议文档，结构参考
   `ontology-mem.md`。
2. 把运行时部分准备好 —— 通常是一个 agent 可调用的 MCP server。模块
   的协议文档要说明用户如何启动它。
3. 给 auto-wiki 提 PR。SKILL.md 里会把 governance 模块列在可选插件
   层（与 seed、validator 并列）。

## 当前可用模块

- [`ontology-mem`](ontology-mem.md) — route-before-store + 5 条冲突
  规则 + append-only ledger。适用于金融、医疗、合规，或任何"长期记忆
  错了有真实代价"的场景。

## 反模式

**不要叠加多个 governance 模块。**auto-wiki 只会加载一个。如果你需
要更丰富的 governance，应该扩展你选择的那一个，而不是堆两个。
