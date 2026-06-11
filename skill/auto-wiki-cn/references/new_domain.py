#!/usr/bin/env python3
"""
new_domain.py — auto-wiki 领域脚手架 + 跨域注册表生成器

一条命令建一个新领域（克隆骨架 + 初始化 data.db + 写 meta/本体/Hub/log + 重建注册表），
或单独重建 wiki/_index.md。

  # 建新域
  python new_domain.py tech \
      --direction 科技 --central "AI 产业链" \
      --hub 科技 --desc "AI / 半导体 / 软件 产业认知层" \
      --types "公司,产品,指标,机制,事件,分析,来源" \
      --keywords "AI,大模型,LLM,半导体,芯片,算力,GPU,英伟达,国产替代,SaaS,Agent"

  # 只重建注册表（任何 meta.yaml 改了之后）
  python new_domain.py --reindex

设计：meta.yaml 是单一真相源（含 direction/hub/keywords），_index.md 是它的派生视图。
受控关系词表不在此处校验——它是 _ontology.md 的散文约定，由 lint 人工对照（schema.py 域无关）。
"""
from __future__ import annotations
import argparse
import sys
from datetime import date
from pathlib import Path

# 复用引擎建表（与 store.py 同目录）
sys.path.insert(0, str(Path(__file__).resolve().parent))
import store  # noqa: E402

try:
    import yaml
