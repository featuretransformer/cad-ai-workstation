"""
Design Agent Node.
Synthesizes canonical CADIR documents using engineering intent and retrieved exemplars.
Combines few-shot retrieval grounding with deterministic parametric construction.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
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
    CADIRPolygon,
    Point3D,
    Vector3D,
)
from utils.llm import get_design_llm


def _repair_truncated_json(text: str):
    cleaned = text.strip()
    idx = cleaned.find("{")
    if idx == -1:
        return None
    cleaned = cleaned[idx:]

    delims = [len(cleaned)]
    for i in range(len(cleaned) - 1, -1, -1):
        if cleaned[i] in (",", "{", "[", "}"):
            delims.append(i)
        if len(delims) >= 25:
            break

    for pos in delims:
        sub = cleaned[:pos].rstrip(", \r\n\t")
        open_braces = 0
        open_brackets = 0
        in_string = False
        escape = False
        for ch in sub:
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                open_braces += 1
            elif ch == '}':
                open_braces = max(0, open_braces - 1)
            elif ch == '[':
                open_brackets += 1
            elif ch == ']':
                open_brackets = max(0, open_brackets - 1)

        repaired = sub + ("]" * open_brackets) + ("}" * open_braces)
        try:
            parsed = json.loads(repaired)
            if isinstance(parsed, dict) and ("features" in parsed or "id" in parsed):
                return repaired
        except Exception:
            continue

    return None

def _extract_json_from_text(raw_text: str) -> Optional[str]:
    """Extract valid JSON object from raw LLM text using balanced braces and markdown stripping."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

    # Fast check: If whole text is valid JSON
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            pass

    # Prefer root repaired JSON if it contains features (prevents pulling out an inner child feature)
    repaired_root = _repair_truncated_json(cleaned)
    if repaired_root:
        try:
            parsed = json.loads(repaired_root)
            if isinstance(parsed, dict) and "features" in parsed and len(parsed["features"]) > 0:
                return repaired_root
        except Exception:
            pass

    # Balanced brace extraction
    start = cleaned.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape_next = False
        for i in range(start, len(cleaned)):
            c = cleaned[i]
            if escape_next:
                escape_next = False
                continue
            if c == "\\" and in_string:
                escape_next = True
                continue
            if c == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start : i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        break
        start = cleaned.find("{", start + 1)

    # Fallback to regex
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        candidate = match.group(0)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # Fallback to truncated JSON recovery
    repaired = _repair_truncated_json(cleaned)
    if repaired:
        return repaired

    return None


