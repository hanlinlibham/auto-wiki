# Seed Configuration (Seeds)

Seed files provide a cold-start vocabulary for domain-specific wikis. They live in this directory, one file per domain.

## File Format

```markdown
---
name: my-seed-name              # Unique identifier, referenced by this name in meta.yaml
display_name: Display Name
source: Name of the standard ontology this seed is based on
url: Reference link to the standard ontology
applies_to: Description of the research domains it applies to
validator: validators/xxx.md    # Optional, associated external validator
---

# Seed Title

## Vocabulary Category 1

| Standard concept | Description | Maps to in the wiki |
|---------|------|--------------|
| ConceptA | ... | entities/ |
| ConceptB | ... | concepts/ |

## Relation Templates

​```
EntityA --relation_type--> EntityB
​```

## No-confusion Rules

| Easily confused concept pair | Difference |
|----------------|------|
| A ≠ B | Explanation |
```

## How to Reference

Set the `seed` field in the wiki's `meta.yaml`:

```yaml
name: my-research-topic
ontology_type: domain
seed: my-seed-name        # Matches the name in the seed file's frontmatter
```

The Agent reads the corresponding seed file before the first ingest.

## Authoring Principles

1. **Keep the vocabulary lean**. List only the 20-50 most central concepts of the domain; don't try to cover the entire standard
2. **No-confusion rules are the core value**. For the concept pairs the Agent most easily mixes up, spell out the difference
3. **Relation templates must be concrete**. Don't just list relation type names; give complete `A --type--> B` examples
4. **The target language is allowed**. Concept names use standard English, but descriptions and no-confusion rules may be written in the target language
5. **Declaring a validator is optional**. If the domain has a usable external validator (such as FIBO MCP), point to it via the `validator` field in the frontmatter

## Currently Available Seeds

| File | Domain | Concept count |
|------|------|--------|
| `fibo-pensions.md` | Enterprise annuity (企业年金) / pensions | ~30 |
