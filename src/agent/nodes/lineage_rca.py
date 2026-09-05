import json
from pathlib import Path


# ============================================================
# LOAD LINEAGE
# ============================================================

def load_lineage(lineage_path: str) -> dict:
    """
    Load the lineage graph from a JSON file.
    """

    path = Path(lineage_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Lineage file not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# BUILD LINEAGE GRAPH
# ============================================================

def build_graph(lineage: dict) -> dict:
    """
    Build upstream and downstream adjacency maps.
    """

    upstream = {}
    downstream = {}

    # Initialize nodes
    for node in lineage.get("nodes", []):
        name = node["name"]

        upstream.setdefault(name, set())
        downstream.setdefault(name, set())

    # Build edges
    for edge in lineage.get("edges", []):
        source = edge["source"]
        target = edge["target"]

        downstream.setdefault(source, set()).add(target)
        upstream.setdefault(target, set()).add(source)

    return {
        "upstream": upstream,
        "downstream": downstream,
    }


# ============================================================
# FIND UPSTREAM ANCESTORS
# ============================================================

def find_ancestors(stage: str, upstream: dict) -> list:
    """
    Find all upstream ancestors of a stage.
    """

    ancestors = set()

    stack = list(
        upstream.get(stage, set())
    )

    while stack:

        current = stack.pop()

        if current in ancestors:
            continue

        ancestors.add(current)

        stack.extend(
            upstream.get(current, set())
        )

    return sorted(ancestors)


# ============================================================
# FIND DOWNSTREAM DESCENDANTS
# ============================================================

def find_descendants(stage: str, downstream: dict) -> list:
    """
    Find all downstream descendants of a stage.
    """

    descendants = set()

    stack = list(
        downstream.get(stage, set())
    )

    while stack:

        current = stack.pop()

        if current in descendants:
            continue

        descendants.add(current)

        stack.extend(
            downstream.get(current, set())
        )

    return sorted(descendants)


# ============================================================
# PERFORM LINEAGE RCA
# ============================================================

def perform_lineage_rca(
    stage: str,
    lineage_path: str,
    issues: list | None = None,
) -> dict:
    """
    Perform deterministic lineage-based
    root-cause analysis.
    """

    # --------------------------------------------------------
    # Load lineage
    # --------------------------------------------------------

    lineage = load_lineage(lineage_path)

    # --------------------------------------------------------
    # Build graph
    # --------------------------------------------------------

    graph = build_graph(lineage)

    # --------------------------------------------------------
    # Validate stage
    # --------------------------------------------------------

    if stage not in graph["upstream"]:

        raise ValueError(
            f"Stage '{stage}' does not exist in lineage."
        )

    # --------------------------------------------------------
    # Find ancestors
    # --------------------------------------------------------

    ancestors = find_ancestors(
        stage,
        graph["upstream"],
    )

    # --------------------------------------------------------
    # Find descendants
    # --------------------------------------------------------

    descendants = find_descendants(
        stage,
        graph["downstream"],
    )

    # --------------------------------------------------------
    # Direct upstream
    # --------------------------------------------------------

    direct_upstream = sorted(
        graph["upstream"].get(
            stage,
            set(),
        )
    )

    # --------------------------------------------------------
    # Direct downstream
    # --------------------------------------------------------

    direct_downstream = sorted(
        graph["downstream"].get(
            stage,
            set(),
        )
    )

    # --------------------------------------------------------
    # Root cause
    # --------------------------------------------------------
    #
    # Since the DQ issue was directly detected
    # in the affected stage, that stage becomes
    # the current root-cause candidate.
    #

    root_cause_stage = stage

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {

        "affected_stage": stage,

        "issues": issues or [],

        "direct_upstream": direct_upstream,

        "upstream_ancestors": ancestors,

        "potential_root_causes": ancestors,

        "root_cause_stage": root_cause_stage,

        "direct_downstream": direct_downstream,

        "downstream_blast_radius": descendants,

        "blast_radius_count": len(descendants),
    }


# ============================================================
# ANALYZE LINEAGE
# ============================================================

def analyze_lineage(
    stage: str,
    lineage_path: str,
    issues: list | None = None,
) -> dict:
    """
    Graph-compatible wrapper used by graph.py.
    """

    return perform_lineage_rca(
        stage=stage,
        lineage_path=lineage_path,
        issues=issues,
    )


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    LINEAGE_FILE = "data/lineage/lineage.json"

    TEST_STAGE = "stg_orders"

    SAMPLE_ISSUES = [

        {
            "severity": "MEDIUM",
            "rule": "NOT_NULL",
            "column": "customer_id",
            "message": "Missing values detected",
            "count": 2,
        },

        {
            "severity": "HIGH",
            "rule": "PRICE_NON_NEGATIVE",
            "column": "price",
            "message": "Negative prices detected",
            "count": 3,
        },

        {
            "severity": "MEDIUM",
            "rule": "VALID_STATUS",
            "column": "status",
            "message": "Invalid status values detected",
            "count": 2,
        },
    ]

    # --------------------------------------------------------
    # Run RCA
    # --------------------------------------------------------

    result = perform_lineage_rca(
        stage=TEST_STAGE,
        lineage_path=LINEAGE_FILE,
        issues=SAMPLE_ISSUES,
    )

    # --------------------------------------------------------
    # Print result
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("LINEAGE RCA RESULT")
    print("=" * 60)

    print(
        "Affected stage:",
        result["affected_stage"],
    )

    print(
        "Issues:",
        result["issues"],
    )

    print(
        "Direct upstream:",
        result["direct_upstream"],
    )

    print(
        "Upstream ancestors:",
        result["upstream_ancestors"],
    )

    print(
        "Potential root causes:",
        result["potential_root_causes"],
    )

    print(
        "Root cause stage:",
        result["root_cause_stage"],
    )

    print(
        "Direct downstream:",
        result["direct_downstream"],
    )

    print(
        "Downstream blast radius:",
        result["downstream_blast_radius"],
    )

    print(
        "Blast radius count:",
        result["blast_radius_count"],
    )

    print("=" * 60)