except ImportError:
    print("需要 pyyaml：pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ── 定位仓库根（向上找含 CLAUDE.md 的目录）──────────────────────────────────
def find_repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [Path.cwd(), *Path.cwd().parents, *p.parents]:
        if (parent / "CLAUDE.md").exists() and (parent / "wiki").exists():
            return parent
    # 兜底：references -> auto-wiki -> skills -> .claude -> repo
    return p.parents[4]


REPO = find_repo_root()
WIKI = REPO / "wiki"
TODAY = date.today().isoformat()


# ── 模板 ────────────────────────────────────────────────────────────────────
def meta_yaml(name, direction, central, desc, hub, keywords, validator, coverage) -> str:
    kw = ", ".join(keywords)
    return f"""name: {name}
domain: {name}
direction: {direction}          # 大方向（科技 / 金融），_index.md 据此分组
ontology_type: domain
description: {desc}
central_entity: {central}
hub: {hub}                       # Obsidian Hub 页文件名（不含 .md）
keywords: [{kw}]                 # 路由关键词：ingest/recall 据此判断材料属哪个域
validator: {validator}
validator_coverage: {coverage}
schema_version: '2.0'
created: '{TODAY}'
updated: '{TODAY}'
"""


def ontology_md(name, direction, central, hub, types) -> str:
    type_rows = "\n".join(
        f"| ? | `{t}/` | <填判据> | <填例子> |" for t in types
    )
    return f"""---
title: {hub}领域本体契约
type: ontology
domain: {name}
direction: {direction}
created: '{TODAY}'
updated: '{TODAY}'
schema_version: "2.0"
central_entity: {central}
tags: [ontology, contract]
---

# Air Vault · {hub}领域本体契约

> `wiki/{name}/` 的本体定义。`ingest`/`recall` 前先读本页。引擎规范见 `.claude/skills/auto-wiki/`，
> 与 [[_ontology|macro 本体]] **共用同一套 6 档时间模型、退役不删除协议与三分铁律**——
> **本页只声明 {hub} 领域特有的节点类型与受控关系词表**，其余一律以引擎 + macro 契约为准。

## 0. 总原则（同 macro）
1. **节点 / 数据 / 边 三分**：数值绝不是节点（进 data.db）；关系是边不是页；分类标签是边不是页。
2. **编译单向**：`Inbox(散文) → ingest → wiki(本体)`。严谨只用在已结晶的知识。
3. **退役不删除**：T1/T2/T3 任何变化都是「旧行封 valid_to + 插新行」，永不 DELETE，必有 T4 事件盖章。

## 1. 节点判据（同 macro 的「能不能指向就是这一个」）
能用手指指向「就是这一个」、明年同名还指同一个 → **实体**；必须先讲一段机理才懂 → **概念**。

## 2. 节点类型（=目录=图谱着色）
| 类型 | 子目录 | 判据 | 例子 |
|---|---|---|---|
{type_rows}

> ⚠️ 脚手架生成的占位表——首次 ingest 前**必须**把每行的判据/例子填实，并删掉本提示。

## 3. 受控关系词表（{hub} 特有；通用词 references/part_of/instance_of 等沿用 macro）
<在此声明本域的关系词：from_type → to_type，一句话语义。lint 时以此对照，越界边拒绝。>

## 4. 跨域连接
本域作为驱动层时，用 `references` 边连到其他域的「分析/节点」（如 {name}/分析 → equity/公司）。
跨域 wikilink 直接写对方 slug 即可。
"""


def hub_md(name, direction, central, hub, types) -> str:
    sections = "\n".join(f"## {t}\n- \n" for t in types)
    return f"""---
title: {hub}
type: ontology
domain: {name}
direction: {direction}
updated: '{TODAY}'
tags: [hub, moc]
---

# {hub}领域 Wiki

> 中心实体 [[{central}]] · 本体契约见 [[_ontology]] · 数据见 data.db · 方向：{direction}

## 知识结构
```
（首次 ingest 后补：中心实体辐射图）
```

{sections}"""


def log_md(name, hub) -> str:
    return f"""# {hub}领域 · ingest 日志

> 每次 ingest 追加一行：日期 · 源材料 · 新增/更新节点 · 关系边 · 校验结果。

## {TODAY}
- 域创建（new_domain.py 脚手架）。待首次 ingest。
"""


# ── 注册表生成 ──────────────────────────────────────────────────────────────
def reindex() -> str:
    domains = []
    for meta_path in sorted(WIKI.glob("*/meta.yaml")):
        m = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        domains.append(m)

    by_dir: dict[str, list] = {}
    for m in domains:
        by_dir.setdefault(m.get("direction", "未分类"), []).append(m)

    lines = [
        "---",
        "title: wiki 域注册表",
        "type: registry",
        f"updated: '{TODAY}'",
        "tags: [hub, moc, registry]",
        "---",
        "",
        "# Air Vault · wiki 域注册表（自动生成）",
        "",
        "> 由 `new_domain.py --reindex` 扫描各域 `meta.yaml` 生成，**勿手改**（改 meta.yaml 再重建）。",
        "> **ingest/recall 第 0 步先读本页**：按「路由关键词」把材料/问题命中到域；横跨多域则双写 + 跨域连边。",
        "",
        f"当前 {len(domains)} 个域，{len(by_dir)} 个方向。",
        "",
    ]
    for direction in sorted(by_dir):
        lines.append(f"## 方向：{direction}")
        lines.append("")
        lines.append("| 域 | 中心实体 | 范围 | 路由关键词 |")
        lines.append("|---|---|---|---|")
        for m in by_dir[direction]:
            hub = m.get("hub", m.get("name"))
            kws = m.get("keywords", []) or []
            kw = "、".join(kws) if isinstance(kws, list) else str(kws)
            lines.append(
                f"| [[{hub}]] `{m.get('name')}/` | [[{m.get('central_entity','')}]] | "
                f"{m.get('description','')} | {kw} |"
            )
        lines.append("")

    out = "\n".join(lines)
    (WIKI / "_index.md").write_text(out, encoding="utf-8")
    return out


# ── 建域 ────────────────────────────────────────────────────────────────────
def create_domain(args) -> None:
    name = args.name
    ddir = WIKI / name
    if ddir.exists():
        print(f"✗ 域已存在：{ddir}", file=sys.stderr)
        sys.exit(1)

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    hub = args.hub or name

    # 1. 目录骨架
    ddir.mkdir(parents=True)
    for t in types:
        sub = ddir / t
        sub.mkdir()
        (sub / ".gitkeep").write_text("", encoding="utf-8")

    # 2. data.db（幂等建表）
    s = store.WikiStore(str(ddir))
    s.init_db()
    s.close()

    # 3. 四件套
    (ddir / "meta.yaml").write_text(
        meta_yaml(name, args.direction, args.central, args.desc, hub,
                  keywords, args.validator, args.coverage), encoding="utf-8")
    (ddir / "_ontology.md").write_text(
        ontology_md(name, args.direction, args.central, hub, types), encoding="utf-8")
    (ddir / f"{hub}.md").write_text(
        hub_md(name, args.direction, args.central, hub, types), encoding="utf-8")
    (ddir / "log.md").write_text(log_md(name, hub), encoding="utf-8")

    # 4. 重建注册表
    reindex()

    print(f"✓ 域已创建：wiki/{name}/")
    print(f"  类型子目录：{', '.join(types)}")
    print(f"  data.db 已建表 | meta.yaml/_ontology.md/{hub}.md/log.md 已生成")
    print(f"  wiki/_index.md 已重建（{args.direction} 方向）")
    print(f"  ⚠️ 下一步：手动填实 wiki/{name}/_ontology.md 的类型判据表 + 关系词表，再 ingest")


def main():
    ap = argparse.ArgumentParser(description="auto-wiki 领域脚手架")
    ap.add_argument("name", nargs="?", help="域名（英文 slug，如 tech）")
    ap.add_argument("--direction", default="未分类", help="大方向：科技 / 金融")
    ap.add_argument("--central", default="", help="中心实体（中文 slug）")
    ap.add_argument("--desc", default="", help="一句话范围描述")
    ap.add_argument("--hub", default="", help="Hub 页中文名（不含 .md，默认=域名）")
    ap.add_argument("--types", default="机构,指标,机制,事件,分析,来源",
                    help="节点类型子目录，逗号分隔")
    ap.add_argument("--keywords", default="", help="路由关键词，逗号分隔")
    ap.add_argument("--validator", default="fibo-mcp")
    ap.add_argument("--coverage", default="partial")
    ap.add_argument("--reindex", action="store_true", help="只重建 wiki/_index.md")
    args = ap.parse_args()

    if args.reindex:
        reindex()
        print("✓ wiki/_index.md 已重建")
        return
    if not args.name:
        ap.error("建域需要域名；或用 --reindex 只重建注册表")
    create_domain(args)


if __name__ == "__main__":
    main()
