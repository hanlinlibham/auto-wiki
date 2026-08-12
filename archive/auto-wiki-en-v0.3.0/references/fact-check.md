# Data Validation Protocol

> Prevent erroneous data from polluting the wiki. Verifiable data must be verified; unverifiable data must be labeled.

## Core Principle

**The wiki is a knowledge asset, not a trash bin.** Once erroneous data enters the wiki, subsequent queries cite it and other ingests treat it as an "existing conclusion" to compare against — errors compound. The gate must be at the entrance.

## When to Validate

Insert a validation step in the ingest flow, **after reading the source file and before writing to the wiki**:

```
Read source file → extract key claims
    ↓
Classify: verifiable vs unverifiable
    ↓
Verifiable → cross-validate with tools → pass / fail / unable to verify
    ↓
Write to wiki (with validation labels)
```

## Identifying Verifiable Data

The following claim types should be validated where possible. **Which tool to use depends on the MCPs/tools available in the user's environment** — the table below is a common mapping, not a hard requirement:

| Data type | Example | Common validation tools (environment-dependent) |
|---------|------|--------------------------|
| Listed-company financials | Revenue, net profit, ROE | Financial data MCP (e.g. tushare, ifind, wind) |
| Fund / annuity scale | AUM, shares | Financial data MCP |
| Macro indicators | GDP, CPI, PMI | Financial data MCP |
| Regulatory document numbers | MOHRSS Doc. [2026] No. XX | WebSearch |
| Basic company info | Founding date, registered capital, legal representative | Financial data MCP / WebSearch |
| Industry statistics | Market size, growth rate, share | WebSearch / industry data MCP |
| Dates and events | "Released in March 2026" | WebSearch |

**Tool discovery**: on the first ingest, the agent confirms available tools via the environment check (see `source-validation.md`). When no matching tool exists, that data type is labeled `verified: false` without blocking the ingest.

**Unverifiable claims**: opinions, analysis, forecasts, inferences, subjective judgments. These skip validation and are labeled per the source grading in source-validation.md.

## Validation Flow

### Step 1: Extract verifiable claims

From the source file, identify factual claims containing specific numbers, dates, or document numbers:

```
Source text:
"By the end of 2024, China's enterprise annuity funds reached a cumulative RMB 3.2 trillion, covering 128,000 enterprises"

Extract 2 verifiable claims:
- Claim A: cumulative enterprise annuity scale of RMB 3.2 trillion (as of end-2024)
- Claim B: 128,000 enterprises covered (as of end-2024)
```

### Step 2: Attempt verification

Use available tools in priority order:

```
1. Specialized data MCP (e.g. finance, healthcare, legal domain data interfaces): interface exists → query directly
2. WebSearch: search for officially published figures for the same period
3. Wiki-internal cross-check: see whether other wiki pages hold related data
4. No tool available: skip, label unverified
```

### Step 3: Adjudicate the result

| Result | Handling | frontmatter label |
|------|------|-----------------|
| **verified** — tool returns matching data (deviation < 5%) | Ingest normally | `verified: true` |
| **disputed** — tool returns conflicting data | **Pause**, show the discrepancy, let the user decide | After user confirmation, label `verified: user-confirmed` |
| **unverifiable** — no tool, or the data source lacks coverage | Ingest normally | `verified: false` |
| **partial** — some claims verified, some not | Label item by item | Mixed labels |

### User interaction on disputed

The example below uses the finance domain; in real runs, substitute the user's target domain and tools:

```
 Data validation found a discrepancy:

Claim: "The XX fund reached a cumulative scale of RMB 3.2 trillion (end-2024)"
Data-tool query result: RMB 3.58 trillion (end-2024)
Deviation: -10.6%

Possible causes:
- The source file's figure is wrong
- Different statistical scopes
- The data tool lags in updates

Please choose:
1. Use the tool-verified figure (3.58 trillion) → replace the source figure, then ingest
2. Use the source-file figure (3.2 trillion) → label user-confirmed, then ingest
3. Record both → ingest as contested
4. Drop this item → skip the claim
```

## Validation Labels in Pages

Mark verification status in entity/concept pages:

```markdown
## Fund Scale

By the end of 2024, the XX fund reached a cumulative RMB 3.58 trillion.
 verified (data-tool query, 2025-01-15)
(Source: [[2026-04-06-source-doc]]; original figure 3.2 trillion, corrected via tool)

## History

- ~~Cumulative scale RMB 3.2 trillion~~ (source: [[2026-04-06-source-doc]] original text, tool-corrected to 3.58 trillion)
```

## Tool Availability

| Scenario | With tools | Without tools |
|------|---------|---------|
| Specialized domain data | Auto-verified via the matching MCP | Label unverified, suggest manual confirmation by the user |
| Public information | Cross-validated via WebSearch | Label unverified |
| Internal data (verbal / meetings) | Cannot be verified | Label source_type: oral, confidence: medium |

**In passive mode (no search tools)**: all data is labeled `verified: false`, relying on the source grading in source-validation.md as the credibility reference. Ingest is never blocked, but every figure carries an "unverified" annotation.

## Relationship to ingest-protocol

Validation slots in between Step 1 and Step 2 of ingest-protocol.md:

```
Step 1: Read the source file, extract key information
Step 1.5: [Data validation] extract verifiable claims → cross-validate with tools → adjudicate
Step 2: Search the existing wiki
Step 3: Compare old vs new page by page
...
```

If Step 1.5 finds disputed data and pauses, Step 2 resumes only after user confirmation.
