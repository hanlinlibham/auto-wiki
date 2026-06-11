"""Graph positional encoding: a "calibrated", deterministic coordinate system for the ontology graph.

Motivation
    Force-directed layouts re-simulate on every open; node positions are a layout
    by-product and carry no semantics. This script turns "position" into data:
      · y axis = ontology abstraction layer (mechanisms on top; institutions/instruments/indicators descending; events/analyses below)
      · x axis = Fiedler vector of the graph Laplacian (spectral coordinate) — nodes in the same community naturally cluster
      · pe   = per-node sin/cos-expanded positional encoding vector (usable for similarity recall)

Why Laplacian eigenvectors instead of copying the Transformer's sin/cos directly?
    The Transformer's sinusoidal positional encoding assumes a total order on the input (tokens 0,1,2,...).
    Mathematically, the sin/cos sinusoidal basis happens to be the eigenvectors of the
    Laplacian matrix of a path graph (a "chain" graph).
    A graph has no total order, but it has a Laplacian — its eigenvectors are the
    generalization of sin/cos to arbitrary graphs (the "graph Fourier basis" in graph
    signal processing; Graph Transformers' Laplacian PE is the same idea).
    So here: first compute the spectral coordinate φ (the "position" on the graph),
    then expand φ with multi-frequency sin/cos to get the pe vector — directly in the
    lineage of the construction in Attention Is All You Need.

Usage
    python position_encoding.py <wiki_dir>          # writes <wiki_dir>/_positions.json
    then run python schema.py --report <wiki_dir>   # the report auto-loads it and enables the "calibrated layout"

Pure stdlib implementation (power iteration for eigenvectors); no numpy dependency.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# Reuse schema.py's page/relation extraction (including data.db relations merge)
sys.path.insert(0, str(Path(__file__).parent))
from schema import collect_report_data  # noqa: E402

# ── Semantic y axis: ontology abstraction layer (smaller = higher = more abstract) ──
# Mechanisms are durable logic (T2), governing everything → top layer; institutions act;
# instruments are operated; indicators are the observation surface (where T0 attaches);
# events are timestamps; analyses/sources are derived views.
LAYER_BY_SUBTYPE = {"institution": 1, "instrument": 2, "indicator": 3}
LAYER_BY_TYPE = {
    "concept": 0, "mental-model": 0,
    "entity": 2,
    "event": 4,
    "analysis": 5, "source": 5,
}
DEFAULT_LAYER = 3
LAYER_GAP = 240      # gap between layers (px)
X_SPAN = 1600        # total x-axis width (px)
PE_FREQS = 4         # number of sin/cos expansion frequencies → pe dims = 2 coords × 2 functions × 4 freqs = 16


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
            for nb in adj.get(cur, ()):  # BFS or DFS both work; order does not affect the result set
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(sorted(comp))  # sort to guarantee determinism
    return comps


def _spectral_coords(comp: list[str], adj: dict[str, set]) -> dict[str, tuple[float, float]]:
    """For a single connected component, compute the 2nd and 3rd smallest eigenvectors of the normalized Laplacian (the Fiedler vector and its next dimension).

    Power iteration finds the largest eigenvector of M = I + D^{-1/2} A D^{-1/2}
    (i.e. the smallest of L); after Gram-Schmidt deflation against the trivial
    vector D^{1/2}·1, it converges to the Fiedler vector.
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
        # Deterministic initial vector (no random, to guarantee reproducibility)
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

    # Adjacency list (undirected; all edges after frontmatter + data.db merge; dangling targets also enter the graph)
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

    # Spectral coordinates: computed per connected component; components laid out along the x axis by size
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

    # Layer y: dangling nodes (no page built) take the mean of their neighbors' layers
    layers: dict[str, int] = {}
    for s in ids:
        if s in nodes:
            layers[s] = _node_layer(nodes[s])
    for s in ids:
        if s not in layers:
            nb_layers = [layers[nb] for nb in adj[s] if nb in layers]
            layers[s] = round(sum(nb_layers) / len(nb_layers)) if nb_layers else DEFAULT_LAYER

    # Within each layer, sort by x and alternate a small offset to reduce label overlap
    positions: dict[str, dict] = {}
    by_layer: dict[int, list[str]] = {}
    for s in ids:
        by_layer.setdefault(layers[s], []).append(s)
    for layer, members in by_layer.items():
        members.sort(key=lambda s: coords[s][0])
        for rank, s in enumerate(members):
            x, phi2 = coords[s]
            y = layer * LAYER_GAP + (rank % 2) * 56 - 28
            # pe vector: multi-frequency sin/cos expansion of the spectral coords (φ1, φ2) (graph generalization of Transformer PE)
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
            "layer_axis": "y: 0 mechanism, 1 institution, 2 instrument, 3 indicator, 4 event, 5 analysis",
            "x_axis": "normalized-Laplacian Fiedler vector (spectral coordinate, community structure)",
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
    print("    Next: python schema.py --report", wiki_dir, " → the report will enable the calibrated layout")


if __name__ == "__main__":
    main()
