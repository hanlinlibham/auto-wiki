# Lint 协议

> Lint 不只是检查问题，更重要的是**治理**——合并、归档、修复。防止 wiki 变成信息坟场。

## 流程

```
1. 扫描全部页面
   ├─ 读 meta.yaml 获取 wiki 基本信息
   ├─ 读 index.md 获取页面列表
   ├─ 遍历 sources/ entities/ concepts/ analyses/ 目录
   └─ 对比 index 与实际文件（发现 index 遗漏或多余的条目）

2. 逐项检查（7 项）
   ├─ 2.1 Validation — 页面格式是否合规
   ├─ 2.2 Contradiction — 不同页面之间是否有矛盾
   ├─ 2.3 Duplication — 是否有重复页面
   ├─ 2.4 Orphan — 是否有孤立页面
   ├─ 2.5 Broken Link — 是否有断链
   ├─ 2.6 Staleness — 是否有过时内容
   └─ 2.7 Coverage — 知识覆盖是否有明显缺口

3. 执行修复（自动 + 需确认）
   ├─ 自动修复：index 同步、断链修复、格式补全
   └─ 需确认：合并重复、归档过时、矛盾标注

4. 输出健康报告
5. 更新 meta.yaml 统计
6. 追加 log.md
```

## 两档执行

Lint 分两档。结构化检查可以自动跑完全量页面，语义检查需要 Agent 逐页理解内容，代价随页面数线性增长。

| 档位 | 包含检查项 | 执行方式 | 代价 |
|------|-----------|---------|------|
| **结构档**（必跑） | Validation, Orphan, Broken Link, Staleness | 全量扫描，确定性输出 | O(N) 文件读取 |
| **语义档**（按需） | Contradiction, Duplication, Coverage | Agent 抽样或用户指定范围 | O(N²) 语义比较 |

**默认行为**：`lint` 只跑结构档。用户说"深度 lint"或"检查矛盾"时跑语义档。

**语义档的范围控制**：
- wiki < 50 页：全量扫描
- wiki 50-200 页：只扫最近 30 天内 ingest 触及的页面 + 其关联页面
- wiki > 200 页：用户必须指定范围（如"检查 entities/ 下的矛盾"）

---

## 7 项检查细则

### 2.1 Validation（格式校验）— 结构档

按 wiki-format.md 的 Validation Rules 检查每个页面：

| 规则 | 自动修复？ |
|------|-----------|
| frontmatter 缺字段 | 是 — 补充默认值（type=entity, confidence=medium） |
| type 值非法 | 否 — 报告，等用户确认 |
| sources 为空（非 source 类型） | 否 — 报告，建议关联 |
| slug 与文件名不一致 | 否 — 报告 |
| 日期格式错误 | 是 — 尝试自动修正 |

### 2.2 Contradiction（矛盾检测）— 语义档

扫描实体页和概念页，检查：
- 同一事实在不同页面有不同数值/结论
- 同一实体页内有 `contested` 标注——检查是否有新 source 可以解决

```
发现矛盾：
- alpha-corp.md 说管理规模 1200 亿（来源：2026-policy-doc）
- industry-overview.md 说某机构市场份额对应约 1000 亿（来源：industry-report-2025）
→ 标注两个页面 confidence → contested
```

### 2.3 Duplication（重复检测）— 语义档

检查是否有两个页面描述同一个实体/概念：
- 文件名相似（如 `alpha-corp.md` 和 `alpha-annuity.md`）
- 标题相似
- 正文内容重叠度高

**处理**：合并为一个页面，保留更完整的版本，将另一个的独有信息合并进来。需用户确认。

### 2.4 Orphan（孤页检测）— 结构档

页面没有任何入链（没有别的页面通过 `[[slug]]` 引用它）。

**处理**：
1. 检查是否有应该引用它的页面 → 是 → 添加 wikilink
2. 仍然无关联 → 建议归档或删除

### 2.5 Broken Link（断链检测）— 结构档

页面中有 `[[slug]]` 但对应文件不存在。

**处理**：
1. 如果能推断应该是哪个页面（slug 拼写接近）→ 修正 wikilink
2. 否则 → 创建 stub 页面（只有 frontmatter + "待补充"），或移除断链

### 2.6 Staleness（过时检测）— 结构档

| 条件 | 判定 |
|------|------|
| 页面 `updated` 距今 > 6 个月，且 confidence ≤ medium | 过时候选 |
| 页面的所有 sources 都 > 12 个月 | 过时候选 |
| 页面 confidence 为 low 且从未被 ingest 强化过 | 过时候选 |

**处理**：标注"待验证"或建议归档。不自动删除。

### 2.7 Coverage（覆盖度评估）— 语义档

不是找错误，而是找缺口：
- 某个实体被 5 个其他页面引用，但自身内容很薄（< 100 字）→ 建议深化
- 某个类型（如 concepts/）页面很少，但 entities/ 页面很多 → 建议提炼概念
- source 页面多但 analysis 页面少 → 建议做综合分析

## 健康报告格式

```
## Wiki 健康报告：{主题名}
生成时间：{日期}

### 概况
- 页面总数：42（sources: 12, entities: 15, concepts: 10, analyses: 5）
- 健康度：良好 / 需要关注 / 需要干预
- confidence 分布：high 30 / medium 8 / low 2 / contested 2

### 本次修复
- [自动] index.md 同步（新增 2 个遗漏条目）
- [自动] 修复 1 个断链（portable-annuity → portable-annuity-scheme）
- [需确认] 合并 alpha-corp.md 和 alpha-annuity.md（疑似重复）

### 待处理问题
- 矛盾：2 处（列出具体页面和矛盾点）
- 过时：1 页建议归档（portfolio-category，6 个月未更新）

### 覆盖度建议
- entities/beta-corp.md 内容较薄（仅 50 字），被 4 个页面引用，建议 ingest 更多材料
- concepts/ 只有 10 页，而 entities/ 有 15 页，建议提炼更多概念页

### 统计
- 最活跃 source：hrss-2026-policy（被 8 个页面引用）
- 最孤立 entity：portfolio-category（0 个入链）
- 最近 ingest：2026-04-06（3 天前）
```
