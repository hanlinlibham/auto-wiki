#!/usr/bin/env python3
"""实例配置解析器 — auto-wiki v0.4.1 新增（解耦环 1a 的唯一读取入口）。

原生逻辑（环 0）一律经由本模块读"实例事实"，不硬编码任何库习俗——
08-Ops 是陋居 PARA 范式的目录名，不是方法论的一部分。

配置链（后者覆盖前者）：
  内置默认 ← wiki/_config.yaml（standalone 实例）← .burrow/config.json（burrow 范式实例）

解析结果字段：
  vault_root            库根（向上找 .burrow/config.json 或含 wiki/ 的目录）
  ops_dir               运行留痕目录（run 档 / query-miss.md 落点）：
                        显式 ops_dir 键 > 自动识别既有 08-Ops/ > 默认 wiki/_ops
  title_proper          实例显示名（默认 = 目录名）
  mother_ontology_link  母本契约链接（无则空串，模板句自动降级为"引擎规范"）
  mother_ref            母本称谓（无则空串）
  relations             实例声明的关系词表分组（原样透传，0.5.0 词表真校验的输入）
  anchor_required       R9 设立依据口径 {subtypes: [...], since: "YYYY-MM-DD"}（原样透传，
                        缺省 {} = 不启用；schema.py validate_page 消费，0.5.0 改契约驱动）
  engine_version        当前引擎版本（读 SKILL.md frontmatter）

CLI：python instance.py [起点路径] → 解析结果 JSON（协议步骤让 Agent 直接跑它，不要凭记忆猜路径）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_vault_root(start: Path) -> Path:
    p = start.resolve()
    if p.is_file():
        p = p.parent
    for parent in [p, *p.parents]:
        if (parent / ".burrow" / "config.json").exists():
            return parent
        if (parent / "wiki").is_dir():
            return parent
    return p


def engine_version() -> str:
    skill = HERE.parent / "SKILL.md"
    if skill.exists():
        # 0.4.3 起遵循 Skill frontmatter 规范放在 metadata.version；
        # 宽松匹配仍兼容 0.4.2 及更早的顶层 version。
        m = re.search(r'(?m)^\s{0,2}version:\s*["\']?([\d.]+)', skill.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return "unknown"


def load(start: str | Path = ".") -> dict:
    root = find_vault_root(Path(start))
    cfg: dict = {}

    yml = root / "wiki" / "_config.yaml"
    if yml.exists():
        try:
            import yaml
            cfg.update(yaml.safe_load(yml.read_text(encoding="utf-8")) or {})
        except Exception as e:
            print(f"[instance] wiki/_config.yaml 解析失败，忽略：{e}", file=sys.stderr)

    bj = root / ".burrow" / "config.json"
    if bj.exists():
        try:
            cfg.update(json.loads(bj.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[instance] .burrow/config.json 解析失败，忽略：{e}", file=sys.stderr)

    ops = cfg.get("ops_dir")
    if not ops:
        ops = "08-Ops" if (root / "08-Ops").is_dir() else "wiki/_ops"
    nd = cfg.get("new_domain", {}) or {}
    return {
        "vault_root": str(root),
        "ops_dir": ops,
        "title_proper": cfg.get("title_proper", root.name),
        "mother_ontology_link": nd.get("mother_ontology_link", ""),
        "mother_ref": nd.get("mother_ref", ""),
        "relations": cfg.get("relations", {}),
        "anchor_required": cfg.get("anchor_required", {}) or {},
        "engine_version": engine_version(),
    }


if __name__ == "__main__":
    print(json.dumps(load(sys.argv[1] if len(sys.argv) > 1 else "."),
                     ensure_ascii=False, indent=2))