def _sanitize_raw_cadir(data: dict) -> dict:
    """Pre-processes raw LLM JSON data, fixing aliases, coordinates, and missing dependencies."""
    if not isinstance(data, dict):
        return {}

    data.setdefault("schema_version", "1.0.0")
    if not data.get("id"):
        data["id"] = f"doc_{uuid.uuid4().hex[:8]}"
    if not data.get("name"):
        data["name"] = "Generated Mechanical Part"
    data.setdefault("units", "mm")

    TYPE_ALIASES = {
        "through_hole": "hole",
        "blind_hole": "hole",
        "bore": "hole",
        "drill": "hole",
        "counterbore": "hole",
        "countersink": "hole",
        "cbore": "hole",
        "csink": "hole",
        "round": "fillet",
        "blend": "fillet",
        "edge_fillet": "fillet",
        "bevel": "chamfer",
        "edge_chamfer": "chamfer",
        "block": "box",
        "cube": "box",
        "rectangular_pad": "box",
        "cuboid": "box",
        "pin": "cylinder",
        "rod": "cylinder",
        "round_boss": "cylinder",
        "cutout": "pocket",
        "cavity": "pocket",
        "slot_pocket": "pocket",
        "recess": "pocket",
        "pad": "extrude",
        "boss_extrude": "extrude",
        "rotation": "revolve",
        "turn": "revolve",
        "circular_pattern": "polar_pattern",
        "rectangular_pattern": "linear_pattern",
        "subtract": "boolean_cut",
        "add": "boolean_union",
        "intersect": "boolean_intersect",
    }

    OPERATION_ALIASES = {
        "add": "join",
        "union": "join",
        "fuse": "join",
        "merge": "join",
        "modify": "join",
        "fillet": "join",
        "chamfer": "join",
        "subtract": "cut",
        "remove": "cut",
        "difference": "cut",
        "create": "new_body",
        "base": "new_body",
        "new": "new_body",
    }

    # Normalize root parameters
    if "parameters" in data and isinstance(data["parameters"], dict):
        clean_params = {}
        for pk, pv in data["parameters"].items():
            if isinstance(pv, (int, float)):
                clean_params[pk] = float(pv)
            elif isinstance(pv, list):
                clean_params[pk] = pv
            elif isinstance(pv, str):
                try:
                    clean_params[pk] = float(pv)
                except ValueError:
                    clean_params[pk] = pv
        data["parameters"] = clean_params

    features = data.get("features", [])
    if isinstance(features, list):
        for i, f in enumerate(features):
            if not isinstance(f, dict):
                continue

            # Flatten nested parameters or params dicts if LLM generated them
            for p_key in ("parameters", "params"):
                if isinstance(f.get(p_key), dict):
                    for sub_k, sub_v in f[p_key].items():
                        if sub_k not in f or f[sub_k] is None:
                            f[sub_k] = sub_v

            # Map type -> feature_type
            if "type" in f and not f.get("feature_type"):
                f["feature_type"] = f["type"]

            ft = str(f.get("feature_type", "")).lower().strip()
            f["feature_type"] = TYPE_ALIASES.get(ft, ft)

            op = str(f.get("operation", "")).lower().strip()
            f["operation"] = OPERATION_ALIASES.get(op, op)

            if f.get("operation") not in ("new_body", "join", "cut", "intersect"):
                if i == 0:
                    f["operation"] = "new_body"
                elif f["feature_type"] in ("hole", "pocket"):
                    f["operation"] = "cut"
                else:
                    f["operation"] = "join"

            if not f.get("id"):
                f["id"] = f"f{i+1}_{f['feature_type']}"

            # Auto-link dependencies if missing
            deps = f.get("dependencies")
            if i == 0:
                f["dependencies"] = []
            elif not deps or not isinstance(deps, list) or len(deps) == 0:
                prev_id = features[i - 1].get("id", f"f{i}")
                f["dependencies"] = [prev_id]

            # Map non-standard LLM field names to CADIR fields
            FIELD_ALIASES = {
                "head_height": "height",
                "head_diameter": "diameter",
                "head_radius": "radius",
                "shank_diameter": "diameter",
                "shank_length": "length",
                "shank_radius": "radius",
                "bore_diameter": "diameter",
                "bore_depth": "depth",
                "overall_length": "length",
                "overall_height": "height",
                "across_flats": "width",
                "af": "width",
                "hole_diameter": "diameter",
                "hole_depth": "depth",
                "fillet_radius": "radius",
                "chamfer_distance": "distance",
                "chamfer_length": "distance",
                "wall_thickness": "height",
                "thickness": "height",
                "face_width": "height",
                "outer_diameter": "diameter",
                "inner_diameter": "diameter",
            }
            for alias, target in FIELD_ALIASES.items():
                if alias in f and f[alias] is not None and not f.get(target):
                    f[target] = f[alias]

            # Sync position and center
            if "position" in f and ("center" not in f or f.get("center") is None):
                f["center"] = f["position"]
            elif "center" in f and ("position" not in f or f.get("position") is None):
                f["position"] = f["center"]

            # Numeric normalization
            for k in [
                "length",
                "width",
                "height",
                "radius",
                "distance",
                "depth",
                "diameter",
            ]:
                val = f.get(k)
                if val is not None:
                    try:
                        fval = float(val)
                        f[k] = fval if fval > 0 else None
                    except (ValueError, TypeError):
                        f[k] = None

            # Cylinder / Hole diameter vs radius
            if f["feature_type"] in ("cylinder", "hole", "pocket"):
                if f.get("diameter") and not f.get("radius"):
                    f["radius"] = f["diameter"] / 2.0
                elif f.get("radius") and not f.get("diameter"):
                    f["diameter"] = f["radius"] * 2.0

            # Default dimensions for features if missing
            if f["feature_type"] == "cylinder" and not f.get("height"):
                f["height"] = f.get("length") or f.get("depth") or 20.0
            elif f["feature_type"] == "hole" and not f.get("depth"):
                f["depth"] = f.get("height") or 20.0
            elif f["feature_type"] == "fillet" and not f.get("radius"):
                f["radius"] = 1.5
            elif f["feature_type"] == "chamfer" and not f.get("distance"):
                f["distance"] = f.get("length") or 1.0

        # Second pass: fix completely dimensionless features using sibling context
        for i, f in enumerate(features):
            if not isinstance(f, dict):
                continue
            ft = f.get("feature_type", "")
            has_any_dim = any(
                f.get(k) and f[k] > 0
                for k in ["length", "width", "height", "radius", "depth", "diameter", "distance"]
                if f.get(k) is not None
            )
            if has_any_dim or ft in ("fillet", "chamfer", "polar_pattern", "linear_pattern", "mirror"):
                continue
            # Feature has NO dimensions — infer from siblings
            sibling_radii = [
                sf.get("radius") for sf in features
                if isinstance(sf, dict) and sf.get("radius") and sf is not f
            ]
            sibling_heights = [
                sf.get("height") or sf.get("depth") or sf.get("length")
                for sf in features
                if isinstance(sf, dict) and (sf.get("height") or sf.get("depth") or sf.get("length")) and sf is not f
            ]
            if ft in ("extrude", "cylinder", "box"):
                ref_r = max(sibling_radii) if sibling_radii else 10.0
                ref_h = min(sibling_heights) if sibling_heights else 10.0
                if ft == "extrude" or ft == "cylinder":
                    f["radius"] = ref_r * 1.2  # head slightly larger than shank
                    f["diameter"] = f["radius"] * 2.0
                    f["height"] = min(ref_h * 0.4, ref_r * 0.8) if ref_h > 0 else ref_r * 0.8
                elif ft == "box":
                    f["length"] = ref_r * 3.0
                    f["width"] = ref_r * 3.0
                    f["height"] = ref_r * 0.8
            elif ft == "hole":
                ref_r = min(sibling_radii) if sibling_radii else 5.0
                f["radius"] = ref_r * 0.5
                f["diameter"] = f["radius"] * 2.0
                f["depth"] = max(sibling_heights) if sibling_heights else 20.0

        # Third pass: Ensure all holes/cuts fit inside their parent solid bodies
        for f in features:
            if not isinstance(f, dict):
                continue
            if f.get("feature_type") in ("hole", "pocket"):
                hole_r = f.get("radius") or ((f.get("diameter") or 0) / 2.0)
                deps = f.get("dependencies") or []
                parent_f = next((pf for pf in features if isinstance(pf, dict) and pf.get("id") in deps), None)
                if not parent_f and features:
                    parent_f = features[0]
                if parent_f and isinstance(parent_f, dict):
                    p_rad = parent_f.get("radius")
                    if p_rad and hole_r and hole_r >= p_rad:
                        f["radius"] = round(p_rad * 0.55, 2)
                        f["diameter"] = f["radius"] * 2.0
                    elif parent_f.get("length") and parent_f.get("width"):
                        max_r = min(parent_f["length"], parent_f["width"]) / 2.0
                        if hole_r and hole_r >= max_r:
                            f["radius"] = round(max_r * 0.55, 2)
                            f["diameter"] = f["radius"] * 2.0

    return data


