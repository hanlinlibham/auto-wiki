---
name: fibo-pensions
display_name: FIBO 养老金模块
source: EDM Council FIBO (Financial Industry Business Ontology)
url: https://spec.edmcouncil.org/fibo/
applies_to: 企业年金、职业年金、养老金管理
validator: validators/fibo-mcp.md
---

# FIBO 养老金种子词表

> 用于企业年金/养老金领域 wiki 的冷启动参考。
> 在 `meta.yaml` 中设置 `seed: fibo-pensions` 引用本文件。

## 基础金融概念（FIBO-FND）

所有金融领域 wiki 都可参考：

| 标准概念 | 说明 | wiki 中通常对应 |
|---------|------|----------------|
| LegalEntity | 法人实体 | entities/ 下的机构页面 |
| Contract | 合同/协议 | concepts/ 下的制度页面 |
| FinancialInstrument | 金融工具 | entities/ 下的产品页面 |
| RegulatoryAgency | 监管机构 | entities/ |
| Jurisdiction | 管辖区域 | concepts/ |
| DatePeriod | 时间段 | frontmatter 的时间字段 |

## 商业实体（FIBO-BP）

| 标准概念 | 说明 | 常见混淆 |
|---------|------|---------|
| Organization | 组织机构 | ≠ OrganizationalRole（机构 ≠ 机构角色） |
| FunctionalEntity | 职能实体 | 如"受托人"是角色，不是机构本身 |
| Person | 自然人 | |

## 证券（FIBO-SEC）

| 标准概念 | 说明 | 适用场景 |
|---------|------|---------|
| Fund | 基金 | 公募基金、企业年金基金 |
| Portfolio | 投资组合 | ≠ Product（组合 ≠ 产品） |
| Security | 证券 | |
| Issuer | 发行人 | |

## 养老金专用（FIBO-Pensions）

| 标准概念 | 中文对应 | 禁混规则 |
|---------|---------|---------|
| PensionPlan | 企业年金计划 | ≠ PensionFund（计划 ≠ 基金） |
| PensionFund | 企业年金基金 | ≠ PensionProduct（基金 ≠ 产品） |
| PlanSponsor | 委托人（企业） | |
| Trustee | 受托人 | 是角色，不是机构——同一机构可以同时是受托人和投管人 |
| InvestmentManager | 投资管理人 | |
| Custodian | 托管人 | |
| AccountManager | 账户管理人 | |
| Beneficiary | 受益人（职工） | |
| VestingSchedule | 归属计划 | |
| ContributionRate | 缴费比例 | |
| DefinedBenefit | 确定给付型（DB） | ≠ DefinedContribution（DC），中国企业年金是 DC 型 |
| DefinedContribution | 确定缴费型（DC） | |

## 关系模板

```
PlanSponsor --establishes--> PensionPlan
PensionPlan --managed_by--> Trustee (受托管理)
Trustee --delegates_to--> InvestmentManager (投资管理)
Trustee --delegates_to--> Custodian (托管)
Trustee --delegates_to--> AccountManager (账户管理)
PensionFund --invests_in--> Portfolio
Beneficiary --participates_in--> PensionPlan
```

## 禁混规则

| 容易混淆的概念对 | 区别 |
|----------------|------|
| PensionPlan ≠ PensionFund | 计划是制度安排，基金是钱 |
| PensionFund ≠ PensionProduct | 基金是资金池，产品是投资工具 |
| Organization ≠ FunctionalRole | 某银行是机构，受托人是角色；同一机构可以同时担任受托人和账管人 |
| PlanType ≠ PortfolioCategory | 计划类型（单一/集合）≠ 投资组合类别（稳健/积极） |
| ContributionRate ≠ InvestmentReturn | 缴费率 ≠ 投资回报率 |
