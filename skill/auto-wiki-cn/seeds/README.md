# 种子配置（Seeds）

种子文件为特定领域的 wiki 提供冷启动词表。存放在本目录，每个领域一个文件。

## 文件格式

```markdown
---
name: my-seed-name              # 唯一标识，meta.yaml 中引用此名
display_name: 显示名称
source: 基于的标准本体名称
url: 标准本体的参考链接
applies_to: 适用的研究领域描述
validator: validators/xxx.md    # 可选，关联的外部校验器
---

# 种子标题

## 词表分类 1

| 标准概念 | 说明 | wiki 中的对应 |
|---------|------|--------------|
| ConceptA | ... | entities/ |
| ConceptB | ... | concepts/ |

## 关系模板

​```
EntityA --relation_type--> EntityB
​```

## 禁混规则

| 容易混淆的概念对 | 区别 |
|----------------|------|
| A ≠ B | 说明 |
```

## 如何引用

在 wiki 的 `meta.yaml` 中设置 `seed` 字段：

```yaml
name: my-research-topic
ontology_type: domain
seed: my-seed-name        # 对应种子文件 frontmatter 中的 name
```

Agent 在首次 ingest 前读取对应的种子文件。

## 编写原则

1. **词表要精简**。只列该领域最核心的 20-50 个概念，不要试图覆盖整个标准
2. **禁混规则是核心价值**。Agent 最容易搞混的概念对，写清楚区别
3. **关系模板要具体**。不要只列关系类型名，要给出 `A --type--> B` 的完整示例
4. **允许中文**。概念名用标准英文，但说明和禁混规则用中文（或目标语言）
5. **声明校验器是可选的**。如果该领域有可用的外部校验器（如 FIBO MCP），在 frontmatter 的 `validator` 字段指向它

## 当前可用种子

| 文件 | 领域 | 概念数 |
|------|------|--------|
| `fibo-pensions.md` | 企业年金/养老金 | ~30 |