# Canonical Mechanical CADIR Few-Shot Exemplars for Grounding
CADIR_EXEMPLARS = [
    {
        "title": "Rectangular Mounting Plate with 4 Corner Holes",
        "description": "100x80x10mm plate with four M6 corner clearance holes and 2mm edge fillets",
        "doc": {
            "schema_version": "1.0.0",
            "id": "doc_mounting_plate",
            "name": "Rectangular Mounting Plate",
            "component_family": "mounting_plate",
            "units": "mm",
            "parameters": {"length": 100.0, "width": 80.0, "thickness": 10.0, "hole_dia": 6.6},
            "features": [
                {
                    "id": "f1_base_plate",
                    "name": "Base Plate Solid",
                    "feature_type": "box",
                    "operation": "new_body",
                    "length": 100.0,
                    "width": 80.0,
                    "height": 10.0,
                    "position": [0.0, 0.0, 0.0],
                    "dependencies": [],
                },
                {
                    "id": "f2_hole_ne",
                    "name": "Corner Hole (+X, +Y)",
                    "feature_type": "hole",
                    "operation": "cut",
                    "diameter": 6.6,
                    "depth": 15.0,
                    "position": [38.0, 28.0, 0.0],
                    "dependencies": ["f1_base_plate"],
                },
                {
                    "id": "f3_hole_nw",
                    "name": "Corner Hole (-X, +Y)",
                    "feature_type": "hole",
                    "operation": "cut",
                    "diameter": 6.6,
                    "depth": 15.0,
                    "position": [-38.0, 28.0, 0.0],
                    "dependencies": ["f1_base_plate"],
                },
                {
                    "id": "f4_hole_sw",
                    "name": "Corner Hole (-X, -Y)",
                    "feature_type": "hole",
                    "operation": "cut",
                    "diameter": 6.6,
                    "depth": 15.0,
                    "position": [-38.0, -28.0, 0.0],
                    "dependencies": ["f1_base_plate"],
                },
                {
                    "id": "f5_hole_se",
                    "name": "Corner Hole (+X, -Y)",
                    "feature_type": "hole",
                    "operation": "cut",
                    "diameter": 6.6,
                    "depth": 15.0,
                    "position": [38.0, -28.0, 0.0],
                    "dependencies": ["f1_base_plate"],
                },
                {
                    "id": "f6_edge_fillet",
                    "name": "Vertical Edge Fillet",
                    "feature_type": "fillet",
                    "operation": "join",
                    "radius": 2.0,
                    "edge_selector": "vertical",
                    "dependencies": ["f1_base_plate"],
                },
            ],
        },
    },
    {
        "title": "Cylindrical Flanged Bearing Hub with PCD Bolt Circle",
        "description": "80mm OD x 40mm tall flanged hub with 30mm central bore and 4x M8 holes on 60mm PCD",
        "doc": {
            "schema_version": "1.0.0",
            "id": "doc_bearing_hub",
            "name": "Flanged Bearing Hub",
            "component_family": "bearing_housing",
            "units": "mm",
            "parameters": {"flange_dia": 80.0, "hub_dia": 50.0, "bore_dia": 30.0, "pcd": 60.0},
            "features": [
                {
                    "id": "f1_flange_base",
                    "name": "Mounting Flange",
                    "feature_type": "cylinder",
                    "operation": "new_body",
                    "radius": 40.0,
                    "diameter": 80.0,
                    "height": 12.0,
                    "position": [0.0, 0.0, -14.0],
                    "dependencies": [],
                },
                {
                    "id": "f2_hub_body",
                    "name": "Central Hub Column",
                    "feature_type": "cylinder",
                    "operation": "join",
                    "radius": 25.0,
                    "diameter": 50.0,
                    "height": 28.0,
                    "position": [0.0, 0.0, 6.0],
                    "dependencies": ["f1_flange_base"],
                },
                {
                    "id": "f3_center_bore",
                    "name": "Through Shaft Bore",
                    "feature_type": "hole",
                    "operation": "cut",
                    "diameter": 30.0,
                    "depth": 45.0,
                    "position": [0.0, 0.0, 0.0],
                    "dependencies": ["f2_hub_body"],
                },
                {
                    "id": "f4_pcd_hole_1",
                    "name": "PCD Bolt Hole 1",
                    "feature_type": "hole",
                    "operation": "cut",
                    "diameter": 9.0,
                    "depth": 15.0,
                    "position": [30.0, 0.0, -14.0],
                    "dependencies": ["f1_flange_base"],
                },
                {
                    "id": "f5_pcd_hole_2",
                    "name": "PCD Bolt Hole 2",
                    "feature_type": "hole",
                    "operation": "cut",
                    "diameter": 9.0,
                    "depth": 15.0,
                    "position": [-30.0, 0.0, -14.0],
                    "dependencies": ["f1_flange_base"],
                },
                {
                    "id": "f6_pcd_hole_3",
                    "name": "PCD Bolt Hole 3",
                    "feature_type": "hole",
                    "operation": "cut",
                    "diameter": 9.0,
                    "depth": 15.0,
                    "position": [0.0, 30.0, -14.0],
                    "dependencies": ["f1_flange_base"],
                },
                {
                    "id": "f7_pcd_hole_4",
                    "name": "PCD Bolt Hole 4",
                    "feature_type": "hole",
                    "operation": "cut",
                    "diameter": 9.0,
                    "depth": 15.0,
                    "position": [0.0, -30.0, -14.0],
                    "dependencies": ["f1_flange_base"],
                },
            ],
        },
    },
    {
        "title": "Standard Hexagonal Nut",
        "description": "M8 Hexagonal Nut with 13mm across flats, 6.5mm height, and central M8 threaded bore",
        "doc": {
            "schema_version": "1.0.0",
            "id": "doc_hex_nut",
            "name": "M8 Hexagonal Nut",
            "component_family": "fastener",
            "units": "mm",
            "parameters": {"across_flats": 13.0, "height": 6.5, "thread_dia": 8.0},
            "features": [
                {
                    "id": "f1_hex_prism",
                    "name": "Hexagonal Body Prism",
                    "feature_type": "regular_polygon",
                    "operation": "new_body",
                    "side_count": 6,
                    "radius": 7.51,
                    "height": 6.5,
                    "position": [0.0, 0.0, 0.0],
                    "dependencies": [],
                },
                {
                    "id": "f2_central_hole",
                    "name": "Central M8 Bore",
                    "feature_type": "hole",
                    "operation": "cut",
                    "diameter": 8.0,
                    "depth": 10.0,
                    "position": [0.0, 0.0, 0.0],
                    "dependencies": ["f1_hex_prism"],
                },
                {
                    "id": "f3_top_chamfer",
                    "name": "Entry Chamfer",
                    "feature_type": "chamfer",
                    "operation": "join",
                    "distance": 0.5,
                    "edge_selector": "top",
                    "dependencies": ["f1_hex_prism"],
                },
            ],
        },
    },
]


