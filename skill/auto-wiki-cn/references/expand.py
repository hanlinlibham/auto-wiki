"""图谱遍历工具 · expand(节点, 深度)

把"知识图谱"从『带手写索引的文档库』升级成『可遍历的图』：给一个种子节点，
沿受控关系边向外辐射 N 跳，返回每一环的邻居 + 连到它的那条边（带方向、带类型）。

为什么存在：LLM 默认是"语义聚光"（按意思跳到相关节点），会漏掉**语义盲区里的
结构邻居**——名字看不出相关、但结构上一跳即达的节点（典型：跨域 grounds 边，
『自由意志怀疑论 →grounds→ 道德责任』）。本工具让"走边"成为一个显式动作，
专治这种相关性排序的死角。

跨全库遍历：slug 全库唯一（命名纪律），所以合并所有 wiki/*/data.db 的 relations
成一张全局图——跨域边（grounds/references）落在理论域的 db 里，照样能从实践域的
节点反向走到它。这正是最值钱的盲区邻居所在。

用法：
    python expand.py <种子slug> [--depth N] [--dir out|in|both]
                     [--types t1,t2] [--skip-types t1,t2]
                     [--cross-only] [--include-retired] [--json]
                     [--vault PATH]

例：
    python expand.py 连点成线 --depth 2            # 从"连点成线"辐射两跳
    python expand.py 自由意志 --dir in --cross-only # 只看跨域、指向它的边
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
from collections import deque
from datetime import date

FAR_FUTURE = "9999-12-31"


# ── 装载：合并全库 data.db → 一张全局图 ──────────────────────────────
def load_graph(vault_root: str, include_retired: bool = False):
    """返回 (nodes, out_adj, in_adj)。
    nodes[slug] = {title,type,subtype,confidence,domain}
    out_adj[slug] = [(to, type, edge_domain), ...]   # slug 指向的
    in_adj[slug]  = [(frm, type, edge_domain), ...]   # 指向 slug 的
    """
    nodes: dict[str, dict] = {}
    out_adj: dict[str, list] = {}
    in_adj: dict[str, list] = {}
    today = date.today().isoformat()

    db_paths = sorted(glob.glob(os.path.join(vault_root, "wiki", "*", "data.db")))
    if not db_paths:
        sys.exit(f"[expand] 没找到任何 wiki/*/data.db（vault={vault_root}）")

    for db in db_paths:
        domain = os.path.basename(os.path.dirname(db))
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        # 节点：每个 slug 的 home 域 = 其 page 所在 db
        for r in conn.execute("SELECT slug,title,type,subtype,confidence FROM pages"):
            nodes.setdefault(r["slug"], {
                "title": r["title"], "type": r["type"], "subtype": r["subtype"],
                "confidence": r["confidence"], "domain": domain,
            })
        # 边：current = valid_to 仍是远期（或 >= today）且未被退役事件盖章
        q = "SELECT from_slug,to_slug,type,valid_to,retract_event_slug FROM relations"
        for r in conn.execute(q):
            if not include_retired:
                vt = r["valid_to"]
                retired = r["retract_event_slug"] is not None or (
                    vt is not None and vt != FAR_FUTURE and vt < today)
                if retired:
                    continue
            f, t, ty = r["from_slug"], r["to_slug"], r["type"]
            out_adj.setdefault(f, []).append((t, ty, domain))
            in_adj.setdefault(t, []).append((f, ty, domain))
        conn.close()

    return nodes, out_adj, in_adj


# ── 遍历：BFS 辐射 ─────────────────────────────────────────────────
def expand(seed, depth, direction, nodes, out_adj, in_adj,
           types=None, skip_types=None, cross_only=False):
    """BFS 从 seed 辐射 depth 跳。返回 rings[hop] = [reach...] 与 subedges。
    每个 reach = {slug, via_type, via_node, dir('→'|'←'), cross(bool)}。
    """
    seed_dom = nodes.get(seed, {}).get("domain")
    visited = {seed}
    rings = {0: [{"slug": seed, "via_type": None, "via_node": None,
                  "dir": None, "cross": False}]}
    subedges = []                       # 子图里所有边（含环内），给 agent 看局部结构
    frontier = deque([(seed, 0)])

    def edge_ok(ty, to_dom):
        if types and ty not in types:
            return False
        if skip_types and ty in skip_types:
            return False
        if cross_only and to_dom == seed_dom:
            return False
        return True

    while frontier:
        cur, hop = frontier.popleft()
        if hop >= depth:
            continue
        # out 边：cur → nb（cur 指向的）
        steps = []
        if direction in ("out", "both"):
            for nb, ty, ed in out_adj.get(cur, []):
                steps.append((nb, ty, "→"))
        if direction in ("in", "both"):
            for nb, ty, ed in in_adj.get(cur, []):
                steps.append((nb, ty, "←"))
        for nb, ty, arrow in steps:
            nb_dom = nodes.get(nb, {}).get("domain")
            cross = nb_dom is not None and nb_dom != nodes.get(cur, {}).get("domain")
            if not edge_ok(ty, nb_dom):
                continue
            subedges.append((cur, nb, ty, arrow))
            if nb in visited:
                continue
            visited.add(nb)
            rings.setdefault(hop + 1, []).append({
                "slug": nb, "via_type": ty, "via_node": cur,
                "dir": arrow, "cross": cross,
            })
            frontier.append((nb, hop + 1))
    return rings, subedges


# ── 渲染 ───────────────────────────────────────────────────────────
def fmt_node(slug, nodes):
    n = nodes.get(slug)
    if not n:
        return f"{slug}  [⚠ 无 page · 悬挂目标]"
    conf = "" if n["confidence"] in ("high", "medium") else f" · {n['confidence']}"
    return f"{slug}  ({n['type']}/{n['domain']}{conf})"


def render_text(seed, depth, rings, subedges, nodes):
    if seed not in nodes:
        cands = [s for s in nodes if seed in s][:8]
        out = [f"[expand] 种子 '{seed}' 不在图里。"]
        if cands:
            out.append("是不是想找：" + " · ".join(cands))
        return "\n".join(out)

    L = [f"⊙ expand('{seed}', depth={depth})  —  {fmt_node(seed, nodes)}"]
    total = sum(len(v) for k, v in rings.items() if k > 0)
    cross = sum(1 for k in rings if k > 0 for r in rings[k] if r["cross"])
    L.append(f"  辐射到 {total} 个邻居 · 其中 {cross} 个跨域（★ = 语义盲区里的结构邻居）")
    for hop in sorted(k for k in rings if k > 0):
        L.append(f"\n── 第 {hop} 跳 ({len(rings[hop])}) ──")
        # 跨域排前面（最值钱）
        for r in sorted(rings[hop], key=lambda x: (not x["cross"], x["via_type"] or "")):
            star = "★ " if r["cross"] else "  "
            edge = f"{r['dir']}{r['via_type']}{r['dir']}"   # 如 ←grounds←
            L.append(f"  {star}{edge:<16} {fmt_node(r['slug'], nodes)}")
            L.append(f"       └ 经 {r['via_node']}")
    # 悬挂目标提示
    dangling = sorted({t for _, t, _, _ in subedges if t not in nodes})
    if dangling:
        L.append(f"\n⚠ 悬挂边目标（边指向但无 page）：{' · '.join(dangling)}")
    return "\n".join(L)


# ── 结构空洞扫描（全库巡检：找该织入却没织入的节点）──────────────────
SKIP_TYPES_SCAN = {"source", "analysis", "ontology"}   # 天然边缘，不算洞
# 下面三组关系词分桶是 per-vault 的（金融用 drives/transmits_to…，哲学用 grounds/enables…）。
# 默认是「金融∪哲学」并集，真值由各库 .burrow/config.json 的 relations 覆盖（见 load_scan_vocab）。
ANCHOR_TYPES = {"part_of", "instance_of"}              # 把节点归入概念树的锚边
# 真·结构/思想边（有其一即"已横向织入"，不进富化池）
IDEA_TYPES = {"enables", "develops", "supports", "critiques", "grounds", "responds_to",
              "operated_by", "implements", "transmits_to", "bounds", "drives"}
# 纯归属/标签边：只有这些 = 没真正连进结构（"谁提的/什么类"不算织入）
ATTRIB_ONLY = {"proposed_by", "authored_by", "classified_as", "references"}


def load_scan_vocab(vault_root):
    """scan 用的关系词分桶：优先读 {vault}/.burrow/config.json 的 relations，缺省回退上面的并集。
    返回 (anchor, idea, attrib_only) 三个 set；让同一份 expand.py 在不同库按各自受控词表判洞。"""
    cfg_path = os.path.join(vault_root, ".burrow", "config.json")
    rel = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                rel = (json.load(f) or {}).get("relations", {}) or {}
        except Exception:
            rel = {}
    anchor = set(rel.get("anchor") or ANCHOR_TYPES)
    idea = set(rel.get("idea") or IDEA_TYPES)
    attrib = set(rel.get("attrib_only") or ATTRIB_ONLY)
    return anchor, idea, attrib


def scan_holes(nodes, out_adj, in_adj):
    """返回 (hard, soft)。
    hard = 真洞：孤儿（0 边）/ 未归位概念（无 part_of 锚，既非子也非父）/ 弱连接实体（单线 attribution）。
    soft = 可横向富化：已 part_of 归位、但无思想边的概念（enables/develops… 候选，非洞）。
    关键修正：已 part_of 归位的干净树叶（deg=1）不再误报为洞——一个干净分类树的叶子必然 deg=1。
    """
    hard, soft = [], []
    for slug, n in nodes.items():
        if n["type"] in SKIP_TYPES_SCAN:
            continue
        outs, ins = out_adj.get(slug, []), in_adj.get(slug, [])
        deg = len(outs) + len(ins)
        all_t = {t for _, t, _ in outs} | {t for _, t, _ in ins}
        woven = bool(all_t - ATTRIB_ONLY)          # 有任何非纯归属边 = 已连进结构（不止"谁提的"）
        placed = bool(all_t & ANCHOR_TYPES)        # 有 part_of/instance_of 分类锚
        has_idea = bool(all_t & IDEA_TYPES)
        rec = {"slug": slug, "type": n["type"], "domain": n["domain"],
               "deg": deg, "types": sorted(all_t)}
        if deg == 0:
            rec["tier"] = "孤儿"; hard.append(rec)
        elif n["type"] == "concept" and not woven:
            rec["tier"] = "未织入"; hard.append(rec)
        elif n["type"] == "entity" and deg == 1:
            rec["tier"] = "弱连接"; hard.append(rec)
        elif n["type"] == "concept" and placed and not has_idea:
            rec["tier"] = "可富化"; soft.append(rec)
        # else: 有思想边 / 实体多连 / 已健康 → 跳过
    return hard, soft


def render_scan(hard, soft, nodes):
    total = sum(1 for v in nodes.values() if v["type"] not in SKIP_TYPES_SCAN)
    L = [f"⊙ 结构空洞扫描 · 实质节点 {total} · 真洞 {len(hard)} · 可富化 {len(soft)}"]
    desc = {"孤儿": "0 边 · 完全断开 · P0",
            "未织入": "概念只有纯归属边（proposed/authored）· 没连进结构 · P1",
            "弱连接": "实体单线（attribution）· 实体常态 · P2"}
    order = {"孤儿": 0, "未织入": 1, "弱连接": 2}
    hard.sort(key=lambda r: (order[r["tier"]], r["domain"], r["slug"]))
    by = {}
    for r in hard:
        by.setdefault(r["tier"], []).append(r)
    for tier in ["孤儿", "未织入", "弱连接"]:
        grp = by.get(tier, [])
        if not grp:
            continue
        L.append(f"\n── {tier}（{len(grp)}）· {desc[tier]} ──")
        for r in grp:
            et = (" · 现有: " + "/".join(r["types"])) if r["types"] else ""
            L.append(f"  {r['slug']}  ({r['type']}/{r['domain']} · deg={r['deg']}{et})")
    if soft:
        soft.sort(key=lambda r: (r["domain"], r["slug"]))
        L.append(f"\n── 可横向富化（{len(soft)}）· 已 part_of 归位、缺思想边（enables/develops 候选，非洞）──")
        for r in soft:
            L.append(f"  {r['slug']}  ({r['type']}/{r['domain']} · deg={r['deg']} · 现有: {'/'.join(r['types'])})")
    L.append("\n→ 真洞派研究员织入边；可富化用 enables/develops 补横向思想边（富化非必须）")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="图谱遍历：从种子节点沿边辐射 N 跳")
    ap.add_argument("seed", nargs="?", help="种子节点 slug（--scan 模式可省）")
    ap.add_argument("--scan", action="store_true",
                    help="扫全库结构空洞（孤儿/挂件/仅taxonomy），不需种子")
    ap.add_argument("--depth", type=int, default=1, help="辐射跳数（默认 1）")
    ap.add_argument("--dir", choices=["out", "in", "both"], default="both",
                    help="边方向：out=它指向的 / in=指向它的 / both（默认）")
    ap.add_argument("--types", default="", help="只走这些边类型（逗号分隔）")
    ap.add_argument("--skip-types", default="", help="跳过这些边类型（逗号分隔）")
    ap.add_argument("--cross-only", action="store_true", help="只要跨域边")
    ap.add_argument("--include-retired", action="store_true", help="含已退役的边")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--vault", default=".", help="库根目录（默认当前目录）")
    a = ap.parse_args()

    types = set(t.strip() for t in a.types.split(",") if t.strip()) or None
    skip = set(t.strip() for t in a.skip_types.split(",") if t.strip()) or None

    nodes, out_adj, in_adj = load_graph(a.vault, a.include_retired)

    if a.scan:
        global ANCHOR_TYPES, IDEA_TYPES, ATTRIB_ONLY
        ANCHOR_TYPES, IDEA_TYPES, ATTRIB_ONLY = load_scan_vocab(a.vault)
        hard, soft = scan_holes(nodes, out_adj, in_adj)
        print(json.dumps({"hard": hard, "soft": soft}, ensure_ascii=False, indent=2) if a.json
              else render_scan(hard, soft, nodes))
        return
    if not a.seed:
        ap.error("需要种子 slug，或用 --scan 扫全库")

    rings, subedges = expand(a.seed, a.depth, a.dir, nodes, out_adj, in_adj,
                             types=types, skip_types=skip, cross_only=a.cross_only)

    if a.json:
        print(json.dumps({
            "seed": a.seed, "depth": a.depth,
            "rings": rings,
            "subedges": [{"from": f, "to": t, "type": ty, "dir": d}
                         for f, t, ty, d in subedges],
        }, ensure_ascii=False, indent=2))
    else:
        print(render_text(a.seed, a.depth, rings, subedges, nodes))


if __name__ == "__main__":
    main()
