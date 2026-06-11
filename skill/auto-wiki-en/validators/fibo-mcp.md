# FIBO MCP: Runtime Logic Validator

> External validator that checks the logical structure of wiki knowledge via SPARQL queries against the FIBO ontology (627K inferred triples).
> Optional enhancement — when unreachable, lint degrades to schema.py format validation + static seed rules.
>
> Based on [NeuroFusionAI/fibo-mcp](https://github.com/NeuroFusionAI/fibo-mcp) (MIT), which materializes the FIBO ontology into a queryable MCP SPARQL endpoint.

## Service Info

| Item | Value |
|----|-----|
| Endpoint (registered as `fibo-mcp` in the project-level `.mcp.json`) | `http://39.96.218.64:8113/mcp` ← currently available |
| Backup mirror | `https://mcp.ablemind.cc/fibomcp/mcp` (Cloudflare; origin returned 522, unreachable as tested 2026-06) |
| Protocol | MCP Streamable HTTP (`initialize` automatically obtains `Mcp-Session-Id`) |
| Service version | FIBO 3.3.1 |
| Tools | `sparql` (SPARQL queries), `inspect` (class/property details) |
| Data size | 627,712 triples (including OWL-RL inference materialization) |

> **Coverage (tested 2026-06)**: FIBO covers financial entities / securities / interest rates / legal entities / pensions, etc. For the domains in this repo:
> - **macro domain = partial coverage**: central bank / government bond / interest rate / repurchase agreement are covered; monetary policy / lending facility (MLF/SLF) / interest rate corridor are not (central-bank operating tools are not in FIBO).
> - **annuity domain = high coverage**: trustee / custodian / pension fund / fund manager — FIBO's home turf, see `seeds/fibo-pensions.md`.
> Therefore FIBO validation **only checks the permanent skeleton (T3 entities/relations, T5 types)**, never the time-varying layers (T0 values / T1 states / T2 logic / T4 events).

## How to Call

Send a `tools/call` request over the MCP protocol with tool name = `sparql` and the SPARQL query string as the argument.
First `initialize` to obtain an `Mcp-Session-Id`, then attach that header to subsequent requests.

> **No user credentials needed**: `Mcp-Session-Id` is the standard session identifier of the MCP Streamable HTTP transport (similar to an HTTP session). The Agent obtains it automatically by calling `initialize`; no API key or other secret is required from the user. The endpoint is a public read-only SPARQL query service.

## Three Levels of Validation

schema.py validates page format (are frontmatter fields present, are types correct).
FIBO SPARQL validates knowledge logic — at three levels:

### 1. Logical pathway: is a relation's domain/range legal?

The Agent wrote a relation — is that relation legal in the standard ontology?

**Query template**: given a property name, look up its domain and range.

```sparql
SELECT DISTINCT ?domainLabel ?rangeLabel WHERE {
  ?prop rdfs:label ?propLabel .
  FILTER(CONTAINS(LCASE(STR(?propLabel)), "{property_name}"))
  ?prop rdfs:domain ?domain . ?domain rdfs:label ?domainLabel .
  ?prop rdfs:range ?range . ?range rdfs:label ?rangeLabel .
}
```

**Example** (using `has trustee`, verified 2026-04-07):

| domain | range |
|--------|-------|
| business entity | trustee |
| trust | trustee |
| trust | controlling party |

-> If the Agent writes `PensionProduct --hasTrustee--> X`, the logical pathway is illegal: PensionProduct is not in the domain.

### 2. Conditional edges: relations required for an entity to hold

The Agent created an entity page — which relations are mandatory?

**Query template**: given a class URI, look up its OWL restrictions.

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

`someValuesFrom` = entities of this class **must** have this relation (at least one).
`allValuesFrom` = the relation's values **can only** be of the specified type.

### 3. Type hierarchy: is the entity classified correctly?

The Agent tagged an entity with some type — does it exist in the standard ontology?

**Query template**: fuzzy-search class names.

```sparql
SELECT DISTINCT ?label ?def WHERE {
  ?class rdfs:label ?label .
  FILTER(CONTAINS(LCASE(STR(?label)), "{keyword}"))
  OPTIONAL { ?class <http://www.w3.org/2004/02/skos/core#definition> ?def }
}
```

If nothing is found, validation should prompt: "This type is not in the standard ontology; please double-check the naming."

## Integration

Does not change the Skill's core flow; acts as an optional enhancement layer of lint:

```
lint → schema.py format validation
     → external validator (if meta.yaml declares a validator and it is reachable)
       ├─ Logical pathway: does the relation type's domain/range match
       ├─ Conditional edges: are required relations (someValuesFrom) missing
       └─ Type hierarchy: is the entity type in the standard ontology
     → health report
```

## Principles

- Never hard-code FIBO constraints into schema.py — it is an external reference, not an internal rule
- Never require wiki pages to satisfy every OWL constraint — just report what is missing; the Agent decides whether to fill it in
- Never block at ingest time — logic validation runs only at lint; ingest prioritizes speed
- Skip silently when the service is unreachable — note in the health report that "external validator unreachable, skipped"
