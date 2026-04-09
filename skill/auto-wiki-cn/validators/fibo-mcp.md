# FIBO MCP：运行时逻辑校验器

> 外部校验器，通过 SPARQL 查询 FIBO 本体（627K 推理三元组）校验 wiki 中知识的逻辑结构。
> 可选增强——不可达时 lint 退化为 schema.py 格式校验 + 种子静态规则。
>
> 基于 [NeuroFusionAI/fibo-mcp](https://github.com/NeuroFusionAI/fibo-mcp)（MIT），将 FIBO 本体物化为可查询的 MCP SPARQL 端点。

## 服务信息

| 项 | 值 |
|----|-----|
| 端点 | `https://mcp.ablemind.cc/fibomcp/mcp` |
| 协议 | MCP Streamable HTTP（需 `Mcp-Session-Id`），HTTPS via Cloudflare |
| 工具 | 仅 `sparql`（无 search） |
| 数据规模 | 627,712 triples（含 OWL-RL 推理物化） |

## 调用方式

通过 MCP 协议发送 `tools/call` 请求，tool name = `sparql`，参数为 SPARQL 查询字符串。
需要先 `initialize` 获取 `Mcp-Session-Id`，后续请求带上该 header。

> **无需用户凭证**：`Mcp-Session-Id` 是 MCP Streamable HTTP 传输层的标准会话标识（类似 HTTP Session），由 Agent 调用 `initialize` 时自动获取，不需要用户配置 API key 或任何密钥。该端点为公开只读 SPARQL 查询服务。

## 校验的三个层次

schema.py 校验页面格式（frontmatter 字段有没有、类型对不对）。
FIBO SPARQL 校验知识逻辑——三个层次：

### 1. 逻辑通路：关系的 domain/range 是否合法

Agent 写了一条关系，这条关系在标准本体中合法吗？

**查询模板**：给定一个属性名，查其 domain 和 range。

```sparql
SELECT DISTINCT ?domainLabel ?rangeLabel WHERE {
  ?prop rdfs:label ?propLabel .
  FILTER(CONTAINS(LCASE(STR(?propLabel)), "{property_name}"))
  ?prop rdfs:domain ?domain . ?domain rdfs:label ?domainLabel .
  ?prop rdfs:range ?range . ?range rdfs:label ?rangeLabel .
}
```

**示例**（以 `has trustee` 为例，2026-04-07 验证）：

| domain | range |
|--------|-------|
| business entity | trustee |
| trust | trustee |
| trust | controlling party |

-> 如果 Agent 写 `PensionProduct --hasTrustee--> X`，逻辑通路不合法：PensionProduct 不在 domain 中。

### 2. 条件边：实体成立的必要关系

Agent 创建了一个实体页面，需要哪些必要关系？

**查询模板**：给定一个类的 URI，查其 OWL 约束。

```sparql
SELECT DISTINCT ?onPropLabel ?restrictType ?valueLabel WHERE {
  <{class_uri}> rdfs:subClassOf ?r .
  { ?r owl:onProperty ?p . ?p rdfs:label ?onPropLabel .
    ?r owl:someValuesFrom ?v . ?v rdfs:label ?valueLabel .
    BIND("someValuesFrom" AS ?restrictType) }
  UNION
  { ?r owl:onProperty ?p . ?p rdfs:label ?onPropLabel .
    ?r owl:allValuesFrom ?v . ?v rdfs:label ?valueLabel .
    BIND("allValuesFrom" AS ?restrictType) }
}
```

`someValuesFrom` = 该类实体**必须**存在此关系（至少一个）。
`allValuesFrom` = 该关系的值**只能**是指定类型。

### 3. 类型层级：实体归类是否正确

Agent 把实体标记为某个类型，标准本体中有没有？

**查询模板**：模糊搜索类名。

```sparql
SELECT DISTINCT ?label ?def WHERE {
  ?class rdfs:label ?label .
  FILTER(CONTAINS(LCASE(STR(?label)), "{keyword}"))
  OPTIONAL { ?class <http://www.w3.org/2004/02/skos/core#definition> ?def }
}
```

如果搜不到，校验应提示："该类型不在标准本体中，请确认命名"。

## 集成方式

不改 Skill 核心流程，作为 lint 的可选增强层：

```
lint → schema.py 格式校验
     → 外部校验器（如果 meta.yaml 声明了 validator 且可达）
       ├─ 逻辑通路：relation type 的 domain/range 是否匹配
       ├─ 条件边：必要关系（someValuesFrom）是否缺失
       └─ 类型层级：实体类型是否在标准本体中
     → 健康报告
```

## 原则

- 不把 FIBO 约束硬编码进 schema.py——外部参考，不是内部规则
- 不要求 wiki 页面完全满足所有 OWL 约束——报告缺失即可，Agent 判断是否补充
- 不在 ingest 时阻塞——逻辑校验只在 lint 时运行，ingest 优先保证速度
- 服务不可达时静默跳过——在健康报告中注明"外部校验器不可达，已跳过"
