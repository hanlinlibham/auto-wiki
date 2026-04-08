# Why Compilation, Not RAG

> This document explains the design philosophy behind auto-wiki.
> It is not read by the Agent — it is for humans considering whether to use or contribute to this project.

## The RAG Ceiling

RAG (Retrieval-Augmented Generation) solves one problem well: finding relevant chunks from a document collection at query time. But it has a fundamental limitation — **it doesn't learn**.

Every query re-derives its answer from raw documents. There is no accumulation. Ask a subtle question that requires synthesizing five documents, and the LLM has to find and piece together the relevant fragments every time. Nothing is built up.

This is the difference between a student who re-reads their textbook every time they're asked a question, versus one who has been building notes, connecting concepts, and refining their understanding over months.

## Compilation as an Alternative

auto-wiki takes a different approach: **the agent compiles knowledge once and keeps it current**.

When a new source document arrives, the agent doesn't just index it for later retrieval. It:

1. **Reads** the source and extracts key information
2. **Searches** its existing wiki for related pages
3. **Compares** new information against old, page by page
4. **Decides** for each conflict: reinforce, update, or mark as contested
5. **Writes** the result — updating existing pages, creating new ones, recording the history

The wiki is the persistent artifact. The cross-references are already there. The contradictions have already been flagged. The synthesis already reflects everything the agent has read.

## The Three-Way Comparison

The core of the compilation model is the three-way comparison at ingest time:

| New vs Old | Decision | Rationale |
|-----------|----------|-----------|
| Consistent | **Reinforce** — add citation, raise confidence | More sources agreeing = higher trust |
| Newer/better source | **Update** — rewrite, archive old in history | Knowledge evolves, old conclusions become historical record |
| Contradictory, can't resolve | **Conflict** — keep both, mark `contested` | Don't force resolution; let evidence accumulate |

This is deliberately not a merge strategy. The agent never "reconciles" contradictions — it presents them. This preserves the integrity of the knowledge base and surfaces genuinely contested points for human judgment.

## What This Enables

With a compiled wiki, the agent can:

- **Answer questions from accumulated knowledge**, not just retrieved fragments
- **Cite specific pages** with their provenance chain (source → page → conclusion)
- **Identify gaps** — "the wiki has 3 sources on X but nothing on Y, suggest ingesting more on Y"
- **Track evolution** — "this number was 800 in December, updated to 1200 in March, source changed from report A to report B"
- **Detect contradictions** across sources that were ingested weeks apart

None of this is possible with RAG alone. RAG retrieves; compilation accumulates.

## Trade-offs

Compilation is not free:

| Trade-off | RAG | Compilation |
|-----------|-----|-------------|
| Latency at ingest | Near-zero (just index) | Minutes (read, compare, write) |
| Latency at query | Retrieval + synthesis | Fast (read pre-compiled pages) |
| Correctness | Re-derives every time (fresh but expensive) | Pre-compiled (fast but may be stale) |
| Contradiction handling | Implicit (different chunks may disagree) | Explicit (marked `contested`) |
| Knowledge decay | None (raw docs are immutable) | Possible (wiki may drift from sources) |

The lint operation exists specifically to address knowledge decay — periodic health checks catch staleness, orphaned pages, and unresolved contradictions.

## When Not to Use This

- **One-off questions** that don't benefit from accumulation
- **Rapidly changing data** where compilation can't keep up (use real-time APIs instead)
- **Very large document collections** (>500 pages) — beyond this scale, consider migrating to a proper database with vector search
- **Multi-user collaboration** — auto-wiki is designed for one agent, one wiki
