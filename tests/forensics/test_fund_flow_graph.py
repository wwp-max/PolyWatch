"""Tests for forensics.fund_flow_graph module."""

from __future__ import annotations

from pathlib import Path

from forensics.fund_flow_graph import create_wallet_graph


def test_create_wallet_graph_generates_dot(tmp_path: Path) -> None:
    edges = [
        ("wallet_a", "wallet_b", "100 USDC"),
        ("wallet_b", "polymarket_contract", "80 USDC"),
    ]
    output_prefix = tmp_path / "case_001_fund_flow"

    result = create_wallet_graph(edges, output_prefix)

    dot_path = Path(result["dot_path"])
    assert dot_path.exists()
    dot_content = dot_path.read_text(encoding="utf-8")
    assert "wallet_a" in dot_content
    assert "wallet_b" in dot_content
    assert "polymarket_contract" in dot_content


def test_create_wallet_graph_graceful_degradation_without_graphviz(
    monkeypatch, tmp_path: Path
) -> None:
    import forensics.fund_flow_graph as module

    def always_fail(_name: str):
        raise ImportError("graphviz not installed")

    monkeypatch.setattr(module.importlib, "import_module", always_fail)

    edges = [("wallet_x", "wallet_y", "50 USDC")]
    output_prefix = tmp_path / "case_missing_binary"
    result = create_wallet_graph(edges, output_prefix)

    assert Path(result["dot_path"]).exists()
    assert result["png_path"] == ""


def test_create_wallet_graph_graceful_degradation_executable_missing(
    monkeypatch, tmp_path: Path
) -> None:
    import forensics.fund_flow_graph as module

    class FakeExecutableNotFound(Exception):
        pass

    class FakeDigraph:
        def __init__(self, _name: str, format: str):
            self.source = "digraph fund_flow {\n  rankdir=LR;\n}\n"

        def attr(self, **_kwargs):
            return None

        def edge(self, source: str, target: str, label: str):
            self.source = (
                "digraph fund_flow {\n"
                "  rankdir=LR;\n"
                f'  "{source}" -> "{target}" [label="{label}"];\n'
                "}\n"
            )

        def render(self, **_kwargs):
            raise FakeExecutableNotFound("dot not found")

    monkeypatch.setattr(
        module,
        "_resolve_graphviz",
        lambda: (FakeDigraph, FakeExecutableNotFound),
    )

    output_prefix = tmp_path / "case_exec_missing"
    result = create_wallet_graph([("wallet_a", "wallet_b", "10 USDC")], output_prefix)

    assert Path(result["dot_path"]).exists()
    assert result["png_path"] == ""
