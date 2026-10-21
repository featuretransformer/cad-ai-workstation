"""
Feature Planner Agent Node.
Decomposes complex mechanical CAD requests into an ordered, logically sequenced
Feature Build Plan. Ensures strict engineering order: base body first, secondary
features/bosses next, cuts and holes intermediate, edge modifications last.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import re
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.state import AgentState
from utils.llm import get_design_llm


def _extract_json_plan(raw_text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse build plan JSON from LLM output."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

    # Try direct parse
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "build_plan" in data and isinstance(data["build_plan"], list):
            return data
    except Exception:
        pass

    # Match JSON block
    match = re.search(r"\{[\s\S]*\"build_plan\"\s*:[\s\S]*\}", cleaned)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict) and "build_plan" in data:
                return data
        except Exception:
            pass

    return None


def decompose_complex_prompt_deterministic(prompt: str, intent: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Deterministic rule-based mechanical feature planner.
    Analyzes prompt clauses and creates an ordered sequence of feature groups.
    """
    p_lower = prompt.lower()
    intent = intent or {}
    dims = intent.get("dimensions", [])
    family = (intent.get("component_family") or "").lower()

    steps: List[Dict[str, Any]] = []

    # ── 1. Determine Base Body Envelope ───────────────────────────────────────
    is_cylindrical = any(k in p_lower or k in family for k in ["motor", "bearing", "housing", "cylinder", "shaft", "round", "pipe", "tube", "drum", "spindle"])
    is_box_like = any(k in p_lower or k in family for k in ["manifold", "block", "gearbox", "enclosure", "bracket", "cube", "plate", "box"])

    if is_cylindrical and not is_box_like:
        # Extract main diameter & length if available
        d_match = re.search(r'(?:[⌀ø]|diameter|dia|od)\s*[:=]?\s*(\d+(?:\.\d+)?)', p_lower)
        l_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm)?[\s\-]*(?:long|length|tall|height)', p_lower)
        d = float(d_match.group(1)) if d_match else (dims[0] if dims else 80.0)
        l = float(l_match.group(1)) if l_match else (dims[1] if len(dims) > 1 else 100.0)

        steps.append({
            "step": 1,
            "group_name": "Main Cylindrical Body",
            "description": f"Main cylindrical envelope, diameter {d}mm, length {l}mm, centered at origin",
            "feature_types": ["cylinder"],
            "spatial_anchor": "origin",
            "estimated_bounds": {"x": d, "y": d, "z": l},
            "depends_on_steps": [],
        })
    else:
        # Box / prismatic body
        box_dims = re.search(r'(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)(?:\s*[x×]\s*(\d+(?:\.\d+)?))?', p_lower)
        if box_dims and box_dims.group(3):
            lx, ly, lz = float(box_dims.group(1)), float(box_dims.group(2)), float(box_dims.group(3))
        elif len(dims) >= 3:
            lx, ly, lz = dims[0], dims[1], dims[2]
        else:
            lx, ly, lz = 100.0, 80.0, 50.0

        steps.append({
            "step": 1,
            "group_name": "Main Prismatic Body",
            "description": f"Base block {lx}mm x {ly}mm x {lz}mm centered at origin",
            "feature_types": ["box"],
            "spatial_anchor": "origin",
            "estimated_bounds": {"x": lx, "y": ly, "z": lz},
            "depends_on_steps": [],
        })

    # ── 2. Secondary Positive Additions (Flanges, Bosses, Lugs, Spigots) ──────
    if any(k in p_lower for k in ["flange", "mounting flange", "base plate"]):
        steps.append({
            "step": len(steps) + 1,
            "group_name": "Mounting Flange",
            "description": "External mounting flange extending outward at base or end face",
            "feature_types": ["cylinder" if is_cylindrical else "box"],
            "spatial_anchor": "base_face",
            "depends_on_steps": [1],
        })

    if any(k in p_lower for k in ["boss", "gland", "terminal block", "spigot", "lug", "ear"]):
        steps.append({
            "step": len(steps) + 1,
            "group_name": "External Bosses and Enclosures",
            "description": "Protruding boss, cable entry gland, or attachment lug on outer face",
            "feature_types": ["box", "cylinder"],
            "spatial_anchor": "outer_surface_mid",
            "depends_on_steps": [1],
        })

    if any(k in p_lower for k in ["fin", "fins", "cooling fin", "rib", "ribs"]):
        steps.append({
            "step": len(steps) + 1,
            "group_name": "Cooling Fins / Structural Ribs",
            "description": "Array of external cooling fins or reinforcing webs distributed across perimeter",
            "feature_types": ["box", "polar_pattern" if is_cylindrical else "linear_pattern"],
            "spatial_anchor": "outer_surface_mid",
            "depends_on_steps": [1],
        })

    # ── 3. Subtractive Features (Bores, Pockets, Channels, Grooves, Holes) ───
    if any(k in p_lower for k in ["pocket", "internal pocket", "cavity", "hollow"]):
        steps.append({
            "step": len(steps) + 1,
            "group_name": "Internal Pocket / Cavity",
            "description": "Internal pocket cutout recessed inside main body",
            "feature_types": ["pocket"],
            "spatial_anchor": "top_face_center",
            "depends_on_steps": [1],
        })

    if any(k in p_lower for k in ["bore", "bearing bore", "through-bore", "channel", "channels", "port", "ports"]):
        b_dia = 30.0
        b_match = re.search(r'(?:bore|bearing|channel)\s*[:=]?\s*(?:[⌀ø])?\s*(\d+(?:\.\d+)?)', p_lower)
        if b_match:
            b_dia = float(b_match.group(1))

        steps.append({
            "step": len(steps) + 1,
            "group_name": "Central Bore and Fluid Ports",
            "description": f"Internal bore ⌀{b_dia}mm and connecting fluid/cable routing channels",
            "feature_types": ["hole"],
            "spatial_anchor": "front_face_center",
            "depends_on_steps": [1],
        })

    if any(k in p_lower for k in ["groove", "snap-ring", "circlip", "retaining ring", "o-ring", "keyway"]):
        steps.append({
            "step": len(steps) + 1,
            "group_name": "Retaining Grooves and Keyways",
            "description": "Internal circlip/retaining groove or keyway cutout inside bore/shaft",
            "feature_types": ["groove" if is_cylindrical else "pocket"],
            "spatial_anchor": "bore_interior",
            "depends_on_steps": [1, len(steps)],
        })

    if any(k in p_lower for k in ["mounting hole", "holes", "bolt hole", "tapped", "m6", "m8", "m10", "m12", "m4", "m5", "pcd"]):
        steps.append({
            "step": len(steps) + 1,
            "group_name": "Mounting Hole Pattern",
            "description": "Bolt clearance or tapped holes arranged symmetrically or on pitch circle",
            "feature_types": ["hole", "polar_pattern"],
            "spatial_anchor": "flange_or_face",
            "depends_on_steps": [1],
        })

    # ── 4. Edge Modification (ALWAYS LAST) ─────────────────────────────────────
    if any(k in p_lower for k in ["fillet", "fillets", "chamfer", "chamfers", "rounded", "bevel", "edge"]) or len(steps) >= 3:
        steps.append({
            "step": len(steps) + 1,
            "group_name": "Edge Finishing & Blends",
            "description": "Stress-relief fillets on internal transitions and protective chamfers on entry edges",
            "feature_types": ["fillet", "chamfer"],
            "spatial_anchor": "global_edges",
            "depends_on_steps": list(range(1, len(steps) + 1)),
        })

    # Ensure at least 2 steps exist if marked complex
    if len(steps) < 2:
        steps.append({
            "step": 2,
            "group_name": "Detail Features and Bores",
            "description": "Functional holes, mounting points, and structural clearances",
            "feature_types": ["hole"],
            "spatial_anchor": "top_face_center",
            "depends_on_steps": [1],
        })

    # Renumber sequentially
    for idx, s in enumerate(steps):
        s["step"] = idx + 1

    return steps


