# Cognitive Ontology: Collection & Synthesis Strategy for Person Research

> Use this strategy when the research subject is a **person** (their way of thinking, decision patterns, expression style).
> Adapted from cognitive-profile methodology; covers only the wiki accumulation phase, not final persona crystallization.

---

## I. Six-Dimension Collection Framework

Each dimension corresponds to one ingest, producing one source page.

| Dimension | What to search | What to extract | Source page output |
|------|---------|---------|----------------|
| **Writings** | Books, long-form essays, papers, newsletters | Recurring core arguments (>=3 occurrences = genuine belief); coined terms; recommended reading lists (intellectual lineage) | `sources/{date}-writings.md` |
| **Conversations** | Podcasts, long videos, AMAs, in-depth interviews | How they answer under probing; improvised analogies; moments of changing position; questions they refuse to answer | `sources/{date}-conversations.md` |
| **Expression DNA** | Twitter/X, Weibo, Jike, short posts | High-frequency wording and sentence patterns; controversial stances; style of humor; public debates | `sources/{date}-expression-dna.md` |
| **External Views** | Others' analyses, book reviews, critiques, biographies | Externally observed patterns; criticism and controversies; comparison with peers | `sources/{date}-external-views.md` |
| **Decision Records** | Major decisions, turning points, controversial actions | Decision context and logic; after-the-fact reflection; cases of word-deed consistency/inconsistency | `sources/{date}-decisions.md` |
| **Timeline** | Full career history + last 12 months of activity | Key milestones; intellectual turning points; latest status (anti-staleness) | `sources/{date}-timeline.md` |

**Information grading**: every extracted item must label its source type — primary (the person's own words) > secondary (others' retelling) > inference.

**Source priority**: own writings / long interviews / actual decisions > social media / others' assessments > secondhand retelling.
Source blacklist: Zhihu, WeChat official accounts, Baidu Baike. For Chinese-speaking subjects, prefer original Bilibili videos, Xiaoyuzhou podcasts, and authoritative media (36Kr / LatePost / Caixin).

---

## II. Synthesis Rules

Once all 6 source pages are in place, run synthesis to produce entity and concept pages.

### 2.1 Triple Verification (mental model vs decision heuristic)

List candidate arguments from all sources (typically 15-30), then verify each one:

| Verification dimension | Method | Pass signal |
|---------|---------|---------|
| **Cross-domain recurrence** | Same thinking framework appears in >=2 distinct domains/topics | Corroborated by both writings and decisions |
| **Generative power** | The model can predict the person's stance on questions they have not addressed | Produces plausible predictions |
| **Exclusivity** | Not how every smart person thinks; reflects this person's distinctive perspective | Discriminative |

- Passes all three → mental model (write into an entity page)
- Passes only 1-2 → downgrade to decision heuristic (write into a concept page)
- Passes none → not included in the wiki

### 2.2 Expression DNA Quantification

Sample 20 passages from the person's long-form writing/speeches and measure:

- **Sentence fingerprint**: average sentence length, question ratio, analogy density (per 1,000 words), first-person frequency, certainty-tone ratio
- **Style tags** (scored on 7 axes): formal-colloquial, abstract-concrete, cautious-assertive, academic-popular, long-short sentences, build-up vs conclusion-first, data-driven vs narrative-driven
- **Taboo words and verbal tics**: words never used + high-frequency expressions

Output one concept page: `concepts/expression-dna.md`.

### 2.3 Contradiction Handling

Contradictions are personality features, not bugs to be fixed. Handle them in three categories:

| Contradiction type | Meaning | Treatment in the wiki |
|---------|------|--------------|
| **Temporal contradiction** | Said A early on, B later (opinion evolution) | Record the evolution trajectory in the page, labeling the periods; confidence stays `high` |
| **Domain contradiction** | Advocates X at work, Y in private life | Record per domain, no forced unification; this is where depth comes from |
| **Essential tension** | Internal value conflict (e.g. prizing freedom yet valuing discipline) | Create a standalone concept page `concepts/tension-{name}.md`, marked as a core tension |

Never do: pick one side and ignore the other, fabricate reconciling explanations, or pretend the contradiction does not exist.

---

## III. Wiki Page Types

### Entity pages

**One page per mental model**, not one page per person.

```markdown
---
title: Inversion
type: mental-model
created: 2026-04-06
updated: 2026-04-06
sources: [2026-04-06-writings, 2026-04-06-decisions]
confidence: high
verification:
  cross_domain: true
  generative: true
  exclusive: false
  domains: [investment decisions, risk management, product design]
relations:
  - target: psychology-of-misjudgment
    type: derived_from
---

## Model Description
Facing "how to succeed", first ask "how to guarantee failure".

## Source Evidence
- Writings: mentioned X times in Poor Charlie's Almanack ([[2026-04-06-writings]])
- Decisions: actually applied in event Y ([[2026-04-06-decisions]])

## How to Apply
Given any goal G, first enumerate every path leading to ~G, then avoid each one.

## Limitations
Biased toward conservatism; may miss opportunities that require a frontal assault.
```

The person also gets one overview entity page (`entities/{person-slug}.md`) linking to all mental-model and concept pages.

### Concept pages

Used for the following content:

| Content | Page example |
|------|---------|
| Decision heuristics (rules that failed triple verification) | `concepts/heuristic-{name}.md` |
| Values and anti-patterns | `concepts/values.md`, `concepts/anti-patterns.md` |
| Expression DNA | `concepts/expression-dna.md` |
| Core tensions | `concepts/tension-{name}.md` |
| Intellectual lineage (influenced / influenced-by relations) | `concepts/intellectual-lineage.md` |
| Honest boundaries (what this framework cannot do) | `concepts/honest-boundaries.md` |

### Source pages

One source page per collection dimension (6 in total) — a faithful digest of the raw material, never modified after creation.

---

## IV. Suggested Ingest Order

No strict order required, but recommended:

1. **Writings + Timeline** first — establish the basic framework and chronology
2. **Conversations + Decisions** next — capture improvised thinking and real behavior
3. **Expression DNA + External Views** last — quantify style and bring in external calibration

After each ingest, check: do existing pages need a confidence update, and have new contradictions emerged?

---

## V. Quality Standards

| Check | Pass criterion |
|--------|---------|
| Number of mental models | 3-7, each with evidence from >=2 distinct domains |
| Limitations per model | Failure conditions explicitly written |
| Expression DNA | All measurement dimensions complete (sentence + style + taboo words) |
| Primary-source share | > 50% |
| Contradiction records | >=2 tensions, neither avoided nor reconciled away |
| Honest boundaries | >=3 concrete limitations, with under-informed dimensions flagged |
