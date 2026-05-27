# Governance Module — `ontology-mem`

> Route-before-store + 5-rule conflict detector + append-only ledger,
> backed by SQLite, addressable via MCP.

This is the first concrete governance plugin for auto-wiki. It
applies the Ontology-Mem governance protocol
([`docs/spec-phase1.md`](https://github.com/abuttoncc/Ontology-Mem/blob/main/docs/spec-phase1.md))
between auto-wiki's candidate extraction and the wiki write step.

## When to use it

Pick `ontology-mem` when **wrong long-term memory has real downstream
cost**:

- Finance — wrong metric scope (归母 vs 合并 净利润) corrupts every
  future answer
- Healthcare / regulated industries — agent paraphrase mixed with
  source material erodes the audit trail
- Multi-user shared wikis — agent-coined inferences silently
  overwriting each user's intent
- Long-horizon research where you'll re-query a year later and need
  to trust the wiki

Skip it for exploratory single-user wikis where re-deriving from
sources is cheap. Auto-wiki's default ingest protocol is already
useful without governance.

## Enable

```yaml
# wiki/{topic}/meta.yaml
name: personal-pension
ontology_type: domain
seed: fibo-pensions
governance: ontology-mem
```

## Runtime requirement

`ontology-mem` runs as an MCP server. The agent must have it wired
in its MCP config:

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

Install with `pip install ontology-mem[mcp]`. The DB file is one per
topic — auto-wiki agents already keep one directory per topic, so the
file slots in naturally.

## Storage layout

When governance is enabled, the topic directory gains one file:

```
wiki/personal-pension/
├── meta.yaml              # declares governance: ontology-mem
├── index.md
├── data.db                # auto-wiki structured data (unchanged)
├── governance.db          # ★ NEW: ontology-mem store + ledger
├── log.md
├── sources/  entities/  concepts/  analyses/
```

`governance.db` holds the candidate review queue, conflict verdicts,
and the append-only event ledger. The Markdown layer (`entities/`,
`concepts/`, …) is unchanged in shape — only the path through which
new content lands changes.

## What the module decides

Auto-wiki extracts candidates from a source (entities, concepts,
facts, claims). For each candidate, `ontology-mem` returns one of:

| Verdict | What it means | Auto-wiki action |
|---|---|---|
| `verified` (status) on `memory` / `fact` / `evidence` route | Deterministic gate passed at confidence ≥ 0.6, no conflict | Proceed to write into the wiki layer as normal |
| `conflict_checked` on `ontology` route | Conflict detector ran; verdict attached | Surface as review card; do NOT write until human acts |
| `needs_review` | Low confidence or origin_role=agent | Surface as review card; do NOT write |
| `rejected` (status) — route was `discard` | Out-of-domain / empty | Log only; no wiki change |

The route taxonomy (`ontology` / `fact` / `evidence` / `memory` /
`needs_review` / `discard`) maps cleanly onto auto-wiki's existing
page types:

| ontology-mem route | Auto-wiki destination |
|---|---|
| `ontology` (concept-shaped, stable) | `concepts/{slug}.md` after verify |
| `fact` (period + numeric) | `data.db` `data_points` table |
| `evidence` (quote, citation) | `sources/{date}-{slug}.md` |
| `memory` (preference, convention) | `concepts/{slug}.md` with `kind=methodology` |
| `needs_review` | Hold in governance queue, surface card |
| `discard` | Ledger only |

## origin_role mapping

Auto-wiki must set `origin_role` on every candidate it submits:

| Auto-wiki source | `origin_role` |
|---|---|
| User-provided file content (verbatim extract) | `extractor` |
| User-typed text in chat | `user` |
| Agent inference / paraphrase from source | `agent` |
| auto-wiki internal (e.g., schema audit fix) | `system` |

The single most consequential rule: candidates with
`origin_role=agent` cannot auto-route to `memory` or `fact` — they
**always** go to `needs_review` regardless of confidence. This is
ontology-mem's headline differentiator and is non-negotiable when
the module is loaded.

## Ingest hook (called from `ingest-protocol.md` § Governance Hook)

```pseudocode
function ingest_with_ontology_mem_governance(source_file):
    candidates = extract_candidates(source_file)   # entities, concepts, facts, evidence

    verified, pending, rejected = [], [], []
    for cand in candidates:
        result = mcp__ontology_mem__ingest_candidate(
            user_id     = current_user_id,
            title       = cand.title,
            content     = cand.content,
            kind        = cand.kind,         # concept | entity | metric | claim | note
            origin_role = cand.origin_role,  # see mapping above
            aliases     = cand.aliases,
            edges       = cand.edges,
        )
        if result.status == "verified":
            verified.append((cand, result))
        elif result.status in ("conflict_checked", "needs_review"):
            pending.append((cand, result))
        elif result.status == "rejected":
            rejected.append((cand, result))

    # ── Standard write path runs only on verified ──
    for cand, result in verified:
        write_to_wiki(cand, result)

    # ── Present review cards for pending ──
    if pending:
        present_review_cards(pending)
        # User can /verify, /reject, /promote inline; each calls back
        # to mcp__ontology_mem__verify / reject / promote.

    # ── Log rejected to wiki log.md (not wiki content) ──
    for cand, result in rejected:
        log_md.append(f"discarded {cand.title}: {result.route_verdict.reasons}")
```

## Review card shape

When `ingest` produces pending items, present them inline in a
compact format:

```
Ingested into {topic} wiki:
  ✓ 8 verified  (6 facts, 2 concepts) — written to wiki
  ⚠ 2 need your eyes:

  ┌─ ⚠ CONFLICT — same_as_conflict ──────────────────────────
  │ Candidate: "trustee_market_share" → A same_as B
  │ Conflict: platform constraint not_same_as(A, B)
  │ Severity: HIGH
  │
  │ [verify --override] [reject "<reason>"] [promote-to-platform]
  └──────────────────────────────────────────────────────────

  ┌─ 💭 NEEDS REVIEW — origin_role=agent ────────────────────
  │ Candidate: "regulation X applies to scenario Y"
  │ Reason: inferred from source §3.2, not direct quote
  │ Route gate downgraded auto-memory to needs_review
  │
  │ [verify "<note>"] [reject "<reason>"] [keep as inference]
  └──────────────────────────────────────────────────────────

  ✗ 1 discarded (out of domain)
```

The bracketed actions are agent-callable: each maps to an MCP tool
on `ontology-mem`. The user can either approve them in-line or defer
to a later `/auto-wiki review` session.

## Recall hook

When recall mode is active on a governance-enabled wiki, every
synthesised answer must include two extras:

1. **Origin badges**: tag each cited claim with `🔵 source`,
   `🟢 your decision`, `💭 agent inference` based on
   `record.candidate.origin_role` and the latest ledger event.
2. **Pending awareness**: before answering, call
   `mcp__ontology_mem__recall_context(query)` which returns:

   ```json
   {
     "verified": [...],
     "needs_review": [...],
     "recent_decisions": [...]
   }
   ```

   If `needs_review` has matching items, the agent must surface them:
   "I also see 3 pending review items mentioning X. Want to review
   them first?"

## Lint hook (optional)

`/auto-wiki lint` can additionally call
`mcp__ontology_mem__list_review_queue` to surface stale review items
in the health report:

```
Wiki Health Report: personal-pension
  ...
  Governance:
    - 12 pending review items (5 needs_review, 7 conflict_checked)
    - Oldest pending: 14 days ago — suggest /auto-wiki review
```

## Deep-dive hook

When `/auto-wiki deep-dive` runs and produces auto-generated
candidates, those candidates **must** carry `origin_role=agent`. The
ontology-mem gate will automatically downgrade them to
`needs_review`, ensuring no auto-generated content lands in the wiki
without a human pass. This is by design — deep-dive is a *proposal
generator*, not a *writer*.

## Failure modes

| Failure | Behavior |
|---|---|
| ontology-mem MCP server not reachable | Auto-wiki must refuse to ingest, not silently fall back to the no-governance path. Loud failure beats silent corruption. |
| `governance.db` corrupted | Re-create from the ledger's event stream (each event is sufficient to replay state). Re-creation guide: [Ontology-Mem § ledger replay](https://github.com/abuttoncc/Ontology-Mem/blob/main/docs/spec-phase1.md). |
| Disagreement between auto-wiki's local view and `governance.db` | `governance.db` wins. The wiki Markdown is the *rendered view* of governance-approved state; if it drifts, regenerate it. |

## What the module does NOT do

To set expectations:

- **No vector retrieval.** The route-before-store gate is
  deterministic (and LLM-fallback for low-confidence). Vector recall
  is the wiki's job, not governance.
- **No vocabulary normalisation.** That's the seed layer's job.
- **No format validation.** That's the validator layer's job.
- **No source verification.** That's `fact-check.md`.

Governance answers exactly one question per candidate: *should this
become canonical*?

## References

- Ontology-Mem repo:
  https://github.com/abuttoncc/Ontology-Mem
- Phase 1 spec:
  https://github.com/abuttoncc/Ontology-Mem/blob/main/docs/spec-phase1.md
- Backagent integration recipe:
  https://github.com/abuttoncc/Ontology-Mem/blob/main/USAGE.md
- License: Apache 2.0
