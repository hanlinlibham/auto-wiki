# Source Validation

## Source Credibility Grading

Every piece of information is tagged with a source type; each type maps to a default confidence:

| Source Type | Tag | Default confidence | Description |
|-------------|-----|--------------------|-------------|
| Primary source | `[primary]` | high | The subject's own writings, official documents, raw data, meetings attended in person |
| Authoritative secondary | `[authoritative-secondary]` | high | Reports by authoritative media, academic papers, regulator releases |
| Regular secondary | `[secondary]` | medium | Industry research reports, analysis articles, third-party compilations |
| Hearsay | `[hearsay]` | low | Reprocessed content, social media discussion, information with no stated source |
| Inference | `[inference]` | low | Conclusions derived by the Agent or the user from existing information |
| Oral | `[oral]` | medium | User's verbal account, meeting notes, unrecorded conversations |

### Tagging in Source Summary Pages

```markdown
---
title: New Labor Department Pension Rules
type: source
source_type: primary           # Source type
source_origin: Department of Labor official website   # Source origin
source_date: 2026-04-01        # Date of the original material
source_url: ""                 # Source URL (if any)
---

## Key Information

- [primary] New pension portability rules released...
- [primary] Trustee admission threshold raised to...
```

### Tagging in Entity/Concept Pages

When citing sources of differing credibility, tag them in the body:

```markdown
## Assets Under Management

As of end-2025, AUM reached 120 billion. [primary] (Source: [[2026-04-06-policy-doc]])

Market ranking roughly 3rd. [secondary] (Source: [[2025-industry-report]], unofficial data)
```

## Source Blacklist

The following channels are never used as standalone sources (they may serve as leads but are not cited):

| Channel | Reason |
|---------|--------|
| Content-mill Q&A and answer-aggregation sites | Heavy content rehashing, high distortion rate |
| Random blogs / unattributed Substack & Medium newsletters | Unverifiable, dominated by second-hand retelling |
| Wiki mirrors and SEO content-farm encyclopedias | Stale and unreliable information |
| Aggregated content with no stated source | Untraceable, unauditable |

**Acceptable channels**: Reuters, Bloomberg, Financial Times, The Wall Street Journal, The Economist, MIT Technology Review, Ars Technica, peer-reviewed journals, regulator official websites, listed-company filings and announcements.

## Tool Dependency Check

### Environment Check on First Use

On its first ingest run, the Agent checks which tools are available in the user's environment:

```
┌─────────────────────────────────────────────────────────┐
│ Knowledge Compiler · Environment Check                   │
│                                                          │
│  File I/O      — can create and edit wiki pages          │
│  Local search  — can grep wiki content                   │
│                                                          │
│  The following capabilities depend on your setup:        │
│ {?} Web search — needs WebSearch tool or a search MCP    │
│ {?} Web fetch  — needs WebFetch tool                     │
│ {?} PDF read   — needs Agent PDF support (Claude Code)   │
│ {?} Domain data — needs a data MCP for the domain        │
│                                                          │
│  Current modes:                                          │
│ • User provides source files →  always available         │
│ • Agent searches autonomously → needs search tools       │
└─────────────────────────────────────────────────────────┘
```

### Two Work Modes

| Mode | Required Tools | Description |
|------|----------------|-------------|
| **Passive mode** | File I/O only | The user provides source files, the Agent compiles them into the wiki. Zero dependencies |
| **Active mode** | Search + web fetch | The Agent searches for information autonomously, then ingests. Requires MCP/WebSearch |

**The Skill defaults to passive mode** — the user drops files in, the Agent compiles. It assumes no search tooling on the user's side.

**When the user says "research XX for me" but provides no source files**:

```
Agent: How would you like me to obtain the materials?

1. You provide files/text → I compile them directly (recommended)
2. I search autonomously → I need to confirm you have:
   - WebSearch or a search-type MCP tool
   - WebFetch (to read web content)
   Without these, I cannot obtain materials on my own.
```

### Search Tool Adaptation

If the user has search tools, the Agent's ingest flow extends to:

```
1. Draw up a search plan for the research topic (what to search, where to search)
2. Run the searches and collect a candidate source list
3. Grade sources by credibility; read primary/authoritative sources first
4. Run the standard ingest flow on every source worth keeping
5. Record the search keywords and the filtering process in the source summary page
```

**Key principle: search is a means of obtaining source files; it does not change ingest's core logic (read the old, compare the new, revise the old).**

### Tagging Deep-Dive Search Sources

When a source was obtained by the deep-dive pipeline's automated search, the source summary page must record extra deep-dive metadata:

```yaml
---
title: Alpha Corp 2025 Annual Report Summary
type: source
source_type: secondary     # Graded on its own merits — not changed by how it was found
source_origin: Reuters
source_date: 2025-06-15
source_url: "https://..."
deep_dive_meta:            # deep-dive-specific fields
  search_query: "Alpha Corp pension annual report 2025"
  gap_filled: "single_source:alpha-corp"
  search_date: 2026-04-09
---
```

**Confidence ceiling rules**:
- Search-obtained sources have a confidence ceiling of medium, unless the source qualifies as "primary" or "authoritative-secondary"
- When multiple search sources corroborate the same conclusion, confidence may rise to high
- A source's source_type is still graded by the standard criteria — never altered by how it was acquired (search vs user-provided)
