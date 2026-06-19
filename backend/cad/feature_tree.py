"""
Feature tree management — converts build123d code into a structured tree.
"""
import ast
import re
from typing import List, Dict, Any


def extract_features_from_code(code: str) -> List[Dict[str, Any]]:
    """
    Parse build123d code and extract a list of CAD features.
    Returns a list of feature dicts for the UI feature tree.
    """
    features = []
    lines = code.splitlines()

    # Common build123d operation patterns
    patterns = [
        (r"Box\(([^)]+)\)", "Box", "primitive"),
        (r"Cylinder\(([^)]+)\)", "Cylinder", "primitive"),
        (r"Sphere\(([^)]+)\)", "Sphere", "primitive"),
        (r"Cone\(([^)]+)\)", "Cone", "primitive"),
        (r"CounterBoreHole\(([^)]+)\)", "CounterBoreHole", "feature"),
        (r"CounterSinkHole\(([^)]+)\)", "CounterSinkHole", "feature"),
        (r"Hole\(([^)]+)\)", "Hole", "feature"),
        (r"Fillet\(([^)]+)\)", "Fillet", "modify"),
        (r"Chamfer\(([^)]+)\)", "Chamfer", "modify"),
        (r"extrude\(([^)]+)\)", "Extrude", "feature"),
        (r"revolve\(([^)]+)\)", "Revolve", "feature"),
        (r"loft\(([^)]+)\)", "Loft", "feature"),
        (r"sweep\(([^)]+)\)", "Sweep", "feature"),
        (r"Shell\(([^)]+)\)", "Shell", "modify"),
        (r"Mirror\(([^)]+)\)", "Mirror", "pattern"),
        (r"PolarLocations\(([^)]+)\)", "PolarArray", "pattern"),
        (r"GridLocations\(([^)]+)\)", "GridArray", "pattern"),
    ]

    feature_id = 1
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern, name, ftype in patterns:
            match = re.search(pattern, stripped)
            if match:
                features.append({
                    "id": f"f{feature_id}",
                    "name": name,
                    "type": ftype,
                    "params": match.group(1)[:60],
                    "line": i,
                    "suppressed": False,
                })
                feature_id += 1
                break

    return features


def build_tree(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a hierarchical feature tree from a flat feature list."""
    return {
        "root": {
            "id": "root",
            "name": "Design",
            "type": "root",
            "children": features,
        }
    }
