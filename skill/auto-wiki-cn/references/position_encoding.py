"""图谱位置编码（Positional Encoding）：给本体图谱一个"校准"的、确定性的坐标系。

动机
    力导向布局每次打开都重新模拟，节点位置是布局副产品，不携带语义。
    本脚本把"方位"变成数据：
      · y 轴 = 本体抽象层级（机制在上，机构/工具/指标递降，事件/分析在下）
      · x 轴 = 图拉普拉斯 Fiedler 向量（谱坐标）——同社区的节点自然聚在一起
      · pe   = 每个节点一个 sin/cos 展开的位置编码向量（可用于相似度召回）

为什么是拉普拉斯特征向量而不是直接抄 Transformer 的 sin/cos？
    Transformer 的正弦位置编码假设输入有全序（token 0,1,2,...）。
    数学上，sin/cos 正弦基恰好是"链状图"（path graph）拉普拉斯矩阵的特征向量。
    图没有全序，但有拉普拉斯——其特征向量就是 sin/cos 在任意图上的推广
    （图信号处理里的"图傅里叶基"；Graph Transformer 的 Laplacian PE 同源）。
    所以这里：先算谱坐标 φ（图上的"位置"），再对 φ 做多频率 sin/cos 展开得 pe 向量，
    与 Attention is All You Need 的构造一脉相承。

用法
    python position_encoding.py <wiki_dir>          # 写出 <wiki_dir>/_positions.json
    之后运行 python schema.py --report <wiki_dir>   # 报告自动读取并启用"校准布局"

纯标准库实现（幂迭代求特征向量），不引入 numpy。
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# 复用 schema.py 的页面/关系抽取（含 data.db relations 合并）
sys.path.insert(0, str(Path(__file__).parent))
from schema import collect_report_data  # noqa: E402

# ── 语义 y 轴：本体抽象层级（小 = 上方 = 更抽象）────────────────
# 机制是耐用逻辑（T2），统摄一切 → 顶层；机构施动；工具被运行；
# 指标是观测面（T0 挂靠处）；事件是时间戳；分析/来源是派生视图。
LAYER_BY_SUBTYPE = {"institution": 1, "instrument": 2, "indicator": 3}
LAYER_BY_TYPE = {
    "concept": 0, "mental-model": 0,
    "entity": 2,
    "event": 4,
    "analysis": 5, "source": 5,
}
DEFAULT_LAYER = 3
LAYER_GAP = 240      # 层间距（px）
X_SPAN = 1600        # x 轴总宽度（px）
PE_FREQS = 4         # sin/cos 展开频率数 → pe 维度 = 2 坐标 × 2 函数 × 4 频率 = 16


def _node_layer(node: dict) -> int:
    return LAYER_BY_SUBTYPE.get(node.get("subtype") or "",
                                 LAYER_BY_TYPE.get(node.get("type") or "", DEFAULT_LAYER))


def _connected_components(ids: list[str], adj: dict[str, set]) -> list[list[str]]:
    seen, comps = set(), []
    for start in ids:
        if start in seen:
            continue
        comp, stack = [], [start]
        seen.add(start)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in adj.get(cur, ()):  # BFS/DFS 均可，顺序不影响结果集
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(sorted(comp))  # 排序保证确定性
    return comps


def _spectral_coords(comp: list[str], adj: dict[str, set]) -> dict[str, tuple[float, float]]:
    """对单个连通分量求归一化拉普拉斯第 2、3 小特征向量（Fiedler 及其次维）。

    幂迭代求 M = I + D^{-1/2} A D^{-1/2} 的最大特征向量（即 L 的最小），
    对平凡向量 D^{1/2}·1 做 Gram-Schmidt 紧缩后，收敛到 Fiedler 向量。
    """
    n = len(comp)
    if n == 1:
        return {comp[0]: (0.0, 0.0)}
    idx = {s: i for i, s in enumerate(comp)}
    deg = [max(1, len(adj[s] & set(comp))) for s in comp]
    inv_sqrt = [1.0 / math.sqrt(d) for d in deg]

    def matvec(v: list[float]) -> list[float]:
        out = list(v)  # I·v
        for s in comp:
            i = idx[s]
            acc = 0.0
            for nb in adj[s]:
                j = idx.get(nb)
                if j is not None:
                    acc += inv_sqrt[j] * v[j]
            out[i] += inv_sqrt[i] * acc
        return out

    def normalize(v: list[float]) -> list[float]:
        nrm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / nrm for x in v]

    def deflate(v: list[float], basis: list[list[float]]) -> list[float]:
        for b in basis:
            dot = sum(x * y for x, y in zip(v, b))
            v = [x - dot * y for x, y in zip(v, b)]
        return v

    trivial = normalize([math.sqrt(d) for d in deg])
    basis = [trivial]
    eigvecs: list[list[float]] = []
    for k in range(2):
        # 确定性初始向量（不用 random，保证可重现）
        v = normalize([math.sin((i + 1) * 12.9898 * (k + 1)) for i in range(n)])
        for _ in range(500):
            v = normalize(deflate(matvec(v), basis))
        eigvecs.append(v)
        basis.append(v)

    def rescale(v: list[float]) -> list[float]:
        lo, hi = min(v), max(v)
        span = (hi - lo) or 1.0
        return [(x - lo) / span for x in v]

    phi1, phi2 = rescale(eigvecs[0]), rescale(eigvecs[1])
    return {s: (phi1[idx[s]], phi2[idx[s]]) for s in comp}


def compute_positions(wiki_dir: Path) -> dict:
    data = collect_report_data(wiki_dir)
    nodes = {n["id"]: n for n in data["nodes"]}

    # 邻接表（无向，含 frontmatter + data.db 合并后的全部边；悬空目标也入图）
    adj: dict[str, set] = {}
    all_ids = set(nodes)
    for e in data["edges"]:
        a, b = e["from"], e["to"]
        all_ids.update((a, b))
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    for s in all_ids:
        adj.setdefault(s, set())
    ids = sorted(all_ids)

    # 谱坐标：按连通分量分别求，分量沿 x 轴按规模依次排开
    coords: dict[str, tuple[float, float]] = {}
    comps = sorted(_connected_components(ids, adj), key=len, reverse=True)
    total = sum(len(c) for c in comps) or 1
    x_cursor = 0.0
    for comp in comps:
        width = max(120.0, X_SPAN * len(comp) / total)
        local = _spectral_coords(comp, adj)
        for s, (p1, p2) in local.items():
            coords[s] = (x_cursor + p1 * width, p2)
        x_cursor += width + 80

    # 层级 y：悬空节点（没建页）取邻居层级均值
    layers: dict[str, int] = {}
    for s in ids:
        if s in nodes:
            layers[s] = _node_layer(nodes[s])
    for s in ids:
        if s not in layers:
            nb_layers = [layers[nb] for nb in adj[s] if nb in layers]
            layers[s] = round(sum(nb_layers) / len(nb_layers)) if nb_layers else DEFAULT_LAYER

    # 同层内按 x 排序后交替微错位，减少标签重叠
    positions: dict[str, dict] = {}
    by_layer: dict[int, list[str]] = {}
    for s in ids:
        by_layer.setdefault(layers[s], []).append(s)
    for layer, members in by_layer.items():
        members.sort(key=lambda s: coords[s][0])
        for rank, s in enumerate(members):
            x, phi2 = coords[s]
            y = layer * LAYER_GAP + (rank % 2) * 56 - 28
            # pe 向量：对谱坐标 (φ1, φ2) 做多频率 sin/cos 展开（Transformer PE 的图推广）
            phi1 = (x % X_SPAN) / X_SPAN
            pe = []
            for k in range(PE_FREQS):
                f = math.pi * (2 ** k)
                pe += [round(math.sin(f * phi1), 4), round(math.cos(f * phi1), 4),
                       round(math.sin(f * phi2), 4), round(math.cos(f * phi2), 4)]
            positions[s] = {"x": round(x, 1), "y": y, "layer": layer, "pe": pe}

    return {
        "meta": {
            "method": "laplacian-fiedler-x + ontology-layer-y + sincos-pe",
            "layer_axis": "y: 0机制 1机构 2工具 3指标 4事件 5分析",
            "x_axis": "归一化拉普拉斯 Fiedler 向量（谱坐标，社区结构）",
            "pe_dims": PE_FREQS * 4,
        },
        "positions": positions,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python position_encoding.py <wiki_dir>")
        sys.exit(1)
    wiki_dir = Path(sys.argv[1])
    if not wiki_dir.is_dir():
        print(f"Not a directory: {wiki_dir}")
        sys.exit(1)
    result = compute_positions(wiki_dir)
    out = wiki_dir / "_positions.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    n = len(result["positions"])
    print(f"OK  {out}  ({n} nodes, pe {result['meta']['pe_dims']}d)")
    print("    再跑: python schema.py --report", wiki_dir, " → 报告将启用校准布局")


if __name__ == "__main__":
    main()
