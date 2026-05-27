# Governance Protocol — Extension Point for Pre-Ingest Gating

> Auto-wiki's optional **third** plugin layer. Seeds add vocabulary;
> validators add lint checks; governance modules add *runtime rules
> for what is allowed to become canonical*.

This document defines how auto-wiki integrates with external
governance modules. The first concrete module is
[`ontology-mem`](ontology-mem.md); future modules can plug in via
the same protocol.

## When to use governance

| You should add a governance module when... | You should NOT when... |
|---|---|
| Your wiki is research that has downstream cost (finance, healthcare, compliance) | Your wiki is exploratory; getting it wrong is cheap |
| Agent-coined content keeps polluting the wiki | All input is curated by the user |
| You want a review queue between "agent proposes" and "wiki accepts" | You want every ingest to land immediately |
| Multi-tenant: several humans share one wiki | Single user, single workstation |

When in doubt, leave governance off. Auto-wiki's default protocol is
already opinionated about merge / update / conflict — governance is
for cases where that's not enough.

## How to enable

Declare the module in `meta.yaml`:

```yaml
name: personal-pension
ontology_type: domain
seed: fibo-pensions
governance: ontology-mem    # ← references governance/ontology-mem.md
```

The seed and governance fields are **independent**. A wiki can have
both, either, or neither. They live at different layers:

| Layer | Purpose | Touches |
|---|---|---|
| **Seed** | Vocabulary normalisation | Page naming, anti-confusion rules, entity templates |
| **Validator** | Lint-time integrity | Run during `/auto-wiki lint`; produces a health report |
| **Governance** | Pre-ingest gating | Run during `/auto-wiki ingest`; can block writes |

Governance is the only one of the three that can **prevent** a write
to the wiki. Seed and validator are advisory; governance is
load-bearing.

## What a governance module provides

Every governance module ships:

1. **A protocol document** at
   `references/governance/{name}.md` that defines:

   - What candidate format the module accepts
   - Which routes the module can decide (e.g. `verified` /
     `needs_review` / `rejected`)
   - How to integrate with the ingest pipeline (pre-write hook)
   - How to surface results to the user (review cards, status
     reports)
   - What runtime services the module needs (MCP server, library,
     etc.) and how to start them

2. **Required state in the wiki directory** (e.g.
   `wiki/{topic}/governance.db` for ontology-mem).

3. **Optional UX additions** — most governance modules will add
   review cards, recall-time badges, or notification flows.

## Integration with the ingest protocol

When `meta.yaml` declares `governance: <name>`, the ingest flow gains
one mandatory pre-write step:

```
1. Read source file              ┐ unchanged
2. Extract candidate items       ┘
3. ★ governance.gate(candidate)  ← new: route-before-write
   ├─ verified         → continue to step 4
   ├─ needs_review     → present review card, defer write
   ├─ conflict_checked → present review card with conflict details
   └─ rejected         → log + skip
4. Compare old vs new            ┐ runs only on verified items
5. Write structured data         │
6. Create/update Markdown pages  │
7. Update index.md + log.md      ┘
8. ★ Surface review cards for non-verified items
```

See [`../ingest-protocol.md` § Governance Hook](../ingest-protocol.md#governance-hook)
for the full integrated flow.

## Integration with the recall protocol

When `meta.yaml` declares `governance: <name>`, recall mode picks up
two extra responsibilities:

- **Origin badges**: every claim cited from the wiki should be
  tagged with its `origin_role` (`user` / `agent` / `extractor` /
  `system`). The user sees at a glance whether a statement came from
  their own input or from agent inference.

- **Review-queue awareness**: when answering, the agent should also
  check the governance module's review queue for items relevant to
  the question and either:
  - mention them ("3 pending review items mention X — should I
    surface them?")
  - or run a `/auto-wiki review` sub-flow first if the user agrees.

## Authoring a new governance module

To plug in a new module:

1. Create `references/governance/{your-name}.md` following the
   structure of `ontology-mem.md`.
2. Make the runtime side available — usually an MCP server the agent
   can call. The module's protocol document tells users how to
   start it.
3. Submit a PR to auto-wiki. Governance modules are listed in
   SKILL.md as an optional plugin layer alongside seeds and
   validators.

## Currently available

- [`ontology-mem`](ontology-mem.md) — route-before-store + 5-rule
  conflict detector + append-only ledger. Best for finance,
  healthcare, compliance, or any domain where wrong long-term
  memory has real cost.

## Anti-pattern

**Do not chain multiple governance modules.** Auto-wiki only loads
one. If you need richer governance, extend the module you choose —
don't stack two.
