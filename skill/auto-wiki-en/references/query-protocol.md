# Query Protocol

> Answer questions from accumulated wiki knowledge. This is not RAG — we do not search raw documents, we search compiled wiki pages.

## Flow

```
1. Understand the question
   ├─ Identify the target wiki (inferred from the question, or user-specified)
   ├─ Extract keywords (entity names, concept names, time ranges)
   └─ Determine the question type (fact lookup / comparative analysis / trend judgment / open exploration)

2. Search the wiki
   ├─ Read the hub page ({Domain Name}.md) and match page titles and descriptions against the keywords
   ├─ Read the matched pages (usually 3-8)
   ├─ If a page contains [[wikilink]]s, follow them to read linked pages (one level of expansion)
   └─ Watch the confidence field: contested pages require explicit labeling

3. Synthesize the answer
   ├─ Synthesize from the content of the pages read
   ├─ Tag every key claim with its source page: [[page-slug]]
   ├─ If contested information is involved, state it explicitly:
   │   "On XX, the wiki contains a contradiction: source A says..., source B says..."
   └─ If information is insufficient, state the gap explicitly and suggest ingest directions

4. Optional archiving
   ├─ If the answer contains valuable new analysis (not a simple restatement of page content)
   ├─ Prompt the user: "Should this analysis be archived to the wiki?"
   └─ User agrees → write to analyses/{slug}.md and update the hub page
```

## Response Format

### Fact Lookup

```
Based on {N} source files accumulated in the wiki:

{Direct answer}

Sources: [[page-1]], [[page-2]]
```

### Comparative Analysis

```
Based on the wiki's records, comparing {A} and {B}:

| Dimension | {A} | {B} |
|-----------|-----|-----|
| ... | ... | ... |

Sources: [[page-1]], [[page-2]], [[page-3]]

Note: On dimension XX, wiki data is limited (only 1 source); supplementing is recommended.
```

### Insufficient Information

```
The wiki's information on {topic} is insufficient:
- Related pages: {N}
- Source files: {N}
- Gap: {what specifically is missing}

Suggested ingest:
- {suggested material type 1}
- {suggested material type 2}
```

## Cross-Wiki Query

When a question spans multiple wikis:

1. List all wiki directories under `wiki/`
2. Read the hub page of every potentially relevant wiki
3. Search each separately
4. When synthesizing the answer, tag which wiki each source belongs to:

```
Synthesizing across the enterprise-annuity wiki and the charlie-munger wiki:

{Analysis}

Sources:
- enterprise-annuity: [[alpha-corp]], [[fiduciary-responsibility]]
- charlie-munger: [[circle-of-competence]], [[margin-of-safety]]
```

## Query Performance

| Wiki Size | Query Strategy | Expected Latency |
|-----------|----------------|------------------|
| < 30 pages | Read hub page + read matched pages directly | Fast (< 5s) |
| 30-150 pages | Read hub page + grep keywords + read top matches | Medium (5-15s) |
| 150-500 pages | Read hub page + grep + batched reads | Slow (15-30s) |
| > 500 pages | Beyond the Skill's design scope | Suggest migrating to a platform |
