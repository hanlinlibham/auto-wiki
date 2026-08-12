# auto-wiki — English edition v0.3.0 (ARCHIVED)

> 🪦 **Archived 2026-08-12.** This edition is no longer maintained. It is kept here
> intact, not deleted — every file is exactly as it was at v0.3.0.
>
> The maintained implementation is [`../../skill/auto-wiki-cn/`](../../skill/auto-wiki-cn/)
> at **v0.4.4**.

## Why it was archived

Engine development ran ahead on the Chinese edition between 2026-06 and 2026-08.
This edition documents **five modes**; the current engine has **seven**. Porting
0.4.x would mean translating two new protocol documents plus substantial SKILL.md
changes — work that was never scheduled. Rather than leave a stale copy sitting
next to the maintained one where it reads as an equal option, it is archived.

## What it does not have

| Missing | What you lose |
|---|---|
| **`init` mode** (`init-protocol.md`) | The interview-based setup that infers your first domain, node types and relations from your actual workflow. Without it you build the wiki structure by hand. |
| **`source` mode** (`source-protocol.md`) | The collection phase — fan-out search that lands material in `Inbox/raw/` with provenance and channel grading, without touching the wiki. |
| **`precheck.py`** | The pre-write hard gate (schema + four high-frequency defect classes) and same-type collision detection. |
| **`instance.py`** | Instance-config resolution and the `born_of` birth stamp that drives advisory migration hints on engine upgrade. |
| **`export_okf.py`** | One-way OKF v0.1 export for vendor-neutral exchange. |
| **`reading-notes` seed** | The general-purpose cold start for books, courses, papers and podcasts. |
| **`examples/bookshelf/`** | The runnable minimal closed loop used for onboarding. |

## It still runs

Nothing here is broken. The five modes it documents — `recall`, `ingest`, `query`,
`lint`, `deep-dive` — are functional and self-contained; copy this directory and it
works. It simply will not receive updates.

The Python tools under `references/` are language-neutral, so if you read English but
want the current feature set, take [`skill/auto-wiki-cn/`](../../skill/auto-wiki-cn/) —
the code is the same, only the protocol prose is in Chinese.

## If you want to revive it

An English port of 0.4.x is welcome as a contribution. The delta is the table above
plus the SKILL.md rewrite; see [CHANGELOG.md](../../CHANGELOG.md) for the full 0.4.4
entry. Open an issue first so the work isn't duplicated.
