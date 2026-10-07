"""
CAD Intermediate Representation (CADIR) — Validator
Performs strict semantic validation, feature dependency DAG resolution,
topological sorting, and parameter integrity checking for CADIR documents.
"""
from typing import List, Dict, Set, Optional
from pydantic import BaseModel, Field
from collections import deque
from .schema import CADIRDocument, CADIRFeature


class CADIRValidationResult(BaseModel):
    """Structured report returned from CADIR validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    topological_order: List[str] = Field(default_factory=list)
    feature_depths: Dict[str, int] = Field(default_factory=dict)


def validate_cadir_document(doc: CADIRDocument) -> CADIRValidationResult:
    """
    Perform deep semantic validation of a CADIR document.
    Ensures feature dependencies form a valid acyclic graph (DAG),
    all references exist, dimensions are positive, and construction order is sound.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Sketch ID Uniqueness and Integrity
    sketch_ids: Set[str] = set()
    for sketch in doc.sketches:
        if not sketch.id:
            errors.append("Encountered a sketch with empty or missing ID.")
        elif sketch.id in sketch_ids:
            errors.append(f"Duplicate sketch ID detected: '{sketch.id}'.")
        else:
            sketch_ids.add(sketch.id)

        if not sketch.primitives and not sketch.inner_loops:
            warnings.append(f"Sketch '{sketch.id}' has no primitives defined.")

    # 2. Feature ID Uniqueness
    feature_ids: Set[str] = set()
    feature_index_map: Dict[str, int] = {}
    for idx, feature in enumerate(doc.features):
        if not feature.id:
            errors.append(f"Feature at index {idx} has an empty or missing ID.")
            continue
        if feature.id in feature_ids:
            errors.append(f"Duplicate feature ID detected: '{feature.id}'.")
        else:
            feature_ids.add(feature.id)
            feature_index_map[feature.id] = idx

    # 3. Sketch References & Feature-Specific Parameter Sanity
    for feature in doc.features:
        f_type = feature.feature_type
        fid = feature.id

        # Sketch reference check
        if feature.sketch_id is not None:
            if feature.sketch_id not in sketch_ids:
                errors.append(
                    f"Feature '{fid}' ({f_type}) references non-existent sketch '{feature.sketch_id}'."
                )

        # Feature type specific parameter rules
        if f_type == "box":
            if feature.length is None or feature.length <= 0:
                errors.append(f"Box feature '{fid}' requires positive 'length'.")
            if feature.width is None or feature.width <= 0:
                errors.append(f"Box feature '{fid}' requires positive 'width'.")
            if feature.height is None or feature.height <= 0:
                errors.append(f"Box feature '{fid}' requires positive 'height'.")

        elif f_type == "cylinder":
            if feature.radius is None or feature.radius <= 0:
                errors.append(f"Cylinder feature '{fid}' requires positive 'radius'.")
            if feature.height is None or feature.height <= 0:
                errors.append(f"Cylinder feature '{fid}' requires positive 'height'.")

        elif f_type == "sphere":
            if feature.radius is None or feature.radius <= 0:
                errors.append(f"Sphere feature '{fid}' requires positive 'radius'.")

        elif f_type == "extrude":
            if not feature.sketch_id:
                errors.append(f"Extrude feature '{fid}' requires a 'sketch_id'.")
            if feature.distance is None or feature.distance <= 0:
                errors.append(f"Extrude feature '{fid}' requires positive 'distance'.")

        elif f_type == "revolve":
            if not feature.sketch_id:
                errors.append(f"Revolve feature '{fid}' requires a 'sketch_id'.")

        elif f_type == "hole":
            if feature.diameter is None or feature.diameter <= 0:
                errors.append(f"Hole feature '{fid}' requires positive 'diameter'.")
            if feature.depth is None or feature.depth <= 0:
                errors.append(f"Hole feature '{fid}' requires positive 'depth'.")
            if not feature.dependencies:
                errors.append(
                    f"Hole feature '{fid}' must have dependencies declaring the target solid it cuts into."
                )

        elif f_type in ("fillet", "chamfer"):
            if f_type == "fillet" and (feature.radius is None or feature.radius <= 0):
                errors.append(f"Fillet feature '{fid}' requires positive 'radius'.")
            if f_type == "chamfer" and (feature.distance is None or feature.distance <= 0):
                errors.append(f"Chamfer feature '{fid}' requires positive 'distance'.")
            if not feature.dependencies:
                errors.append(
                    f"{f_type.capitalize()} feature '{fid}' must declare dependency on the target solid whose edges are modified."
                )

        elif f_type in ("boolean_cut", "boolean_union", "boolean_intersect"):
            if not feature.tool_feature_id and len(feature.dependencies) < 2:
                errors.append(
                    f"Boolean feature '{fid}' requires 'tool_feature_id' or at least 2 dependency features."
                )

    # 4. Dependency Existence & Topological Sequence Check
    for feature in doc.features:
        curr_idx = feature_index_map.get(feature.id, -1)
        for dep in feature.dependencies:
            if dep not in feature_ids:
                errors.append(
                    f"Feature '{feature.id}' declares dependency on non-existent feature '{dep}'."
                )
            else:
                dep_idx = feature_index_map.get(dep, -1)
                if dep_idx >= curr_idx and curr_idx != -1:
                    errors.append(
                        f"Feature '{feature.id}' (index {curr_idx}) forward-references dependency '{dep}' (index {dep_idx}). "
                        "Dependencies must strictly precede the dependent feature."
                    )

    # 5. Graph Cycle Detection & Topological Sort (Kahn's Algorithm)
    topological_order: List[str] = []
    feature_depths: Dict[str, int] = {}

    if not errors:
        in_degree: Dict[str, int] = {fid: 0 for fid in feature_ids}
        adjacency: Dict[str, List[str]] = {fid: [] for fid in feature_ids}

        for feature in doc.features:
            for dep in feature.dependencies:
                adjacency[dep].append(feature.id)
                in_degree[feature.id] += 1

        queue = deque([fid for fid, deg in in_degree.items() if deg == 0])
        for fid in queue:
            feature_depths[fid] = 0

        while queue:
            curr = queue.popleft()
            topological_order.append(curr)
            curr_depth = feature_depths.get(curr, 0)

            for neighbor in adjacency[curr]:
                in_degree[neighbor] -= 1
                feature_depths[neighbor] = max(
                    feature_depths.get(neighbor, 0), curr_depth + 1
                )
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topological_order) != len(feature_ids):
            errors.append(
                "Cycle detected in feature dependency graph. Features cannot have circular dependencies."
            )

    is_valid = len(errors) == 0
    return CADIRValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        topological_order=topological_order if is_valid else [],
        feature_depths=feature_depths if is_valid else {},
    )
