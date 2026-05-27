# Governance 模块 — `ontology-mem`

> Route-before-store + 5 条冲突规则 + append-only ledger，
> SQLite 持久化，MCP 可寻址。

这是 auto-wiki 第一个具体的 governance 插件。它在 auto-wiki 的
candidate 抽取和 wiki 写入之间，插入 Ontology-Mem 的治理协议
([`docs/spec-phase1.md`](https://github.com/abuttoncc/Ontology-Mem/blob/main/docs/spec-phase1.md))。

## 何时用它

当**"长期记忆错了有真实下游成本"**时选 `ontology-mem`：

- 金融 — 指标口径错了（归母 vs 合并净利润）每次后续问答都偏
- 医疗 / 合规 — agent 改写和源材料混在一起会破坏审计链
- 多人共享的 wiki — agent 推断悄悄盖掉每个用户的本意
- 长跨度研究 — 一年后回来查询，需要相信 wiki

探索性单人 wiki 跳过即可——从源重推成本低，auto-wiki 默认 ingest 协议
已经够用了。

## 启用

```yaml
# wiki/{topic}/meta.yaml
name: personal-pension
ontology_type: domain
seed: fibo-pensions
governance: ontology-mem
```

## 运行时要求

`ontology-mem` 以 MCP server 形式运行。agent 必须在自己的 MCP 配置里
挂上：

```json
{
  "mcpServers": {
    "ontology-mem": {
      "command": "python",
      "args": ["-m", "ontology_mem.mcp"],
      "env": {
        "ONTOLOGY_MEM_DB_PATH": "wiki/personal-pension/governance.db"
      }
    }
  }
}
```

`pip install ontology-mem[mcp]` 安装。一个 topic 对应一个 DB 文件 ——
auto-wiki agent 本来就一 topic 一目录，正好。

## 存储布局

启用 governance 后，topic 目录多一个文件：

```
wiki/personal-pension/
├── meta.yaml              # 声明 governance: ontology-mem
├── index.md
├── data.db                # auto-wiki 结构化数据(不变)
├── governance.db          # ★ 新增：ontology-mem store + ledger
├── log.md
├── sources/  entities/  concepts/  analyses/
```

`governance.db` 存 candidate review 队列、冲突判定、append-only 事件
账本。Markdown 层（`entities/`、`concepts/` 等）形状不变 —— 变的只是
**新内容进入 wiki 的路径**。

## 模块给出什么判定

auto-wiki 从源中抽出 candidate（实体、概念、事实、声明）。每个
candidate 由 `ontology-mem` 给出以下之一：

| 判定 | 含义 | auto-wiki 应做的事 |
|---|---|---|
| `verified` (status) + `memory`/`fact`/`evidence` route | 确定性 gate 在 confidence ≥ 0.6 通过，无冲突 | 走标准写入路径进 wiki |
| `conflict_checked` + `ontology` route | 冲突检测器跑过，判定已附 | 显示 review 卡片;**不**写入,等人决定 |
| `needs_review` | 低置信度或 origin_role=agent | 显示 review 卡片;**不**写入 |
| `rejected` (status) + route 为 `discard` | 域外/空 | 仅记日志，无 wiki 改动 |

route 分类（`ontology` / `fact` / `evidence` / `memory` /
`needs_review` / `discard`）干净映射到 auto-wiki 的页面类型：

| ontology-mem route | auto-wiki 目的地 |
|---|---|
| `ontology` (概念形态、稳定) | `concepts/{slug}.md` (verify 后) |
| `fact` (期间 + 数值) | `data.db` `data_points` 表 |
| `evidence` (引用、出处) | `sources/{date}-{slug}.md` |
| `memory` (偏好、约定) | `concepts/{slug}.md` (`kind=methodology`) |
| `needs_review` | 留在 governance 队列，呈现卡片 |
| `discard` | 仅 ledger 记录 |

## origin_role 映射

auto-wiki 必须在提交每个 candidate 时设置 `origin_role`：

| auto-wiki 来源 | `origin_role` |
|---|---|
| 用户提供的文件内容（原文抽取） | `extractor` |
| 用户在对话里直接输入 | `user` |
| agent 从源材料推断 / 改写 | `agent` |
| auto-wiki 内部行为（如 schema 审计修正） | `system` |

**最重要的一条规则**：`origin_role=agent` 的 candidate **不能**自动
路由到 `memory` 或 `fact` —— 不论置信度多高都**强制**走
`needs_review`。这是 ontology-mem 的头牌差异点，加载模块后**不可
关**。

## Ingest 钩子（被 `ingest-protocol.md` § Governance 钩子调用）

```pseudocode
function ingest_with_ontology_mem_governance(source_file):
    candidates = extract_candidates(source_file)   # 实体、概念、事实、引用

    verified, pending, rejected = [], [], []
    for cand in candidates:
        result = mcp__ontology_mem__ingest_candidate(
            user_id     = current_user_id,
            title       = cand.title,
            content     = cand.content,
            kind        = cand.kind,         # concept | entity | metric | claim | note
            origin_role = cand.origin_role,  # 见上表
            aliases     = cand.aliases,
            edges       = cand.edges,
        )
        if result.status == "verified":
            verified.append((cand, result))
        elif result.status in ("conflict_checked", "needs_review"):
            pending.append((cand, result))
        elif result.status == "rejected":
            rejected.append((cand, result))

    # ── 标准写入路径只对 verified 跑 ──
    for cand, result in verified:
        write_to_wiki(cand, result)

    # ── 把 pending 项作为 review 卡片呈现 ──
    if pending:
        present_review_cards(pending)
        # 用户可以 inline /verify、/reject、/promote;
        # 每一个映射到 mcp__ontology_mem__verify/reject/promote 工具。

    # ── rejected 进 log.md(不进 wiki 内容) ──
    for cand, result in rejected:
        log_md.append(f"discarded {cand.title}: {result.route_verdict.reasons}")
```

## Review 卡片样式

当 ingest 产生 pending 项时，inline 用紧凑格式呈现：

```
已 ingest 到 {topic} wiki：
  ✓ 8 已 verify (6 facts, 2 concepts) — 已写入 wiki
  ⚠ 2 需要你看一下：

  ┌─ ⚠ CONFLICT — same_as_conflict ──────────────────────────
  │ 候选: "trustee_market_share" → A same_as B
  │ 冲突: 平台约束 not_same_as(A, B)
  │ 严重度: HIGH
  │
  │ [verify --override] [reject "<reason>"] [promote-to-platform]
  └──────────────────────────────────────────────────────────

  ┌─ 💭 NEEDS REVIEW — origin_role=agent ────────────────────
  │ 候选: "规章 X 适用于场景 Y"
  │ 原因: 从源 §3.2 推断得出,非原文引用
  │ Route gate 把 auto-memory 降级为 needs_review
  │
  │ [verify "<note>"] [reject "<reason>"] [保留为推断]
  └──────────────────────────────────────────────────────────

  ✗ 1 已 discard (域外)
```

方括号里的动作 agent 可以代调用：每个映射到 ontology-mem 的一个 MCP
工具。用户可以 inline 直接批准，也可以延后到一次
`/auto-wiki review` 会话里处理。

## Recall 钩子

当 governance 启用的 wiki 处于 recall 模式时，每次综合答案必须附加两
件事：

1. **来源徽章**：每条引用的结论标注 `🔵 源材料`、`🟢 你的决定`、
   `💭 agent 推断`，依据是 `record.candidate.origin_role` 和最近一次
   ledger 事件。
2. **待审感知**：作答前调用
   `mcp__ontology_mem__recall_context(query)`，它返回：

   ```json
   {
     "verified": [...],
     "needs_review": [...],
     "recent_decisions": [...]
   }
   ```

   如果 `needs_review` 里有匹配项，agent 必须提一句：
   "我看到还有 3 条待审项也提到了 X，要先过一遍吗？"

## Lint 钩子（可选）

`/auto-wiki lint` 可以顺带调
`mcp__ontology_mem__list_review_queue`，把陈旧的待审项纳入健康报告：

```
Wiki 健康报告: personal-pension
  ...
  Governance:
    - 12 项待审 (5 needs_review, 7 conflict_checked)
    - 最早一项已 pending 14 天 — 建议跑一次 /auto-wiki review
```

## Deep-dive 钩子

`/auto-wiki deep-dive` 产生的 auto-生成 candidate **必须**带
`origin_role=agent`。ontology-mem gate 会自动把它们降级为
`needs_review`，确保**没有任何 auto-生成内容在没有人审的情况下落入
wiki**。这是有意为之 —— deep-dive 是*提议生成器*，不是*写手*。

## 失败模式

| 失败情况 | 行为 |
|---|---|
| ontology-mem MCP server 连不上 | auto-wiki **必须**拒绝 ingest，**不**能静默回落到无 governance 路径。响亮失败胜过静默腐败。 |
| `governance.db` 损坏 | 从 ledger 事件流重建（每条事件足以重放状态）。重建指引: [Ontology-Mem § ledger replay](https://github.com/abuttoncc/Ontology-Mem/blob/main/docs/spec-phase1.md) |
| auto-wiki 本地视图与 `governance.db` 不一致 | `governance.db` 为准。wiki Markdown 是 governance-approved 状态的*渲染*；如果漂了，重建它。 |

## 模块**不**做什么

为了校准预期：

- **不做向量检索**。route-before-store gate 是确定性的（低置信度走
  LLM fallback），向量召回是 wiki 自己的事。
- **不做词汇标准化**。那是 seed 层的事。
- **不做格式校验**。那是 validator 层的事。
- **不做信源核实**。那是 `fact-check.md` 的事。

governance 每个 candidate 只回答一个问题：**这条内容是否应该成为
canonical**？

## 引用

- Ontology-Mem 仓库：
  https://github.com/abuttoncc/Ontology-Mem
- Phase 1 spec:
  https://github.com/abuttoncc/Ontology-Mem/blob/main/docs/spec-phase1.md
- Backagent 集成实操：
  https://github.com/abuttoncc/Ontology-Mem/blob/main/USAGE.md
- License: Apache 2.0
