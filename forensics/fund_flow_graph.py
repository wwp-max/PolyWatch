from __future__ import annotations

import importlib
from pathlib import Path
from typing import Iterable


class GraphvizExecutableNotFound(Exception):
    """Fallback exception when graphviz backend exception is unavailable."""


def create_wallet_graph(
    edges: Iterable[tuple[str, str, str]],
    output_prefix: str | Path,
) -> dict[str, str]:
    """Create wallet graph, always write .dot, render .png when possible."""
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    dot_path = Path(f"{prefix}.dot")
    png_path = Path(f"{prefix}.png")

    digraph_cls, executable_not_found = _resolve_graphviz()
    if digraph_cls is None:
        _write_dot_fallback(edges, dot_path)
        return {"dot_path": str(dot_path), "png_path": ""}

    graph = digraph_cls("fund_flow", format="png")
    graph.attr(rankdir="LR")
    for source, target, label in edges:
        graph.edge(source, target, label=label)

    dot_path.write_text(graph.source, encoding="utf-8")
    try:
        graph.render(filename=str(prefix), cleanup=True, format="png")
        return {"dot_path": str(dot_path), "png_path": str(png_path)}
    except executable_not_found:
        return {"dot_path": str(dot_path), "png_path": ""}


def _resolve_graphviz() -> tuple[type | None, type[Exception]]:
    try:
        graphviz_module = importlib.import_module("graphviz")
        backend_module = importlib.import_module("graphviz.backend")
        digraph_cls = getattr(graphviz_module, "Digraph")
        executable_not_found = getattr(backend_module, "ExecutableNotFound")
        return digraph_cls, executable_not_found
    except Exception:
        return None, GraphvizExecutableNotFound


def _write_dot_fallback(edges: Iterable[tuple[str, str, str]], dot_path: Path) -> None:
    lines = ["digraph fund_flow {", "  rankdir=LR;"]
    for source, target, label in edges:
        lines.append(f'  "{source}" -> "{target}" [label="{label}"];')
    lines.append("}")
    dot_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
