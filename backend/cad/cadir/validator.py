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
            # Auto-normalize length/depth into height if height is missing
            if (feature.height is None or feature.height <= 0) and feature.length and feature.length > 0:
                feature.height = feature.length
            elif (feature.height is None or feature.height <= 0) and feature.depth and feature.depth > 0:
                feature.height = feature.depth
            # Auto-normalize diameter into radius if radius is missing
            if (feature.radius is None or feature.radius <= 0) and feature.diameter and feature.diameter > 0:
                feature.radius = feature.diameter / 2.0

            if feature.radius is None or feature.radius <= 0:
                errors.append(f"Cylinder feature '{fid}' requires positive 'radius'.")
            if feature.height is None or feature.height <= 0:
                errors.append(f"Cylinder feature '{fid}' requires positive 'height'.")

        elif f_type == "sphere":
            if (feature.radius is None or feature.radius <= 0) and feature.diameter and feature.diameter > 0:
                feature.radius = feature.diameter / 2.0
            if feature.radius is None or feature.radius <= 0:
                errors.append(f"Sphere feature '{fid}' requires positive 'radius'.")

        elif f_type == "extrude":
            # Auto-normalize distance from depth if distance is missing
            if (feature.distance is None or feature.distance <= 0) and feature.depth and feature.depth > 0:
                feature.distance = feature.depth
            # If sketch_id is missing, normalize into cylinder or box primitive
            if not feature.sketch_id:
                if (feature.radius and feature.radius > 0) or (feature.diameter and feature.diameter > 0):
                    feature.feature_type = "cylinder"
                    f_type = "cylinder"
                    if not feature.height:
                        feature.height = feature.distance or feature.depth or feature.length or 10.0
                    if not feature.radius and feature.diameter:
                        feature.radius = feature.diameter / 2.0
                elif feature.length and feature.width:
                    feature.feature_type = "box"
                    f_type = "box"
                    if not feature.height:
                        feature.height = feature.distance or feature.depth or 10.0
                elif feature.height and feature.height > 0:
                    # LLM often generates extrude with only height/depth (e.g. bolt heads)
                    # Convert to cylinder with a default radius
                    feature.feature_type = "cylinder"
                    f_type = "cylinder"
                    if not feature.radius:
                        feature.radius = feature.height * 0.8  # reasonable default
                elif feature.depth and feature.depth > 0:
                    # depth-only extrude → cylinder with default radius
                    feature.feature_type = "cylinder"
                    f_type = "cylinder"
                    feature.height = feature.depth
                    if not feature.radius:
                        feature.radius = feature.depth * 0.8
                else:
                    errors.append(f"Extrude feature '{fid}' requires a 'sketch_id' or dimensions (radius/diameter, length/width, or height/depth).")
            if f_type == "extrude" and (feature.distance is None or feature.distance <= 0):
                errors.append(f"Extrude feature '{fid}' requires positive 'distance'.")

        elif f_type == "revolve":
            if not feature.sketch_id:
                if feature.operation == "cut":
                    feature.feature_type = "hole"
                    f_type = "hole"
                    if not feature.diameter and feature.radius:
                        feature.diameter = feature.radius * 2.0
                    elif not feature.diameter:
                        feature.diameter = 10.0
                    if not feature.depth:
                        feature.depth = feature.height or 5.0
                elif feature.radius or feature.diameter:
                    feature.feature_type = "cylinder"
                    f_type = "cylinder"
                    if not feature.height:
                        feature.height = feature.distance or feature.depth or 20.0
                else:
                    errors.append(f"Revolve feature '{fid}' requires a 'sketch_id'.")

        elif f_type == "hole":
            # Auto-normalize radius into diameter if diameter is missing
            if (feature.diameter is None or feature.diameter <= 0) and feature.radius and feature.radius > 0:
                feature.diameter = feature.radius * 2.0
            # Auto-normalize diameter into radius if radius is missing
            if (feature.radius is None or feature.radius <= 0) and feature.diameter and feature.diameter > 0:
                feature.radius = feature.diameter / 2.0
            if feature.diameter is None or feature.diameter <= 0:
                feature.diameter = 8.0
                feature.radius = 4.0
            # Auto-default depth from height or length
            if (feature.depth is None or feature.depth <= 0) and feature.height and feature.height > 0:
                feature.depth = feature.height
            elif (feature.depth is None or feature.depth <= 0) and feature.length and feature.length > 0:
                feature.depth = feature.length
            if feature.depth is None or feature.depth <= 0:
                feature.depth = 20.0
            if not feature.dependencies and feature_index_map.get(fid, 0) > 0:
                prev_id = doc.features[feature_index_map[fid] - 1].id
                feature.dependencies = [prev_id]
            elif not feature.dependencies:
                errors.append(
                    f"Hole feature '{fid}' must have dependencies declaring the target solid it cuts into."
                )

            # Auto-clamp hole radius so it does not exceed the parent body
            if feature.dependencies:
                parent_id = feature.dependencies[0]
                parent_feat = next((pf for pf in doc.features if pf.id == parent_id), None)
                if not parent_feat and feature_index_map.get(fid, 0) > 0:
                    parent_feat = doc.features[feature_index_map[fid] - 1]
                if parent_feat:
                    if parent_feat.feature_type in ("cylinder", "sphere") and parent_feat.radius:
                        if feature.radius and feature.radius >= parent_feat.radius:
                            feature.radius = round(parent_feat.radius * 0.55, 2)
                            feature.diameter = feature.radius * 2.0
                    elif parent_feat.feature_type == "extrude" and parent_feat.sketch_id:
                        sk = next((s for s in doc.sketches if s.id == parent_feat.sketch_id), None)
                        if sk and sk.primitives:
                            prim = sk.primitives[0]
                            prim_r = getattr(prim, "radius", None)
                            if prim_r and feature.radius and feature.radius >= prim_r:
                                feature.radius = round(prim_r * 0.55, 2)
                                feature.diameter = feature.radius * 2.0
                    elif parent_feat.feature_type == "box" and parent_feat.length and parent_feat.width:
                        max_r = min(parent_feat.length, parent_feat.width) / 2.0
                        if feature.radius and feature.radius >= max_r:
                            feature.radius = round(max_r * 0.55, 2)
                            feature.diameter = feature.radius * 2.0

        elif f_type == "pocket":
            # Auto-normalize radius/diameter
            if (feature.diameter is None or feature.diameter <= 0) and feature.radius and feature.radius > 0:
                feature.diameter = feature.radius * 2.0
            if (feature.radius is None or feature.radius <= 0) and feature.diameter and feature.diameter > 0:
                feature.radius = feature.diameter / 2.0
            if (not feature.length or not feature.width) and (not feature.radius and not feature.diameter):
                errors.append(f"Pocket feature '{fid}' requires length and width, or radius/diameter.")
            if not feature.depth and not feature.height:
                feature.depth = 10.0
            elif not feature.depth and feature.height:
                feature.depth = feature.height
            if not feature.dependencies and feature_index_map.get(fid, 0) > 0:
                prev_id = doc.features[feature_index_map[fid] - 1].id
                feature.dependencies = [prev_id]

        elif f_type in ("fillet", "chamfer"):
            if f_type == "fillet" and (feature.radius is None or feature.radius <= 0):
                errors.append(f"Fillet feature '{fid}' requires positive 'radius'.")
            if f_type == "chamfer" and (feature.distance is None or feature.distance <= 0):
                feature.distance = feature.length or 1.0
            if not feature.dependencies and feature_index_map.get(fid, 0) > 0:
                prev_id = doc.features[feature_index_map[fid] - 1].id
                feature.dependencies = [prev_id]
            elif not feature.dependencies:
                errors.append(
                    f"{f_type.capitalize()} feature '{fid}' must declare dependency on the target solid whose edges are modified."
                )

        elif f_type == "sweep":
            if not feature.sketch_id:
                errors.append(f"Sweep feature '{fid}' requires a profile 'sketch_id'.")
            if not feature.path_sketch_id and not feature.distance and not feature.length:
                feature.distance = 20.0  # fallback linear sweep

        elif f_type == "loft":
            if len(feature.section_sketch_ids) < 2 and not feature.sketch_id:
                errors.append(f"Loft feature '{fid}' requires at least 2 sketches in 'section_sketch_ids'.")

        elif f_type == "shell":
            if feature.thickness is None or feature.thickness <= 0:
                feature.thickness = 2.0  # reasonable default wall thickness
            if not feature.dependencies and feature_index_map.get(fid, 0) > 0:
                prev_id = doc.features[feature_index_map[fid] - 1].id
                feature.dependencies = [prev_id]

        elif f_type == "rib":
            if feature.rib_thickness is None or feature.rib_thickness <= 0:
                feature.rib_thickness = feature.thickness or 3.0
            if not feature.dependencies and feature_index_map.get(fid, 0) > 0:
                prev_id = doc.features[feature_index_map[fid] - 1].id
                feature.dependencies = [prev_id]

        elif f_type == "thread":
            if (feature.thread_diameter is None or feature.thread_diameter <= 0):
                feature.thread_diameter = feature.diameter or 10.0
            if (feature.thread_length is None or feature.thread_length <= 0):
                feature.thread_length = feature.length or feature.height or 25.0
            if feature.pitch is None or feature.pitch <= 0:
                # ISO coarse pitch approximation for metric threads
                d = feature.thread_diameter
                feature.pitch = round(0.15 * d + 0.25, 2) if d > 3 else 0.5
            if not feature.dependencies and feature_index_map.get(fid, 0) > 0:
                prev_id = doc.features[feature_index_map[fid] - 1].id
                feature.dependencies = [prev_id]

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