def _try_llm_structured_output(llm, sys_msg: str, prompt: str, semantic_spec: Optional[Dict[str, Any]] = None) -> Optional[CADIRDocument]:
    """
    Attempt LLM-based CADIR generation with rigorous mathematical grounding and few-shot exemplars.
    Includes coordinate framing rules, ISO clearance standards, and self-correction feedback loop.
    """
    exemplars_formatted = []
    for ex in CADIR_EXEMPLARS:
        title = ex["title"]
        desc = ex["description"]
        body = json.dumps(ex["doc"], indent=2)
        exemplars_formatted.append(f"### EXAMPLE: {title} ({desc})\n{body}")
    exemplars_block = "\n\n".join(exemplars_formatted)

    spec_hint = ""
    if semantic_spec:
        spec_lines = [f"- {k}: {v}" for k, v in semantic_spec.items()]
        specs_joined = "\n".join(spec_lines)
        spec_hint = f"\nEXTRACTED SPECIFICATIONS & GROUNDING:\n{specs_joined}\n"

    last_error = ""
    for attempt in range(2):
        try:
            if attempt == 0:
                json_sys_msg = (
                    sys_msg
                    + "\n\n=== CANONICAL MECHANICAL CADIR EXEMPLARS ===\n"
                    + exemplars_block
                    + "\n\n=== STRICT COORDINATE & GEOMETRIC ACCURACY RULES ==="
                    + "\n1. ORIGIN CONVENTION: Base solids are centered at (0, 0, 0) by default."
                    + "\n   - For Box(length=L, width=W, height=H), corners are at (+/-L/2, +/-W/2)."
                    + "\n   - Corner holes with margin M MUST be placed at: (+/-(L/2 - M), +/-(W/2 - M), 0)."
                    + "\n   - NEVER place holes at (L, W) -- that is outside the part!"
                    + "\n2. BOLT CIRCLES (PCD): Radius R = PCD / 2. 4 holes: (+/-R, 0, Z) and (0, +/-R, Z)."
                    + "\n3. REGULAR POLYGONS: Hexagonal across-flats S -> radius = S / 1.732, side_count = 6."
                    + "\n4. OPERATIONS: Base body = 'new_body'. Additions (flange, boss, rib) = 'join'. Cuts (hole, pocket, groove) = 'cut'. Fillets/chamfers = 'join'."
                    + "\n5. METRIC CLEARANCE HOLES: M3=3.4mm, M4=4.5mm, M5=5.5mm, M6=6.6mm, M8=9.0mm, M10=11.0mm, M12=13.5mm."
                    + "\n6. Output ONLY a valid JSON object matching the CADIR schema. No markdown fences, no conversational text."
                )
                user_msg = f"{prompt}\n{spec_hint}\nGenerate the complete CADIR JSON document."
            else:
                json_sys_msg = (
                    sys_msg
                    + f"\n\nCRITICAL ERROR CORRECTION REQUIRED:\nYour previous output failed with error: {last_error}\n"
                    + "Please fix the coordinate positioning and schema structure. Output ONLY the corrected CADIR JSON object."
                )
                user_msg = f"{prompt}\n{spec_hint}\nProduce the corrected CADIR JSON."

            res = llm.invoke([("system", json_sys_msg), ("user", user_msg)])
            raw_text = res.content if hasattr(res, "content") else str(res)
            json_str = _extract_json_from_text(raw_text)

            if json_str:
                raw_dict = json.loads(json_str)
                sanitized_dict = _sanitize_raw_cadir(raw_dict)
                doc = CADIRDocument.model_validate(sanitized_dict)
                if doc.features:
                    return doc
                else:
                    last_error = "JSON parsed but 'features' array is empty."
            else:
                last_error = "Could not extract valid JSON from response."
        except json.JSONDecodeError as je:
            last_error = f"Invalid JSON syntax: {je}"
            print(f"JSON Decode attempt {attempt} error: {je}", file=sys.stderr)
        except Exception as e:
            last_error = f"Validation error: {e}"
            print(
                f"Exemplar JSON prompting attempt {attempt} notice: {e}",
                file=sys.stderr,
            )

    return None


