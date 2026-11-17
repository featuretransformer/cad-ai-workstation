"""
CAD Intermediate Representation (CADIR) — Validator
Performs strict semantic validation, feature dependency DAG resolution,
topological sorting, parameter integrity checking, symbolic parameter resolution,
and pre-execution engineering assertions.
"""
from typing import List, Dict, Set, Optional, Tuple, Any
from pydantic import BaseModel, Field
from collections import deque
import math
import re
from .schema import CADIRDocument, CADIRFeature


class SafeMathEvaluator:
    """Safely evaluates algebraic and geometric constraint expressions."""

    ALLOWED_NAMES = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "atan2": math.atan2,
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "pi": math.pi,
        "e": math.e,
        "True": True,
        "False": False,
    }

    @classmethod
    def eval(cls, expr: str, context: Dict[str, Any]) -> Any:
        if not isinstance(expr, str):
            return expr

        # Replace $var with context value
        def replace_var(m):
            vname = m.group(1)
            if vname in context:
                return str(context[vname])
            return m.group(0)

        cleaned = re.sub(r"\$([a-zA-Z_][a-zA-Z0-9_]*)", replace_var, expr)

        # Safety check: allow only mathematical characters and allowed names
        for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", cleaned):
            if token not in cls.ALLOWED_NAMES:
                raise ValueError(f"Disallowed token in expression: '{token}'")

        return eval(cleaned, {"__builtins__": {}}, cls.ALLOWED_NAMES)


def resolve_symbolic_parameters(doc: CADIRDocument) -> Tuple[CADIRDocument, List[str]]:
    """Resolve global parametric formulas and pre-execution assertions."""
    errors: List[str] = []
    context: Dict[str, Any] = {}

    # Multi-pass parameter resolution to handle variable interdependencies
    raw_params = dict(doc.parameters or {})
    unresolved = dict(raw_params)
    max_passes = max(len(raw_params) * 2, 10)
    passes = 0

    while unresolved and passes < max_passes:
        passes += 1
        progress = False
        for k, v in list(unresolved.items()):
            if isinstance(v, (int, float)):
                context[k] = float(v)
                del unresolved[k]
                progress = True
            elif isinstance(v, str):
                try:
                    val = SafeMathEvaluator.eval(v, context)
                    context[k] = float(val)
                    del unresolved[k]
                    progress = True
                except Exception:
                    pass
        if not progress:
            break

    if unresolved:
        for k in unresolved:
            errors.append(f"Unresolvable cyclic or missing symbolic parameter: '{k}'")

    doc.parameters = context

    # Evaluate engineering assertions
    for assertion in (getattr(doc, "assertions", None) or []):
        try:
            res = SafeMathEvaluator.eval(assertion, context)
            if not bool(res):
                errors.append(f"Pre-execution engineering assertion failed: {assertion}")
        except Exception as e:
            errors.append(f"Failed to evaluate assertion '{assertion}': {e}")

    # Resolve symbolic references on features
    for f in doc.features:
        for field in ("length", "width", "height", "radius", "diameter", "distance", "depth", "thickness", "pattern_radius"):
            val = getattr(f, field, None)
            if isinstance(val, str) and ("$" in val or any(op in val for op in ("+", "-", "*", "/"))):
                try:
                    num_val = float(SafeMathEvaluator.eval(val, context))
                    setattr(f, field, num_val)
                    if field == "radius" and (f.diameter is None or isinstance(f.diameter, str)):
                        f.diameter = num_val * 2.0
                    elif field == "diameter" and (f.radius is None or isinstance(f.radius, str)):
                        f.radius = num_val / 2.0
                except Exception:
                    errors.append(f"Feature '{f.id}' references undefined parameter: '{val}'")

    return doc, errors


