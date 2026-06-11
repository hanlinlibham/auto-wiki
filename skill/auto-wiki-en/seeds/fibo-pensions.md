---
name: fibo-pensions
display_name: FIBO Pensions Module
source: EDM Council FIBO (Financial Industry Business Ontology)
url: https://spec.edmcouncil.org/fibo/
applies_to: enterprise annuity (企业年金), occupational annuity (职业年金), pension management
validator: validators/fibo-mcp.md
---

# FIBO Pensions Seed Vocabulary

> Cold-start reference for wikis in the enterprise annuity (企业年金) / pension domain.
> Reference this file by setting `seed: fibo-pensions` in `meta.yaml`.

## Foundational Financial Concepts (FIBO-FND)

Usable as reference by any financial-domain wiki:

| Standard concept | Description | Usually maps to in the wiki |
|---------|------|----------------|
| LegalEntity | Legal entity | Institution pages under entities/ |
| Contract | Contract / agreement | Institutional-arrangement pages under concepts/ |
| FinancialInstrument | Financial instrument | Product pages under entities/ |
| RegulatoryAgency | Regulatory agency | entities/ |
| Jurisdiction | Jurisdiction | concepts/ |
| DatePeriod | Time period | Temporal fields in frontmatter |

## Business Entities (FIBO-BP)

| Standard concept | Description | Common confusion |
|---------|------|---------|
| Organization | Organization | ≠ OrganizationalRole (an institution ≠ an institutional role) |
| FunctionalEntity | Functional entity | E.g. "trustee" is a role, not the institution itself |
| Person | Natural person | |

## Securities (FIBO-SEC)

| Standard concept | Description | Applicable scenarios |
|---------|------|---------|
| Fund | Fund | Mutual funds, enterprise annuity funds |
| Portfolio | Investment portfolio | ≠ Product (portfolio ≠ product) |
| Security | Security | |
| Issuer | Issuer | |

## Pension-specific (FIBO-Pensions)

| Standard concept | Chinese market equivalent | No-confusion rule |
|---------|---------|---------|
| PensionPlan | Enterprise annuity plan (企业年金计划) | ≠ PensionFund (plan ≠ fund) |
| PensionFund | Enterprise annuity fund (企业年金基金) | ≠ PensionProduct (fund ≠ product) |
| PlanSponsor | Plan sponsor — the employer (委托人) | |
| Trustee | Trustee (受托人) | A role, not an institution — the same institution can be both trustee and investment manager |
| InvestmentManager | Investment manager (投资管理人) | |
| Custodian | Custodian (托管人) | |
| AccountManager | Account manager (账户管理人) | |
| Beneficiary | Beneficiary — the employee (受益人) | |
| VestingSchedule | Vesting schedule (归属计划) | |
| ContributionRate | Contribution rate (缴费比例) | |
| DefinedBenefit | Defined benefit (DB, 确定给付型) | ≠ DefinedContribution (DC); China's enterprise annuity is DC-type |
| DefinedContribution | Defined contribution (DC, 确定缴费型) | |

## Relation Templates

```
PlanSponsor --establishes--> PensionPlan
PensionPlan --managed_by--> Trustee (fiduciary management)
Trustee --delegates_to--> InvestmentManager (investment management)
Trustee --delegates_to--> Custodian (custody)
Trustee --delegates_to--> AccountManager (account administration)
PensionFund --invests_in--> Portfolio
Beneficiary --participates_in--> PensionPlan
```

## No-confusion Rules

| Easily confused concept pair | Difference |
|----------------|------|
| PensionPlan ≠ PensionFund | The plan is an institutional arrangement; the fund is the money |
| PensionFund ≠ PensionProduct | The fund is a pool of money; the product is an investment vehicle |
| Organization ≠ FunctionalRole | A given bank is an institution; trustee is a role; the same institution can serve as both trustee and account manager |
| PlanType ≠ PortfolioCategory | Plan type (single-employer / collective) ≠ portfolio category (conservative / aggressive) |
| ContributionRate ≠ InvestmentReturn | Contribution rate ≠ investment return rate |
