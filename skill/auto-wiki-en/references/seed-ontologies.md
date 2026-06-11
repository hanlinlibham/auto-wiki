# Seed Ontologies: Bootstrapping Wiki Structure with Standard Vocabularies

> Seeds are an optional cold-start reference, not a hard dependency.
> Domains without a seed grow freely — a seed merely makes the start more disciplined.

## Mechanism

### What a Seed Is

A seed is a domain vocabulary configuration containing:

| Content | Purpose |
|---------|---------|
| **Standard terms** | Naming reference for wiki page slugs and titles |
| **Classification scheme** | Hints to the Agent which dimensions the domain typically needs to cover |
| **Relation templates** | Standard inter-entity relation types (manages, regulates, invests_in, etc.) |
| **No-confusion rules** | Flag common concept mix-ups so the Agent doesn't conflate them |

Seed files live in the `seeds/` directory, one file per domain.

### How to Reference One

When creating a new wiki, declare which seed to use in `meta.yaml`:

```yaml
name: my-research-topic
ontology_type: domain
seed: fibo-pensions          # References seeds/fibo-pensions.md
```

The Agent reads the corresponding seed file before the first ingest. If the `seed` field is empty or unset, skip the seed and let the wiki grow freely.

### What It Does Not Do

- No OWL/RDF import — the wiki is markdown, not the semantic web
- No forced standard terminology — if the domain's actual usage differs, follow actual usage but note the mapping
- No overriding of user customizations — the seed is only a starting reference; as the wiki evolves it will outgrow the seed

---

## Available Seeds

| Seed File | Domain Covered | Based On |
|-----------|----------------|----------|
| `seeds/fibo-pensions.md` | Occupational pensions, pension management | FIBO (EDM Council) |
| *(to be extended)* | | |

### Industry-Standard Ontologies Worth Referencing

When writing a new seed, these standards are useful references:

| Standard | Domain Covered | Use Case | Reference Link |
|----------|----------------|----------|----------------|
| **FIBO** | Entire financial industry | Banking, insurance, funds, pensions | spec.edmcouncil.org/fibo |
| **XBRL Taxonomy** | Financial reporting | Listed-company financial data analysis | xbrl.org |
| **Schema.org** | General entities | People, organizations, events, places | schema.org |
| **SKOS** | Knowledge organization | Classification schemes, concept hierarchies | w3.org/2004/02/skos |
| **Dublin Core** | Document metadata | Frontmatter of source pages | dublincore.org |
| **FOAF** | People & social | Person research (cognitive type) | xmlns.com/foaf |

| Research Type | Recommended Seed/Standard |
|---------------|---------------------------|
| Occupational / corporate pensions | `fibo-pensions` |
| Mutual funds | FIBO-SEC (Fund) — a new seed can be written on top of it |
| Listed-company analysis | FIBO-BP + XBRL |
| Macroeconomics | No standard seed (free growth) |
| Person cognition | FOAF + custom mental-model types |
| General topics | Schema.org |

---

## How the Agent Uses Seeds

### During Ingest

```
1. Read the source file, extract key entities
2. If meta.yaml declares a seed → read the seed file and check against the vocabulary:
   - Does the entity have a standard name? → Use the standard name as the page slug
   - Which standard category does it belong to? → Place under the matching entities/ or concepts/
   - Does it touch a no-confusion rule? → Distinguish explicitly on the page
3. Continue with the normal ingest steps
```

**Example** (financial domain):
```
A source file mentions a bank's pension business
→ Check the seed vocabulary: this is an Organization acting in the Trustee role
→ Create entities/bank-x.md (institution page)
→ In the relations, note that bank-x acts as trustee
→ Do NOT create entities/bank-x-trustee.md (organization ≠ role — obey the no-confusion rules)
```

### During Lint

```
1. If meta.yaml declares a seed → read the seed file
2. Check whether page naming aligns with the seed vocabulary
3. Check for violations of the no-confusion rules
4. Check whether any key dimension from the seed remains uncovered
5. Output an alignment score in the health report
```

### During Query

```
The user asks about a domain term
→ From the seed vocabulary, the Agent knows the term's standard position and related concepts
→ The search expands to those related concepts
→ The answer is more complete
```

---

## External Validators

A seed file may declare an associated external validator (the `validator` field in its frontmatter).
A validator provides runtime logical validation beyond the seed's static vocabulary — checking the domain/range legality of relations, whether an entity's required relations are missing, and so on.

Validator configurations live in the `validators/` directory. See each validator's documentation for details.

Currently available validators:

| Validator | Description | Corresponding Seed |
|-----------|-------------|--------------------|
| `validators/fibo-mcp.md` | FIBO SPARQL logical validation (627K inferred triples) | `fibo-pensions` |

**Validators are an optional enhancement.** When unreachable, lint degrades to schema.py format validation + the seed's static rules, without affecting the core flow.

---

## Limitations

1. **A seed is a starting point, not an endpoint.** As the wiki accumulates, it will produce concepts the seed never had
2. **Standard terms may differ from the industry's actual usage.** Follow industry usage, but note the standard-term mapping on the page
3. **Not every domain has a mature standard ontology.** Domains with no suitable seed simply grow freely
4. **Seeds themselves evolve.** When a standard updates, the wiki need not sync — seeds are consulted only once, at cold start