def plan_features_with_llm(prompt: str, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Invokes LLM to construct an ordered feature decomposition build plan."""
    sample_plan = {
        "build_plan": [
            {
                "step": 1,
                "group_name": "Main Cylindrical Housing Shell",
                "description": "Primary cylindrical shell, OD 80mm, length 120mm, centered at origin",
                "feature_types": ["cylinder"],
                "spatial_anchor": "origin",
                "estimated_bounds": {"x": 80.0, "y": 80.0, "z": 120.0},
                "depends_on_steps": []
            },
            {
                "step": 2,
                "group_name": "Bearing Bore with Snap-Ring Groove",
                "description": "Through-bore diameter 35mm at front face with snap-ring groove at Z=5mm",
                "feature_types": ["hole", "groove"],
                "spatial_anchor": "front_face_center",
                "depends_on_steps": [1]
            },
            {
                "step": 3,
                "group_name": "Cooling Fin Array",
                "description": "Radial cooling fins 2mm thick, 8mm tall around outer diameter",
                "feature_types": ["box", "polar_pattern"],
                "spatial_anchor": "outer_surface_mid",
                "depends_on_steps": [1]
            },
            {
                "step": 4,
                "group_name": "Mounting Flange with Holes",
                "description": "Rear mounting flange with 4x M6 clearance holes on 60mm PCD",
                "feature_types": ["cylinder", "hole"],
                "spatial_anchor": "rear_face",
                "depends_on_steps": [1]
            },
            {
                "step": 5,
                "group_name": "Edge Finishing",
                "description": "2mm fillets on outer vertical edges, 0.5mm chamfer on bore entry",
                "feature_types": ["fillet", "chamfer"],
                "spatial_anchor": "global_edges",
                "depends_on_steps": [1, 2, 3, 4]
            }
        ]
    }

    sys_msg = (
        "You are an expert mechanical CAD architect. Decompose a complex mechanical part prompt "
        "into an ordered Feature Build Plan.\n"
        "RULES FOR MECHANICAL BUILD ORDER:\n"
        "1. Step 1 MUST ALWAYS be the main primary solid envelope (the base cylinder or base box).\n"
        "2. Step 2+ should add major solid bodies (flanges, bosses, lugs, ribs).\n"
        "3. Intermediate steps add subtractive features (cavities, pockets, bores, channels, grooves, holes).\n"
        "4. The FINAL step MUST ALWAYS be edge modifications (fillets, chamfers, edge breaks).\n"
        "5. Keep the plan to between 3 and 5 total steps, with 1 to 4 features per step.\n"
        "Output ONLY a valid JSON object matching this schema:\n"
        f"{json.dumps(sample_plan, indent=2)}\n"
        "Output raw JSON without markdown formatting."
    )

    try:
        llm = get_design_llm()
        res = llm.invoke([("system", sys_msg), ("user", f"Decompose this mechanical CAD part into a build plan:\n{prompt}")])
        raw_text = res.content if hasattr(res, "content") else str(res)
        plan_dict = _extract_json_plan(raw_text)
        if plan_dict and "build_plan" in plan_dict and len(plan_dict["build_plan"]) >= 2:
            return plan_dict["build_plan"]
    except Exception as e:
        print(f"LLM Feature Planning error: {e}", file=sys.stderr)

    # Fallback to deterministic mechanical planner
    return decompose_complex_prompt_deterministic(prompt, intent)


def feature_planner_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node: constructs the ordered Feature Build Plan."""
    prompt = state.get("user_prompt", "")
    intent = state.get("parsed_intent", {})

    plan = plan_features_with_llm(prompt, intent)

    return {
        "feature_build_plan": plan,
        "current_build_step": 1,
        "cumulative_cadir": None,
        "build_step_results": [],
        "decomposition_used": True,
        "current_agent": "feature_planner",
    }
