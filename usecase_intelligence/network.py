"""
Use case network — loaded from data/relationships.csv
Source: all_blueprint_use_case_relationships.csv
165 directed edges covering within-function and between-function relationships.

Recommendation logic:
    GREEN  — customer has implemented this use case
    AMBER  — recommended next step based on adjacency scoring
    VETO   — excluded by customer

Usage:
    from usecase_intelligence.network import load_graph, recommend

    G = load_graph()
    recs = recommend(implemented=["Accrual Automation"], veto=[], interested=[])
"""

import os
import pandas as pd
import json
from functools import lru_cache
from collections import defaultdict

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "relationships.csv")


@lru_cache(maxsize=1)
def load_graph() -> dict:
    """
    Load relationships CSV into an adjacency dict.
    Returns:
        {
            use_case: {
                "outbound": [(target, relationship_scope, relationship_label), ...],
                "inbound":  [(source, relationship_scope, relationship_label), ...],
            }
        }
    """
    df = pd.read_csv(DATA_PATH)
    graph = defaultdict(lambda: {"outbound": [], "inbound": []})

    for _, row in df.iterrows():
        src   = row["From Use Case"]
        tgt   = row["To Use Case"]
        scope = row["Relationship Scope"]
        label = row["Relationship Label"]

        graph[src]["outbound"].append((tgt, scope, label))
        graph[tgt]["inbound"].append((src, scope, label))

    return dict(graph)


@lru_cache(maxsize=1)
def load_relationships_df() -> pd.DataFrame:
    """Return the full relationships DataFrame."""
    return pd.read_csv(DATA_PATH)


def get_adjacent(use_case: str, direction: str = "both") -> list:
    """
    Return adjacent use cases for a given node.

    Args:
        use_case:  use case name
        direction: "outbound", "inbound", or "both"
    Returns:
        List of adjacent use case names (deduplicated)
    """
    graph = load_graph()
    node = graph.get(use_case, {"outbound": [], "inbound": []})
    adjacent = []
    if direction in ("outbound", "both"):
        adjacent += [t for t, _, _ in node["outbound"]]
    if direction in ("inbound", "both"):
        adjacent += [s for s, _, _ in node["inbound"]]
    return list(set(adjacent))


def recommend(
    implemented: list,
    veto: list,
    interested: list,
    top_n: int = 5,
    scope_filter: str = None,
) -> list:
    """
    Return ranked AMBER recommendations given customer's current state.

    Scoring:
        Base score    = 1.0 per adjacency edge from an implemented use case
        Interest bonus = 0.5 if use case appears in interested list
        Scope bonus   = 0.25 for within-function edges (lower friction)
        Veto penalty  = excluded entirely

    Args:
        implemented:   use cases customer has already implemented (GREEN)
        veto:          use cases to exclude
        interested:    use cases customer expressed interest in
        top_n:         number of recommendations to return
        scope_filter:  "Within Function" or "Between Functions" or None (both)

    Returns:
        List of dicts sorted by score descending:
        [{"use_case": str, "score": float, "reasons": [str], "scope": str}]
    """
    df = load_relationships_df()
    scores = defaultdict(lambda: {"score": 0.0, "reasons": [], "scopes": set()})

    for uc in implemented:
        # Outbound edges from implemented use case
        outbound = df[df["From Use Case"] == uc]
        for _, row in outbound.iterrows():
            target = row["To Use Case"]
            scope  = row["Relationship Scope"]

            if target in implemented or target in veto:
                continue
            if scope_filter and scope != scope_filter:
                continue

            scores[target]["score"] += 1.0
            scores[target]["reasons"].append(f"Adjacent to '{uc}'")
            scores[target]["scopes"].add(scope)

            if scope == "Within Function":
                scores[target]["score"] += 0.25

        # Inbound edges to implemented use case (reverse adjacency)
        inbound = df[df["To Use Case"] == uc]
        for _, row in inbound.iterrows():
            source = row["From Use Case"]
            scope  = row["Relationship Scope"]

            if source in implemented or source in veto:
                continue
            if scope_filter and scope != scope_filter:
                continue

            scores[source]["score"] += 0.5
            scores[source]["reasons"].append(f"Leads to '{uc}'")
            scores[source]["scopes"].add(scope)

    # Interest bonus
    for uc in interested:
        if uc not in implemented and uc not in veto:
            scores[uc]["score"] += 0.5
            scores[uc]["reasons"].append("Customer expressed interest")

    # Build ranked output
    results = []
    for uc, data in scores.items():
        results.append({
            "use_case": uc,
            "score":    round(data["score"], 2),
            "reasons":  list(set(data["reasons"])),
            "scope":    "Within Function" if "Within Function" in data["scopes"] else "Between Functions",
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


def get_network_json(
    implemented: list,
    veto: list,
    recommendations: list,
) -> dict:
    """
    Return a JSON-serialisable network structure for front-end rendering.
    Node colours:
        green  — implemented
        amber  — recommended
        grey   — not yet assessed
        red    — vetoed

    Args:
        implemented:     list of GREEN use case names
        veto:            list of VETO use case names
        recommendations: output of recommend() — list of dicts with "use_case"

    Returns:
        {"nodes": [...], "edges": [...]}
    """
    df = load_relationships_df()
    rec_names = {r["use_case"] for r in recommendations}

    # Collect all relevant nodes
    all_nodes = set(implemented) | set(veto) | rec_names
    nodes = []
    for uc in all_nodes:
        if uc in implemented:
            colour = "green"
        elif uc in veto:
            colour = "red"
        elif uc in rec_names:
            colour = "amber"
        else:
            colour = "grey"
        nodes.append({"id": uc, "colour": colour})

    # Edges only between relevant nodes
    edges = []
    for _, row in df.iterrows():
        src = row["From Use Case"]
        tgt = row["To Use Case"]
        if src in all_nodes and tgt in all_nodes:
            edges.append({
                "from":  src,
                "to":    tgt,
                "scope": row["Relationship Scope"],
            })

    return {"nodes": nodes, "edges": edges}