class CADIRValidationResult(BaseModel):
    """Structured report returned from CADIR validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    topological_order: List[str] = Field(default_factory=list)
    feature_depths: Dict[str, int] = Field(default_factory=dict)
    resolved_parameters: Dict[str, Any] = Field(default_factory=dict)


def validate_cadir_document(doc: CADIRDocument) -> CADIRValidationResult:
    """
    Perform deep semantic validation of a CADIR document.
    Ensures feature dependencies form a valid acyclic graph (DAG),
    all references exist, dimensions are positive, and construction order is sound.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # 0. Resolve symbolic parameters and engineering assertions
    doc, sym_errs = resolve_symbolic_parameters(doc)
    errors.extend(sym_errs)

    # 1. Sketch ID Uniqueness and Integrity
    sketch_ids: Set[str] = set()
    for sketch in doc.sketches:
        if not sketch.id:
            errors.append("Encountered a sketch with empty or missing ID.")
        elif sketch.id in sketch_ids:
            errors.append(f"Duplicate sketch ID detected: '{sketch.id}'.")
        else:
            sketch_ids.add(sketch.id)

        if not sketch.primitives and not sketch.inner_loops and not getattr(sketch, "entities", []):
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

        if feature.sketch_id is not None:
            if feature.sketch_id not in sketch_ids:
                errors.append(
                    f"Feature '{fid}' ({f_type}) references non-existent sketch '{feature.sketch_id}'."
                )

        if f_type == "box":
            if feature.length is None or feature.length <= 0:
                errors.append(f"Box feature '{fid}' requires positive 'length'.")
            if feature.width is None or feature.width <= 0:
                errors.append(f"Box feature '{fid}' requires positive 'width'.")
            if feature.height is None or feature.height <= 0:
                errors.append(f"Box feature '{fid}' requires positive 'height'.")

        elif f_type == "cylinder":
            if (feature.height is None or feature.height <= 0) and feature.length and feature.length > 0:
                feature.height = feature.length
            elif (feature.height is None or feature.height <= 0) and feature.depth and feature.depth > 0:
                feature.height = feature.depth
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
            if (feature.distance is None or feature.distance <= 0) and feature.depth and feature.depth > 0:
                feature.distance = feature.depth
            if not feature.sketch_id and not getattr(feature, "profile", None):
                if (feature.radius and feature.radius > 0) or (feature.diameter and feature.diameter > 0):
                    feature.feature_type = "cylinder"
                    if not feature.height and feature.distance:
                        feature.height = feature.distance
                elif feature.length and feature.width and feature.height:
                    feature.feature_type = "box"

        elif f_type == "revolve":
            if feature.angle is None or feature.angle <= 0:
                feature.angle = 360.0
            if not feature.sketch_id and not getattr(feature, "profile", None):
                if (feature.radius and feature.radius > 0) or (feature.diameter and feature.diameter > 0):
                    feature.feature_type = "cylinder"
                    if not feature.height:
                        feature.height = 30.0

        elif f_type == "hole":
            if (feature.radius is None or feature.radius <= 0) and feature.diameter and feature.diameter > 0:
                feature.radius = feature.diameter / 2.0
            if (feature.diameter is None or feature.diameter <= 0) and feature.radius and feature.radius > 0:
                feature.diameter = feature.radius * 2.0
            if feature.radius is None or feature.radius <= 0:
                errors.append(f"Hole feature '{fid}' requires positive 'radius' or 'diameter'.")

        elif f_type in ("fillet", "chamfer"):
            if f_type == "fillet" and (feature.radius is None or feature.radius <= 0):
                errors.append(f"Fillet feature '{fid}' requires positive 'radius'.")
            elif f_type == "chamfer" and (feature.distance is None or feature.distance <= 0):
                errors.append(f"Chamfer feature '{fid}' requires positive 'distance'.")

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
            errors.append("Cycle detected in feature dependency graph.")

    is_valid = len(errors) == 0
    return CADIRValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        topological_order=topological_order if is_valid else [],
        feature_depths=feature_depths if is_valid else {},
        resolved_parameters=doc.parameters or {},
    )