def design_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Produces or refines a CADIRDocument based on user prompt, intent, and retrieved examples.
    """
    design_id = state.get("design_id", "design_default")
    prompt = state.get("user_prompt", "")
    intent = state.get("parsed_intent", {})
    existing_cadir = state.get("cadir_document")
    retrieved = state.get("retrieved_examples", [])

    # If CADIR already extracted via Drawing Understanding Pipeline, preserve and enrich
    if existing_cadir is not None and isinstance(existing_cadir, CADIRDocument) and existing_cadir.features:
        doc = existing_cadir
        if not doc.component_family and intent.get("component_family"):
            doc.component_family = intent["component_family"]
        return {
            "cadir_document": doc,
            "current_agent": "design_agent",
        }

    # Attempt LLM-assisted generation with retrieved context
    doc: Optional[CADIRDocument] = None
    try:
        llm = get_design_llm()
        context_snippets = []
        for ex in retrieved[:2]:
            if ex.get("cadir_json"):
                context_snippets.append(ex["cadir_json"][:400])

        context_str = "\n---\n".join(context_snippets)
        sys_msg = (
            "You are an expert mechanical CAD designer. Generate a JSON document adhering strictly to the CADIR schema.\n"
            "IMPORTANT: Your JSON MUST include 'schema_version', 'id', and 'name' at the root level, with valid 'features'.\n"
            "Each feature must have 'id', 'feature_type', 'operation', and 'dependencies' fields.\n"
            "Use only these feature_type values: box, cylinder, sphere, regular_polygon, groove, extrude, revolve, hole, pocket, fillet, chamfer, "
            "linear_pattern, polar_pattern, mirror, boolean_union, boolean_cut, boolean_intersect.\n"
            "For hexagonal nuts or hex heads, use feature_type: 'regular_polygon' with side_count: 6.\n"
            f"Here are reference examples from the mechanical dataset:\n{context_str}\n"
        )

        doc = _try_llm_structured_output(llm, sys_msg, prompt, semantic_spec=intent.get("semantic_parameters"))
    except Exception as e:
        print(f"LLM Generation Failed: {e}", file=sys.stderr)
        doc = None

    # Deterministic parametric synthesis if LLM is offline or output unparseable
    if doc is None:
        print("LLM generation unavailable — using deterministic parametric synthesis.", file=sys.stderr)
        doc = _synthesize_parametric_cadir(design_id, prompt, intent, retrieved)

    return {
        "cadir_document": doc,
        "current_agent": "design_agent",
    }


def _synthesize_parametric_cadir(
    design_id: str,
    prompt: str,
    intent: Dict[str, Any],
    retrieved: List[Dict[str, Any]],
) -> CADIRDocument:
    """
    Deterministic parametric fallback synthesizing CADIR when offline or parsing fails.
    Uses retrieved exemplars and prompt keywords to select geometry and extract dimensions.
    Generates unique feature IDs per design_id to avoid producing identical models.
    """
    prompt_lower = prompt.lower()
    family = (intent.get("component_family") or "custom_part").lower()
    dims = intent.get("dimensions", [])

    # Use the last 12 chars of design_id as uid — UUIDs and sequential IDs
    # have unique trailing segments, so this ensures IDs never collide across designs.
    uid = design_id[-12:].replace("-", "") if len(design_id) >= 12 else design_id.replace("-", "")

    # Generate a descriptive name from the prompt
    name_words = [w.capitalize() for w in prompt.split()[:6] if len(w) > 2]
    doc_name = " ".join(name_words) if name_words else f"Component {family.capitalize()}"

    doc = CADIRDocument(
        id=f"doc_{uid}",
        name=doc_name,
        component_family=family,
        difficulty="L2",
        units="mm",
        engineering_intent={
            "prompt": prompt,
            "synthesized": True,
            "retrieved_count": len(retrieved),
        },
    )

    # ── 1. Shaft / Rod / Pin / Axle ─────────────────────────────────────────────
    if any(kw in family or kw in prompt_lower for kw in ["shaft", "rod", "pin", "bar", "axle", "roller", "cylinder", "spindle"]):
        is_stepped = "step" in prompt_lower

        # Smart dimension extraction for cylindrical parts
        dia_m = re.search(r'(?:[⌀ø]|diameter|dia)\s*[:=]?\s*(\d+(?:\.\d+)?)', prompt_lower)
        len_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm)?[\s\-]*(?:long|length)', prompt_lower) or re.search(r'(?:length|long)\s*[:=]?\s*(\d+(?:\.\d+)?)', prompt_lower)

        extracted_dia = float(dia_m.group(1)) if dia_m else None
        extracted_len = float(len_m.group(1)) if len_m else None

        if extracted_dia and extracted_len:
            diameter = extracted_dia
            length = extracted_len
        elif extracted_dia:
            diameter = extracted_dia
            length = dims[0] if (dims and dims[0] != diameter) else max(diameter * 3.0, 60.0)
        elif extracted_len:
            length = extracted_len
            diameter = dims[0] if (dims and dims[0] != length) else max(20.0, length * 0.3)
        elif len(dims) >= 2:
            length = max(dims[0], dims[1])
            diameter = min(dims[0], dims[1])
        elif len(dims) == 1:
            diameter = dims[0]
            length = max(diameter * 3.0, 60.0)
        else:
            diameter = 20.0
            length = 80.0

        step_dia = dims[2] if len(dims) > 2 else diameter * 0.75
        step_pos = dims[3] if len(dims) > 3 else length * 0.5

        doc.name = f"{'Roller' if 'roller' in prompt_lower else 'Shaft'} D{diameter}x{length}mm"

        if is_stepped and len(dims) >= 3:
            # Two-section stepped shaft with proper Z offsets and strictly positive lengths
            sec1_len = step_pos if 0 < step_pos < length else length * 0.55
            sec2_len = max(5.0, length - sec1_len)
            f1 = CADIRFeature(
                id=f"f_{uid}_section1",
                name="Main Section",
                feature_type="cylinder",
                radius=diameter / 2.0,
                height=sec1_len,
                center=Point3D(x=0.0, y=0.0, z=sec1_len / 2.0),
                operation="new_body",
                dependencies=[],
            )
            f2 = CADIRFeature(
                id=f"f_{uid}_section2",
                name="Stepped Section",
                feature_type="cylinder",
                radius=step_dia / 2.0,
                height=sec2_len,
                center=Point3D(x=0.0, y=0.0, z=sec1_len + sec2_len / 2.0),
                operation="join",
                dependencies=[f1.id],
            )
            f3 = CADIRFeature(
                id=f"f_{uid}_chamfer",
                name="End Chamfer",
                feature_type="chamfer",
                distance=min(1.0, step_dia * 0.1),
                length=min(1.0, step_dia * 0.1),
                edge_selector="top",
                operation="join",
                dependencies=[f2.id],
            )
            doc.features.extend([f1, f2, f3])
        else:
            # Simple single-section shaft or roller
            f1 = CADIRFeature(
                id=f"f_{uid}_cylinder",
                name="Roller Body" if "roller" in prompt_lower else "Shaft Body",
                feature_type="cylinder",
                radius=diameter / 2.0,
                height=length,
                operation="new_body",
                dependencies=[],
            )
            f2 = CADIRFeature(
                id=f"f_{uid}_chamfer",
                name="End Chamfer",
                feature_type="chamfer",
                distance=min(1.0, diameter * 0.05),
                length=min(1.0, diameter * 0.05),
                edge_selector="top",
                operation="join",
                dependencies=[f1.id],
            )
            doc.features.extend([f1, f2])

            # Check if prompt specifies retaining ring groove / circumferential groove
            if "groove" in prompt_lower:
                gw = 1.5
                gd = 1.0
                if "wide" in prompt_lower or "width" in prompt_lower:
                    m = re.search(r'(\d+(?:\.\d+)?)\s*mm\s*(?:wide|width)', prompt_lower)
                    if m:
                        gw = float(m.group(1))
                if "deep" in prompt_lower or "depth" in prompt_lower:
                    m = re.search(r'(\d+(?:\.\d+)?)\s*mm\s*(?:deep|depth)', prompt_lower)
                    if m:
                        gd = float(m.group(1))
                if "center" in prompt_lower or "centre" in prompt_lower or "middle" in prompt_lower:
                    pz = 0.0
                elif "from" in prompt_lower:
                    m = re.search(r'(\d+(?:\.\d+)?)\s*mm\s*from', prompt_lower)
                    dist = float(m.group(1)) if m else 5.0
                    pz = round(length / 2.0 - dist, 2)
                else:
                    pz = round(length / 2.0 - 5.0, 2)

                fg = CADIRFeature(
                    id=f"f_{uid}_groove",
                    name="Circumferential Retaining Groove",
                    feature_type="groove",
                    outer_radius=diameter / 2.0,
                    inner_radius=max(0.5, round(diameter / 2.0 - gd, 3)),
                    groove_width=gw,
                    depth=gd,
                    position=Point3D(x=0.0, y=0.0, z=pz),
                    operation="cut",
                    dependencies=[f2.id],
                )
                doc.features.append(fg)

    # ── 2. Washer / Disc / Gasket / Ring ────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["washer", "disc", "disk", "gasket", "ring"]):
        od = dims[0] if len(dims) > 0 else 30.0
        id_hole = dims[1] if len(dims) > 1 else round(od * 0.45, 1)
        if id_hole >= od:
            id_hole = round(od * 0.5, 1)
        thickness = dims[2] if len(dims) > 2 else max(2.0, round(od * 0.12, 1))
        sk = CADIRSketchProfile(
            id=f"sk_{uid}_1",
            plane=CADIRPlane(),
            primitives=[CADIRCircle(radius=od / 2.0)],
            is_closed=True,
        )
        doc.sketches.append(sk)
        f1 = CADIRFeature(
            id=f"f_{uid}_extrude",
            name="Washer Body",
            feature_type="extrude",
            sketch_id=sk.id,
            distance=thickness,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_hole",
            name="Centre Hole",
            feature_type="hole",
            diameter=id_hole,
            depth=thickness * 2.0,
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_chamfer",
            name="Edge Chamfer",
            feature_type="chamfer",
            distance=0.5,
            length=0.5,
            edge_selector="top",
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # ── 3. Nut / Hex Nut ────────────────────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["nut", "hex", "lock_nut", "hexagonal"]):
        af = dims[0] if len(dims) > 0 else 19.0
        height = dims[1] if len(dims) > 1 else max(4.0, round(af * 0.4, 1))
        hole_dia = dims[2] if len(dims) > 2 else round(af * 0.55, 1)
        # Hex circumscribed radius = af / sqrt(3)
        hex_rad = round(af / (3.0**0.5), 3)
        f1 = CADIRFeature(
            id=f"f_{uid}_body",
            name="Hex Nut Body",
            feature_type="regular_polygon",
            side_count=6,
            radius=hex_rad,
            height=height,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_hole",
            name="Thread Hole",
            feature_type="hole",
            diameter=hole_dia,
            depth=height * 2.0,
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_chamfer",
            name="Top Chamfer",
            feature_type="chamfer",
            distance=1.0,
            length=1.0,
            edge_selector="top",
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # ── 4. Bolt / Screw / Fastener ───────────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["bolt", "screw", "fastener", "stud"]):
        head_dia = dims[0] if len(dims) > 0 else 16.0
        shank_dia = dims[1] if len(dims) > 1 else round(head_dia * 0.625, 1)
        length = dims[2] if len(dims) > 2 else max(shank_dia * 4.0, 40.0)
        head_h = round(head_dia * 0.4, 1)
        f1 = CADIRFeature(
            id=f"f_{uid}_head",
            name="Bolt Head",
            feature_type="cylinder",
            radius=head_dia / 2.0,
            height=head_h,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_shank",
            name="Bolt Shank",
            feature_type="cylinder",
            radius=shank_dia / 2.0,
            height=length,
            center=Point3D(x=0.0, y=0.0, z=-length / 2.0),
            operation="join",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_chamfer",
            name="Lead Chamfer",
            feature_type="chamfer",
            distance=1.0,
            length=1.0,
            edge_selector="bottom",
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # ── 5. Bearing Housing / Flange / Hub ───────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["bearing", "housing", "flange", "hub"]):
        od = dims[0] if len(dims) > 0 else 80.0
        bore = dims[1] if len(dims) > 1 else round(od * 0.5, 1)
        width = dims[2] if len(dims) > 2 else round(od * 0.35, 1)
        f1 = CADIRFeature(
            id=f"f_{uid}_body",
            name="Housing Body",
            feature_type="cylinder",
            radius=od / 2.0,
            height=width,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_bore",
            name="Bearing Bore",
            feature_type="hole",
            diameter=bore,
            depth=width * 2.0,
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_fillet",
            name="Inner Fillet",
            feature_type="fillet",
            radius=2.0,
            edge_selector="bottom",
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # ── 6. Bracket / L-Bracket ──────────────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["bracket", "angle", "l-bracket"]):
        width = dims[0] if len(dims) > 0 else 50.0
        depth = dims[1] if len(dims) > 1 else 40.0
        thickness = dims[2] if len(dims) > 2 else 6.0
        height = dims[3] if len(dims) > 3 else 40.0
        f1 = CADIRFeature(
            id=f"f_{uid}_base",
            name="Base Flange",
            feature_type="box",
            length=width,
            width=depth,
            height=thickness,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_wall",
            name="Vertical Wall",
            feature_type="box",
            length=width,
            width=thickness,
            height=height,
            center=Point3D(x=0.0, y=-(depth / 2.0 - thickness / 2.0), z=height / 2.0),
            operation="join",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_hole1",
            name="Mounting Hole 1",
            feature_type="hole",
            diameter=min(width, depth) * 0.2,
            depth=thickness * 2.0,
            position=Point3D(x=width * 0.25, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f2.id],
        )
        f4 = CADIRFeature(
            id=f"f_{uid}_hole2",
            name="Mounting Hole 2",
            feature_type="hole",
            diameter=min(width, depth) * 0.2,
            depth=thickness * 2.0,
            position=Point3D(x=-width * 0.25, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f3.id],
        )
        f5 = CADIRFeature(
            id=f"f_{uid}_fillet",
            name="Inner Radius",
            feature_type="fillet",
            radius=3.0,
            edge_selector="vertical",
            operation="join",
            dependencies=[f4.id],
        )
        doc.features.extend([f1, f2, f3, f4, f5])

    # ── 7. Gear / Sprocket / Pulley ─────────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["gear", "sprocket", "pulley"]):
        pitch_d = dims[0] if len(dims) > 0 else 60.0
        bore = dims[1] if len(dims) > 1 else round(pitch_d * 0.25, 1)
        face_w = dims[2] if len(dims) > 2 else round(pitch_d * 0.3, 1)
        f1 = CADIRFeature(
            id=f"f_{uid}_body",
            name="Gear Blank",
            feature_type="cylinder",
            radius=pitch_d / 2.0,
            height=face_w,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_bore",
            name="Bore",
            feature_type="hole",
            diameter=bore,
            depth=face_w * 2.0,
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_keyway",
            name="Keyway Slot",
            feature_type="hole",
            diameter=max(bore * 0.25, 4.0),
            depth=face_w * 2.0,
            position=Point3D(x=bore / 2.0 * 0.85, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f2.id],
        )
        f4 = CADIRFeature(
            id=f"f_{uid}_chamfer",
            name="Face Chamfer",
            feature_type="chamfer",
            distance=1.0,
            length=1.0,
            edge_selector="top",
            operation="join",
            dependencies=[f3.id],
        )
        doc.features.extend([f1, f2, f3, f4])

    # ── 8. Pipe / Tube / Sleeve ──────────────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["pipe", "tube", "hollow", "sleeve"]):
        od = dims[0] if len(dims) > 0 else 40.0
        wall = dims[1] if len(dims) > 1 else max(2.0, round(od * 0.1, 1))
        length = dims[2] if len(dims) > 2 else od * 3.0
        id_val = od - 2.0 * wall
        f1 = CADIRFeature(
            id=f"f_{uid}_outer",
            name="Outer Cylinder",
            feature_type="cylinder",
            radius=od / 2.0,
            height=length,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_bore",
            name="Inner Bore",
            feature_type="hole",
            diameter=id_val,
            depth=length * 2.0,
            operation="cut",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # ── 9. U-Channel / C-Channel ───────────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["u-channel", "c-channel", "channel section", "u channel"]):
        length = dims[0] if len(dims) > 0 else 150.0
        web = dims[1] if len(dims) > 1 else 60.0
        flange = dims[2] if len(dims) > 2 else 40.0
        thick = dims[3] if len(dims) > 3 else 5.0
        f1 = CADIRFeature(
            id=f"f_{uid}_solid",
            name="Channel Outer Solid",
            feature_type="box",
            length=length,
            width=web,
            height=flange,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_cavity",
            name="Channel Inner Pocket",
            feature_type="pocket",
            length=length + 10.0,
            width=max(4.0, web - 2.0 * thick),
            height=flange - thick + 1.0,
            position=Point3D(x=0.0, y=0.0, z=thick / 2.0),
            operation="cut",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # ── 10. Clevis / Lug Mount ──────────────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["clevis", "lug base", "fork lug", "mounting lug"]):
        base_l = dims[0] if len(dims) > 0 else 80.0
        base_w = dims[1] if len(dims) > 1 else 50.0
        base_t = dims[2] if len(dims) > 2 else 10.0
        lug_t = 15.0
        lug_h = 30.0
        gap = 20.0
        pin_dia = 12.0
        f1 = CADIRFeature(
            id=f"f_{uid}_base",
            name="Clevis Baseplate",
            feature_type="box",
            length=base_l,
            width=base_w,
            height=base_t,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_lug1",
            name="Upright Lug 1",
            feature_type="box",
            length=base_l * 0.5,
            width=lug_t,
            height=lug_h,
            position=Point3D(x=0.0, y=-(gap / 2.0 + lug_t / 2.0), z=base_t / 2.0 + lug_h / 2.0),
            operation="join",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_lug2",
            name="Upright Lug 2",
            feature_type="box",
            length=base_l * 0.5,
            width=lug_t,
            height=lug_h,
            position=Point3D(x=0.0, y=+(gap / 2.0 + lug_t / 2.0), z=base_t / 2.0 + lug_h / 2.0),
            operation="join",
            dependencies=[f2.id],
        )
        f4 = CADIRFeature(
            id=f"f_{uid}_pin_hole",
            name="Cross Pin Hole",
            feature_type="hole",
            diameter=pin_dia,
            depth=base_w * 2.0,
            position=Point3D(x=0.0, y=0.0, z=base_t / 2.0 + lug_h * 0.65),
            operation="cut",
            dependencies=[f3.id],
        )
        doc.features.extend([f1, f2, f3, f4])

    # ── 11. Enclosure Lid / Cover Plate ─────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["lid", "cover plate", "enclosure lid", "housing cover"]):
        length = dims[0] if len(dims) > 0 else 120.0
        width = dims[1] if len(dims) > 1 else 80.0
        height = dims[2] if len(dims) > 2 else 8.0
        rim_h = 4.0
        f1 = CADIRFeature(
            id=f"f_{uid}_plate",
            name="Lid Main Plate",
            feature_type="box",
            length=length,
            width=width,
            height=height,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_rim",
            name="Underside Stepped Rim",
            feature_type="box",
            length=max(10.0, length - 8.0),
            width=max(10.0, width - 8.0),
            height=rim_h,
            position=Point3D(x=0.0, y=0.0, z=-(height / 2.0 + rim_h / 2.0)),
            operation="join",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])
        prev = f2.id
        for idx, (hx, hy) in enumerate([
            (length * 0.38, width * 0.35),
            (-length * 0.38, width * 0.35),
            (length * 0.38, -width * 0.35),
            (-length * 0.38, -width * 0.35),
        ]):
            f_cb = CADIRFeature(
                id=f"f_{uid}_cb_{idx+1}",
                name=f"Mounting Hole {idx+1}",
                feature_type="hole",
                hole_type="counterbore",
                diameter=5.0,
                cbore_diameter=9.0,
                cbore_depth=3.0,
                depth=height * 2.0,
                position=Point3D(x=hx, y=hy, z=0.0),
                operation="cut",
                dependencies=[prev],
            )
            doc.features.append(f_cb)
            prev = f_cb.id

    # ── 12. Spherical Knob / Ball Knob ──────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["spherical knob", "ball knob", "shift knob", "round knob"]):
        ball_dia = dims[0] if len(dims) > 0 else 40.0
        neck_dia = dims[1] if len(dims) > 1 else 20.0
        neck_h = dims[2] if len(dims) > 2 else 10.0
        bore_dia = 6.8
        bore_depth = 15.0
        f1 = CADIRFeature(
            id=f"f_{uid}_ball",
            name="Spherical Knob Ball",
            feature_type="sphere",
            radius=ball_dia / 2.0,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_neck",
            name="Neck Cylinder",
            feature_type="cylinder",
            radius=neck_dia / 2.0,
            height=neck_h,
            position=Point3D(x=0.0, y=0.0, z=-(ball_dia / 2.0 - neck_h / 2.0)),
            operation="join",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_bore",
            name="Threaded Bore",
            feature_type="hole",
            diameter=bore_dia,
            depth=bore_depth,
            position=Point3D(x=0.0, y=0.0, z=-(ball_dia / 2.0)),
            operation="cut",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # ── 13. Heatsink / Cooling Fins ─────────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["heatsink", "heat sink", "cooling fin", "fin array"]):
        length = dims[0] if len(dims) > 0 else 100.0
        width = dims[1] if len(dims) > 1 else 60.0
        base_h = dims[2] if len(dims) > 2 else 5.0
        fin_h = 25.0
        fin_t = 2.0
        num_fins = 8
        f1 = CADIRFeature(
            id=f"f_{uid}_base",
            name="Heatsink Baseplate",
            feature_type="box",
            length=length,
            width=width,
            height=base_h,
            operation="new_body",
            dependencies=[],
        )
        doc.features.append(f1)
        prev = f1.id
        for i in range(num_fins):
            y_pos = round(-width / 2.0 + fin_t + i * (width - 2.0 * fin_t) / max(1, num_fins - 1), 2)
            f_fin = CADIRFeature(
                id=f"f_{uid}_fin_{i+1}",
                name=f"Cooling Fin {i+1}",
                feature_type="box",
                length=length,
                width=fin_t,
                height=fin_h,
                position=Point3D(x=0.0, y=y_pos, z=base_h / 2.0 + fin_h / 2.0),
                operation="join",
                dependencies=[prev],
            )
            doc.features.append(f_fin)
            prev = f_fin.id

    # ── 14. Knurled / Thumb Turn Knob ───────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["thumb turn", "knurled knob", "thumb screw", "thumb knob", "radial knob"]):
        head_dia = dims[0] if len(dims) > 0 else 35.0
        stem_dia = dims[1] if len(dims) > 1 else 15.0
        stem_len = dims[2] if len(dims) > 2 else 12.0
        bore_dia = 6.0
        head_h = 10.0
        f1 = CADIRFeature(
            id=f"f_{uid}_head",
            name="Knob Head",
            feature_type="cylinder",
            radius=head_dia / 2.0,
            height=head_h,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_stem",
            name="Knob Stem",
            feature_type="cylinder",
            radius=stem_dia / 2.0,
            height=stem_len,
            position=Point3D(x=0.0, y=0.0, z=-(head_h / 2.0 + stem_len / 2.0)),
            operation="join",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_bore",
            name="D-Shaft Bore",
            feature_type="hole",
            diameter=bore_dia,
            depth=(head_h + stem_len) * 1.5,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # ── 15. V-Block Fixture ─────────────────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["v-block", "v block", "vee block"]):
        length = dims[0] if len(dims) > 0 else 60.0
        width = dims[1] if len(dims) > 1 else 60.0
        height = dims[2] if len(dims) > 2 else 50.0
        f1 = CADIRFeature(
            id=f"f_{uid}_block",
            name="V-Block Solid",
            feature_type="box",
            length=length,
            width=width,
            height=height,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_slot",
            name="Bottom Clamping Slot",
            feature_type="pocket",
            length=length + 5.0,
            width=12.0,
            height=8.0,
            position=Point3D(x=0.0, y=0.0, z=-(height / 2.0 - 4.0)),
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id=f"f_{uid}_v_groove",
            name="Top V-Groove",
            feature_type="pocket",
            length=length + 5.0,
            width=40.0,
            height=20.0,
            position=Point3D(x=0.0, y=0.0, z=height / 2.0 - 10.0),
            operation="cut",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # ── 16. Default: Mounting Plate with 4-corner + centre holes ────────────────
    else:
        length = dims[0] if len(dims) > 0 else 60.0
        width = dims[1] if len(dims) > 1 else 40.0
        height = dims[2] if len(dims) > 2 else 12.0
        hole_dia = min(length, width) * 0.25
        f1 = CADIRFeature(
            id=f"f_{uid}_box",
            name="Base Plate",
            feature_type="box",
            length=length,
            width=width,
            height=height,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id=f"f_{uid}_hole_c",
            name="Centre Hole",
            feature_type="hole",
            diameter=hole_dia,
            depth=height * 1.5,
            position=Point3D(x=0.0, y=0.0, z=0.0),
            operation="cut",
            dependencies=[f1.id],
        )
        is_cbore = any(k in prompt_lower for k in ["counterbore", "counter-bore", "socket head", "shcs", "cap screw", "cbore"])
        is_csink = any(k in prompt_lower for k in ["countersink", "counter-sink", "flat head", "csink"])
        from cad.standards.fasteners import lookup_counterbore, lookup_countersink
        screw_m = re.search(r"\bM(\d+(?:\.\d+)?)\b", prompt, re.IGNORECASE)
        std_cb = lookup_counterbore(screw_m.group(0)) if (screw_m and is_cbore) else None
        std_cs = lookup_countersink(screw_m.group(0)) if (screw_m and is_csink) else None

        corner_hole_type = "counterbore" if is_cbore else ("countersink" if is_csink else "simple")
        corner_d = std_cb["clearance_dia"] if std_cb else (std_cs["clearance_dia"] if std_cs else hole_dia * 0.5)
        corner_cb_d = std_cb["cbore_dia"] if std_cb else (corner_d * 1.8 if is_cbore else None)
        corner_cb_h = std_cb["cbore_depth"] if std_cb else (min(height * 0.5, 6.0) if is_cbore else None)
        corner_cs_d = std_cs["csink_dia"] if std_cs else (corner_d * 2.0 if is_csink else None)

        f3 = CADIRFeature(
            id=f"f_{uid}_hole_1",
            name="Corner Hole 1",
            feature_type="hole",
            hole_type=corner_hole_type,
            diameter=corner_d,
            cbore_diameter=corner_cb_d,
            cbore_depth=corner_cb_h,
            csink_diameter=corner_cs_d,
            csink_angle=90.0 if is_csink else None,
            depth=height * 1.5,
            position=Point3D(x=length * 0.35, y=width * 0.35, z=0.0),
            operation="cut",
            dependencies=[f2.id],
        )
        f4 = CADIRFeature(
            id=f"f_{uid}_hole_2",
            name="Corner Hole 2",
            feature_type="hole",
            hole_type=corner_hole_type,
            diameter=corner_d,
            cbore_diameter=corner_cb_d,
            cbore_depth=corner_cb_h,
            csink_diameter=corner_cs_d,
            csink_angle=90.0 if is_csink else None,
            depth=height * 1.5,
            position=Point3D(x=-length * 0.35, y=width * 0.35, z=0.0),
            operation="cut",
            dependencies=[f3.id],
        )
        f5 = CADIRFeature(
            id=f"f_{uid}_hole_3",
            name="Corner Hole 3",
            feature_type="hole",
            hole_type=corner_hole_type,
            diameter=corner_d,
            cbore_diameter=corner_cb_d,
            cbore_depth=corner_cb_h,
            csink_diameter=corner_cs_d,
            csink_angle=90.0 if is_csink else None,
            depth=height * 1.5,
            position=Point3D(x=length * 0.35, y=-width * 0.35, z=0.0),
            operation="cut",
            dependencies=[f4.id],
        )
        f6 = CADIRFeature(
            id=f"f_{uid}_hole_4",
            name="Corner Hole 4",
            feature_type="hole",
            hole_type=corner_hole_type,
            diameter=corner_d,
            cbore_diameter=corner_cb_d,
            cbore_depth=corner_cb_h,
            csink_diameter=corner_cs_d,
            csink_angle=90.0 if is_csink else None,
            depth=height * 1.5,
            position=Point3D(x=-length * 0.35, y=-width * 0.35, z=0.0),
            operation="cut",
            dependencies=[f5.id],
        )
        f7 = CADIRFeature(
            id=f"f_{uid}_fillet",
            name="Vertical Fillet",
            feature_type="fillet",
            radius=2.0,
            edge_selector="vertical",
            operation="join",
            dependencies=[f6.id],
        )
        doc.features.extend([f1, f2, f3, f4, f5, f6, f7])

    return doc
