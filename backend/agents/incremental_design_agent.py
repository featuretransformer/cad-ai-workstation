"""
Incremental Grounded Design Agent.
Executes individual steps of the Feature Build Plan sequentially.
Each step is grounded on the cumulative CADIR geometry built so far,
eliminating spatial interference, dimensional drift, and boolean conflicts.
"""
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import copy
import json
import re
import sys
import uuid

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.state import AgentState
from cad.cadir.schema import (
    CADIRDocument,
    CADIRFeature,
    CADIRSketchProfile,
    CADIRPlane,
    CADIRCircle,
    CADIRRectangle,
    Point3D,
    Vector3D,
)
from cad.cadir.validator import validate_cadir_document
from utils.llm import get_design_llm


def _extract_features_list(raw_text: str) -> Optional[List[Dict[str, Any]]]:
    """Extracts a list of feature dictionaries from LLM output."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

    # Try direct parse of list
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "features" in data and isinstance(data["features"], list):
                return data["features"]
            # If wrapped in a single feature dict
            if "feature_type" in data:
                return [data]
    except Exception:
        pass

    # Regex search for [ ... ]
    match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", cleaned)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return data
        except Exception:
            pass

    return None


def _sanitize_raw_feature_dict(f: Dict[str, Any]) -> Dict[str, Any]:
    """Pre-processes raw LLM feature dictionary before Pydantic validation."""
    if not isinstance(f, dict):
        return {}

    ft = str(f.get("feature_type", "")).lower().strip()
    TYPE_ALIASES = {
        "through_hole": "hole",
        "blind_hole": "hole",
        "bore": "hole",
        "drill": "hole",
        "counterbore": "hole",
        "countersink": "hole",
        "round": "fillet",
        "blend": "fillet",
        "bevel": "chamfer",
        "block": "box",
        "cube": "box",
        "cuboid": "box",
        "pin": "cylinder",
        "rod": "cylinder",
        "cutout": "pocket",
        "cavity": "pocket",
        "recess": "pocket",
    }
    f["feature_type"] = TYPE_ALIASES.get(ft, ft)

    # Dimensional aliases
    if "dimensions" in f and isinstance(f["dimensions"], (list, tuple)):
        dims = f["dimensions"]
        if len(dims) >= 3:
            f.setdefault("length", dims[0])
            f.setdefault("width", dims[1])
            f.setdefault("height", dims[2])
        elif len(dims) == 2:
            f.setdefault("diameter", dims[0])
            f.setdefault("height", dims[1])

    if "size" in f and isinstance(f["size"], (list, tuple)):
        sz = f["size"]
        if len(sz) >= 3:
            f.setdefault("length", sz[0])
            f.setdefault("width", sz[1])
            f.setdefault("height", sz[2])

    FIELD_ALIASES = {
        "outer_diameter": "diameter",
        "inner_diameter": "diameter",
        "bore_diameter": "diameter",
        "hole_diameter": "diameter",
        "bore_depth": "depth",
        "hole_depth": "depth",
        "fillet_radius": "radius",
        "chamfer_distance": "distance",
        "thickness": "height",
        "wall_thickness": "height",
    }
    for alias, target in FIELD_ALIASES.items():
        if alias in f and f[alias] is not None and not f.get(target):
            f[target] = f[alias]

    if f["feature_type"] in ("cylinder", "hole", "pocket"):
        if f.get("diameter") and not f.get("radius"):
            try:
                f["radius"] = float(f["diameter"]) / 2.0
            except (ValueError, TypeError):
                pass
        elif f.get("radius") and not f.get("diameter"):
            try:
                f["diameter"] = float(f["radius"]) * 2.0
            except (ValueError, TypeError):
                pass

    return f


def merge_step_features(
    cumulative_doc: CADIRDocument,
    new_features: List[CADIRFeature],
    step_number: int,
) -> CADIRDocument:
    """
    Deterministically merges step features into cumulative document:
    - Re-roots dependencies to the parent solid.
    - Normalizes operations (first feature in step joins or cuts from parent).
    - Prefixes feature IDs to avoid cross-step name collisions.
    - Deduplicates redundant edge fillets/chamfers.
    - Clamps feature dimensions to host body bounds.
    """
    if not new_features:
        return cumulative_doc

    last_existing_id = cumulative_doc.features[-1].id if cumulative_doc.features else None
    first_body_id = cumulative_doc.features[0].id if cumulative_doc.features else None

    # Estimate current bounding envelope
    host_r = 40.0
    host_h = 100.0
    for f in cumulative_doc.features:
        if f.radius and f.radius > host_r:
            host_r = f.radius
        if f.height and f.height > host_h:
            host_h = f.height
        if f.length and (f.length / 2.0) > host_r:
            host_r = f.length / 2.0

    sanitized_new: List[CADIRFeature] = []

    for i, feat in enumerate(new_features):
        feat_copy = copy.deepcopy(feat)

        # 1. Unique ID per step
        raw_id = feat_copy.id or f"f_{i+1}"
        if not raw_id.startswith(f"s{step_number}_"):
            feat_copy.id = f"s{step_number}_{raw_id}"

        # 2. Dependency re-rooting
        if not feat_copy.dependencies:
            feat_copy.dependencies = [last_existing_id] if last_existing_id else []
        else:
            # Map internal dependencies
            remapped_deps = []
            for d in feat_copy.dependencies:
                if d in [f.id for f in cumulative_doc.features]:
                    remapped_deps.append(d)
                else:
                    prefixed = f"s{step_number}_{d}" if not d.startswith(f"s{step_number}_") else d
                    remapped_deps.append(prefixed)
            if not remapped_deps and last_existing_id:
                remapped_deps = [last_existing_id]
            feat_copy.dependencies = remapped_deps

        # 3. Operation assignment
        if cumulative_doc.features:
            if feat_copy.operation == "new_body":
                # Convert new_body to join or cut to maintain single manifold component
                if feat_copy.feature_type in ("hole", "pocket", "groove"):
                    feat_copy.operation = "cut"
                else:
                    feat_copy.operation = "join"

        # 4. Dimension safety clamping & defaulting to prevent kernel topological crashes
        if feat_copy.feature_type == "box":
            if not feat_copy.length or feat_copy.length <= 0:
                feat_copy.length = round(host_r * 0.5, 1)
            if not feat_copy.width or feat_copy.width <= 0:
                feat_copy.width = round(host_r * 0.5, 1)
            if not feat_copy.height or feat_copy.height <= 0:
                feat_copy.height = round(host_h * 0.2, 1)

        elif feat_copy.feature_type == "cylinder":
            if not feat_copy.radius or feat_copy.radius <= 0:
                feat_copy.radius = round(host_r * 0.5, 1)
                feat_copy.diameter = feat_copy.radius * 2.0
            if not feat_copy.height or feat_copy.height <= 0:
                feat_copy.height = round(host_h * 0.3, 1)

        elif feat_copy.feature_type in ("hole", "pocket"):
            # Ensure hole diameter does not exceed host body
            if feat_copy.radius and feat_copy.radius >= host_r:
                feat_copy.radius = round(host_r * 0.6, 2)
                feat_copy.diameter = feat_copy.radius * 2.0
            if feat_copy.diameter and (feat_copy.diameter / 2.0) >= host_r:
                feat_copy.diameter = round(host_r * 1.2, 2)
                feat_copy.radius = feat_copy.diameter / 2.0
            if not feat_copy.radius or feat_copy.radius <= 0:
                feat_copy.radius = round(host_r * 0.3, 1)
                feat_copy.diameter = feat_copy.radius * 2.0
            if not feat_copy.depth or feat_copy.depth <= 0:
                feat_copy.depth = min(host_h, 30.0)

        elif feat_copy.feature_type == "fillet":
            # Cap fillet radius to prevent face collapse
            if feat_copy.radius and feat_copy.radius > (host_r * 0.25):
                feat_copy.radius = max(1.0, round(host_r * 0.1, 2))
            if not feat_copy.radius or feat_copy.radius <= 0:
                feat_copy.radius = 1.5

        elif feat_copy.feature_type == "chamfer":
            if feat_copy.distance and feat_copy.distance > (host_r * 0.2):
                feat_copy.distance = max(0.5, round(host_r * 0.08, 2))
            if not feat_copy.distance or feat_copy.distance <= 0:
                feat_copy.distance = 1.0

        sanitized_new.append(feat_copy)

    # 5. Deduplicate edge modifications (avoid applying duplicate fillets on same edges)
    existing_mods = {
        (f.feature_type, f.edge_selector)
        for f in cumulative_doc.features
        if f.feature_type in ("fillet", "chamfer")
    }

    for sf in sanitized_new:
        mod_key = (sf.feature_type, sf.edge_selector)
        if sf.feature_type in ("fillet", "chamfer") and mod_key in existing_mods:
            # Skip duplicate edge modification
            continue
        cumulative_doc.features.append(sf)
        last_existing_id = sf.id

    return cumulative_doc


def _synthesize_step_features_deterministic(
    step: Dict[str, Any],
    cumulative_doc: Optional[CADIRDocument],
    overall_prompt: str,
) -> List[CADIRFeature]:
    """
    Deterministic fallback for individual feature build steps.
    Generates robust, physically scaled features when LLM is unavailable.
    """
    group_name = step.get("group_name", "").lower()
    desc = step.get("description", "").lower()
    p_lower = overall_prompt.lower()
    step_num = step.get("step", 1)

    features: List[CADIRFeature] = []

    # ── Step 1: Base Body ─────────────────────────────────────────────────────
    if step_num == 1 or not cumulative_doc or not cumulative_doc.features:
        # Check if cylinder or box
        if any(k in group_name or k in desc for k in ["cylinder", "round", "shell", "shaft", "drum", "housing"]):
            dia = 80.0
            length = 120.0
            m_dia = re.search(r'(?:[⌀ø]|diameter|dia|od)\s*[:=]?\s*(\d+(?:\.\d+)?)', p_lower)
            m_len = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm)?[\s\-]*(?:long|length|tall|height)', p_lower)
            if m_dia:
                dia = float(m_dia.group(1))
            if m_len:
                length = float(m_len.group(1))

            f_body = CADIRFeature(
                id=f"f_base_body",
                name="Main Cylindrical Body",
                feature_type="cylinder",
                radius=dia / 2.0,
                diameter=dia,
                height=length,
                operation="new_body",
                dependencies=[],
            )
            features.append(f_body)
        else:
            lx, ly, lz = 100.0, 80.0, 50.0
            m_box = re.search(r'(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)(?:\s*[x×]\s*(\d+(?:\.\d+)?))?', p_lower)
            if m_box and m_box.group(3):
                lx, ly, lz = float(m_box.group(1)), float(m_box.group(2)), float(m_box.group(3))

            f_body = CADIRFeature(
                id=f"f_base_body",
                name="Main Prismatic Block",
                feature_type="box",
                length=lx,
                width=ly,
                height=lz,
                operation="new_body",
                dependencies=[],
            )
            features.append(f_body)
        return features

    # Context bounds from existing base
    base_f = cumulative_doc.features[0]
    base_r = base_f.radius or (base_f.length / 2.0 if base_f.length else 40.0)
    base_h = base_f.height or 100.0

    # ── Flanges ───────────────────────────────────────────────────────────────
    if "flange" in group_name or "flange" in desc:
        flange_r = round(base_r * 1.35, 1)
        flange_t = max(8.0, round(base_h * 0.12, 1))
        f_flange = CADIRFeature(
            id=f"f_flange",
            name="Mounting Flange",
            feature_type="cylinder" if base_f.feature_type == "cylinder" else "box",
            radius=flange_r if base_f.feature_type == "cylinder" else None,
            length=flange_r * 2.0 if base_f.feature_type == "box" else None,
            width=flange_r * 2.0 if base_f.feature_type == "box" else None,
            height=flange_t,
            position=Point3D(x=0.0, y=0.0, z=-base_h / 2.0 + flange_t / 2.0),
            operation="join",
        )
        features.append(f_flange)

    # ── Bosses & Lugs ─────────────────────────────────────────────────────────
    elif any(k in group_name or k in desc for k in ["boss", "gland", "terminal", "spigot", "lug"]):
        boss_r = round(base_r * 0.35, 1)
        boss_h = 15.0
        f_boss = CADIRFeature(
            id=f"f_boss",
            name="Connection Boss",
            feature_type="box",
            length=boss_r * 2.0,
            width=boss_r * 2.0,
            height=boss_h,
            position=Point3D(x=base_r * 0.8, y=0.0, z=0.0),
            operation="join",
        )
        features.append(f_boss)

    # ── Cooling Fins / Ribs ────────────────────────────────────────────────────
    elif any(k in group_name or k in desc for k in ["fin", "cooling", "rib"]):
        fin_count = 8
        m_count = re.search(r'(\d+)\s*(?:radial\s*)?fins?', p_lower)
        if m_count:
            fin_count = min(16, max(4, int(m_count.group(1))))

        fin_thick = 2.0
        fin_h = round(base_h * 0.7, 1)
        fin_span = round(base_r * 0.25, 1)

        f_fin = CADIRFeature(
            id=f"f_fin_element",
            name="Radial Cooling Fin Array",
            feature_type="box",
            length=fin_span,
            width=fin_thick,
            height=fin_h,
            position=Point3D(x=base_r + fin_span / 2.0, y=0.0, z=0.0),
            operation="join",
        )
        features.append(f_fin)

    # ── Bores and Channels ────────────────────────────────────────────────────
    elif any(k in group_name or k in desc for k in ["bore", "channel", "port", "bearing bore"]):
        bore_dia = round(base_r * 1.0, 1)
        m_dia = re.search(r'(?:bore|bearing)\s*[:=]?\s*(?:[⌀ø])?\s*(\d+(?:\.\d+)?)', p_lower)
        if m_dia:
            bore_dia = float(m_dia.group(1))

        f_bore = CADIRFeature(
            id=f"f_central_bore",
            name="Central Bore",
            feature_type="hole",
            diameter=bore_dia,
            radius=bore_dia / 2.0,
            depth=base_h + 10.0,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            operation="cut",
        )
        features.append(f_bore)

    # ── Grooves and Retaining Rings ───────────────────────────────────────────
    elif any(k in group_name or k in desc for k in ["groove", "snap-ring", "circlip", "keyway"]):
        gw = 1.8
        f_groove = CADIRFeature(
            id=f"f_snap_groove",
            name="Internal Snap-Ring Groove",
            feature_type="groove",
            outer_radius=round(base_r * 0.58, 2),
            inner_radius=round(base_r * 0.50, 2),
            groove_width=gw,
            depth=1.2,
            position=Point3D(x=0.0, y=0.0, z=base_h / 2.0 - 8.0),
            operation="cut",
        )
        features.append(f_groove)

    # ── Internal Pocket ───────────────────────────────────────────────────────
    elif any(k in group_name or k in desc for k in ["pocket", "cavity", "hollow"]):
        f_pocket = CADIRFeature(
            id=f"f_internal_pocket",
            name="Internal Pocket",
            feature_type="pocket",
            length=round(base_r * 1.4, 1),
            width=round(base_r * 1.2, 1),
            height=round(base_h * 0.75, 1),
            depth=round(base_h * 0.75, 1),
            position=Point3D(x=0.0, y=0.0, z=0.0),
            operation="cut",
        )
        features.append(f_pocket)

    # ── Mounting Holes ────────────────────────────────────────────────────────
    elif any(k in group_name or k in desc for k in ["hole", "mounting", "holes", "bolt", "pcd", "m6", "m8"]):
        hole_d = 6.6
        if "m8" in p_lower:
            hole_d = 9.0
        elif "m10" in p_lower:
            hole_d = 11.0
        elif "m4" in p_lower:
            hole_d = 4.5

        pcd_r = round(base_r * 1.15, 1) if base_r > 20 else base_r * 0.75
        # Add 4 symmetric bolt holes
        for h_i, (hx, hy) in enumerate([
            (pcd_r, 0.0), (-pcd_r, 0.0), (0.0, pcd_r), (0.0, -pcd_r)
        ]):
            features.append(CADIRFeature(
                id=f"f_mount_hole_{h_i+1}",
                name=f"Mounting Hole {h_i+1}",
                feature_type="hole",
                diameter=hole_d,
                radius=hole_d / 2.0,
                depth=30.0,
                position=Point3D(x=hx, y=hy, z=0.0),
                operation="cut",
            ))

    # ── Edge Modifications ────────────────────────────────────────────────────
    elif any(k in group_name or k in desc for k in ["fillet", "chamfer", "finishing", "edge", "blend"]):
        f_fillet = CADIRFeature(
            id=f"f_edge_fillet",
            name="Stress-Relief Fillet",
            feature_type="fillet",
            radius=min(2.0, round(base_r * 0.05, 1)),
            edge_selector="vertical",
            operation="join",
        )
        f_chamfer = CADIRFeature(
            id=f"f_entry_chamfer",
            name="Bore Lead Chamfer",
            feature_type="chamfer",
            distance=min(1.0, round(base_r * 0.03, 1)),
            edge_selector="top",
            operation="join",
        )
        features.extend([f_fillet, f_chamfer])

    else:
        # Default functional hole/relief
        features.append(CADIRFeature(
            id=f"f_detail_hole",
            name="Functional Clearance Hole",
            feature_type="hole",
            diameter=8.0,
            radius=4.0,
            depth=25.0,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            operation="cut",
        ))

    return features


def generate_step_features_with_llm(
    step: Dict[str, Any],
    cumulative_doc: Optional[CADIRDocument],
    overall_prompt: str,
) -> List[CADIRFeature]:
    """
    Invokes LLM with current cumulative geometry context to generate
    only the focused features for this specific step.
    Provides explicit coordinate bounding box, spatial anchoring math, and few-shot grounding.
    """
    step_num = step.get("step", 1)
    group_name = step.get("group_name", "Feature Group")
    desc = step.get("description", "")
    spatial_anchor = step.get("spatial_anchor", "origin")

    # Compute cumulative geometric bounds
    b_min_x, b_max_x = -50.0, 50.0
    b_min_y, b_max_y = -40.0, 40.0
    b_min_z, b_max_z = -10.0, 10.0
    base_f_type = "box"

    existing_features_summary = []
    if cumulative_doc and cumulative_doc.features:
        for f in cumulative_doc.features:
            pos_str = f"({f.position.x},{f.position.y},{f.position.z})" if f.position else "(0,0,0)"
            existing_features_summary.append(
                f"- {f.id} [{f.feature_type}, op={f.operation}]: dim(r={f.radius}, l={f.length}, w={f.width}, h={f.height}, d={f.depth}) at {pos_str}"
            )
        base = cumulative_doc.features[0]
        base_f_type = base.feature_type
        if base.feature_type == "box" and base.length and base.width and base.height:
            b_min_x, b_max_x = -base.length / 2.0, base.length / 2.0
            b_min_y, b_max_y = -base.width / 2.0, base.width / 2.0
            b_min_z, b_max_z = -base.height / 2.0, base.height / 2.0
        elif base.feature_type == "cylinder" and base.radius and base.height:
            b_min_x, b_max_x = -base.radius, base.radius
            b_min_y, b_max_y = -base.radius, base.radius
            b_min_z, b_max_z = -base.height / 2.0, base.height / 2.0

    summary_text = "\n".join(existing_features_summary) if existing_features_summary else "No existing features yet (Step 1)."
    bounds_text = f"X in [{b_min_x}, {b_max_x}], Y in [{b_min_y}, {b_max_y}], Z in [{b_min_z}, {b_max_z}] (Base type: {base_f_type})"

    sys_msg = (
        "You are an expert mechanical CAD systems engineer generating parametric features for an incremental build plan.\n"
        "You are constructing ONE specific feature group onto an EXISTING mechanical solid.\n\n"
        f"OVERALL PART GOAL: {overall_prompt}\n"
        f"CUMULATIVE SOLID BOUNDING BOX: {bounds_text}\n"
        f"EXISTING GEOMETRY IN PART SO FAR:\n{summary_text}\n\n"
        f"CURRENT STEP TO GENERATE:\n"
        f"- Step: {step_num}\n"
        f"- Group Name: {group_name}\n"
        f"- Description: {desc}\n"
        f"- Spatial Anchor: {spatial_anchor}\n\n"
        "=== STRICT RULES FOR FEATURE GROUNDING ===\n"
        "1. COORDINATES: Base body is centered at (0, 0, 0). All coordinates MUST lie strictly within or on the bounding box.\n"
        "   - Corner holes: MUST be at (+/-(length/2 - margin), +/-(width/2 - margin), 0). NEVER place outside part bounds!\n"
        "   - Center bores: Position is [0, 0, 0], depth must be >= part height, operation: 'cut'.\n"
        "   - Circular Bolt Circles (PCD): 4 holes on PCD radius R: (+/-R, 0, 0) and (0, +/-R, 0).\n"
        "2. OPERATIONS:\n"
        "   - Subtractive features (hole, pocket, groove, cavity): MUST have operation: 'cut'.\n"
        "   - Additive features (cylinder, box, boss, flange, lug, rib): MUST have operation: 'join' (or 'new_body' for Step 1).\n"
        "   - Edge modifications (fillet, chamfer): MUST have operation: 'join', radius <= 2.0mm.\n"
        "3. METRIC FASTENERS:\n"
        "   M4=4.5mm hole, M5=5.5mm hole, M6=6.6mm hole, M8=9.0mm hole, M10=11.0mm hole.\n"
        "4. OUTPUT FORMAT: Output ONLY a valid JSON list of 1 to 4 features. E.g.:\n"
        "[\n"
        "  {\n"
        '    "id": "s' + str(step_num) + '_hole_1",\n'
        '    "name": "Mounting Clearance Hole",\n'
        '    "feature_type": "hole",\n'
        '    "operation": "cut",\n'
        '    "diameter": 6.6,\n'
        '    "depth": 20.0,\n'
        '    "position": [35.0, 25.0, 0.0]\n'
        "  }\n"
        "]\n"
        "Output raw JSON list only without markdown code fences."
    )

    try:
        llm = get_design_llm()
        res = llm.invoke([("system", sys_msg), ("user", f"Generate JSON feature list for Step {step_num}: {desc}")])
        raw_text = res.content if hasattr(res, "content") else str(res)
        raw_list = _extract_features_list(raw_text)

        if raw_list and isinstance(raw_list, list):
            valid_feats = []
            for item in raw_list:
                if isinstance(item, dict) and item.get("feature_type"):
                    sanitized_item = _sanitize_raw_feature_dict(item)
                    try:
                        feat = CADIRFeature.model_validate(sanitized_item)
                        # Ensure box and cylinder have dimensions
                        if feat.feature_type == "box" and (not feat.length or not feat.width):
                            continue
                        if feat.feature_type == "cylinder" and not feat.radius:
                            continue
                        valid_feats.append(feat)
                    except Exception:
                        pass
            if valid_feats:
                return valid_feats
    except Exception as e:
        print(f"Incremental LLM generation notice ({e}), using deterministic synthesis for step {step_num}.", file=sys.stderr)

    # Fallback to deterministic synthesis for this step
    return _synthesize_step_features_deterministic(step, cumulative_doc, overall_prompt)


def incremental_design_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph Node: Executes one step of the Feature Build Plan.
    Accumulates features into cumulative_cadir.
    When all steps finish, sets final cadir_document.
    """
    design_id = state.get("design_id", f"design_{uuid.uuid4().hex[:8]}")
    overall_prompt = state.get("user_prompt", "")
    plan = state.get("feature_build_plan", [])
    step_idx = state.get("current_build_step", 1) - 1  # 0-indexed
    cumulative_doc: Optional[CADIRDocument] = state.get("cumulative_cadir")
    results = list(state.get("build_step_results", []))

    if not plan or step_idx >= len(plan):
        # All steps already completed or plan empty
        return {
            "cadir_document": cumulative_doc,
            "current_agent": "incremental_design_agent",
        }

    current_step = plan[step_idx]
    step_num = current_step.get("step", step_idx + 1)
    group_name = current_step.get("group_name", f"Step {step_num}")

    # Initialize cumulative_doc if Step 1
    if cumulative_doc is None:
        cumulative_doc = CADIRDocument(
            id=f"doc_{design_id[-8:]}",
            name=f"Complex Part: {overall_prompt[:35]}",
            component_family="complex_mechanism",
            difficulty="L3",
            units="mm",
            features=[],
            engineering_intent={
                "prompt": overall_prompt,
                "decomposition": True,
                "total_steps": len(plan),
            },
        )

    # Generate features for this step
    new_features = generate_step_features_with_llm(
        step=current_step,
        cumulative_doc=cumulative_doc,
        overall_prompt=overall_prompt,
    )

    # Merge into cumulative document
    cumulative_doc = merge_step_features(cumulative_doc, new_features, step_num)

    results.append({
        "step": step_num,
        "group_name": group_name,
        "features_added": len(new_features),
        "feature_ids": [f.id for f in new_features],
    })

    next_step = step_idx + 2
    is_finished = (next_step > len(plan))

    output = {
        "cumulative_cadir": cumulative_doc,
        "current_build_step": next_step,
        "build_step_results": results,
        "current_agent": "incremental_design_agent",
    }

    if is_finished:
        output["cadir_document"] = cumulative_doc

    return output
