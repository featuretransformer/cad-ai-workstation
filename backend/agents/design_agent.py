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


def _extract_json_from_text(raw_text: str) -> Optional[str]:
    """Extract valid JSON object from raw LLM text, stripping markdown fences."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match.group(0) if match else None


def _try_llm_structured_output(llm, sys_msg: str, prompt: str) -> Optional[CADIRDocument]:
    """
    Attempt LLM-based CADIR generation using structured output.
    Tries exemplar-guided raw JSON prompting first (most robust across Gemini, Groq, and Ollama),
    then json_mode and function calling. Returns None on all failures so caller can use deterministic fallback.
    """
    sample_template = {
        "schema_version": "1.0.0",
        "id": "doc_generated",
        "name": "Part Name",
        "component_family": "bolt | shaft | flange | bracket | gear | washer | plate | custom_part",
        "units": "mm",
        "features": [
            {
                "id": "f1_base",
                "name": "Base Feature",
                "feature_type": "cylinder | box | extrude | revolve",
                "operation": "new_body",
                "radius": 12.5,
                "length": 60.0,
                "height": 10.0,
                "width": 25.0,
                "dependencies": []
            },
            {
                "id": "f2_sub",
                "name": "Secondary Feature",
                "feature_type": "chamfer | fillet | hole",
                "operation": "join | cut",
                "radius": 4.0,
                "distance": 1.5,
                "dependencies": ["f1_base"]
            }
        ]
    }

    # Strategy 1: Clean exemplar-guided JSON prompting (universally supported across all models)
    try:
        json_sys_msg = (
            sys_msg
            + "\n\nCRITICAL: Output ONLY a valid JSON object strictly matching this schema structure:\n"
            + json.dumps(sample_template, indent=2)
            + "\nAllowed feature_type values: box, cylinder, sphere, extrude, revolve, hole, pocket, fillet, chamfer, linear_pattern, polar_pattern, mirror, boolean_union, boolean_cut, boolean_intersect."
            + "\nAllowed operation values: new_body, join, cut, intersect."
            + "\nOutput raw JSON only without markdown code fences or conversational text."
        )
        res = llm.invoke([("system", json_sys_msg), ("user", prompt)])
        raw_text = res.content if hasattr(res, "content") else str(res)
        json_str = _extract_json_from_text(raw_text)
        if json_str:
            doc = CADIRDocument.model_validate_json(json_str)
            if doc.features:
                return doc
    except Exception as e:
        print(f"Exemplar JSON prompting notice: {e}", file=sys.stderr)

    # Strategy 2: json_mode (for OpenAI or compatible providers)
    try:
        structured_llm = llm.with_structured_output(CADIRDocument, method="json_mode")
        doc = structured_llm.invoke([("system", sys_msg), ("user", prompt)])
        if isinstance(doc, CADIRDocument) and doc.features:
            return doc
    except Exception:
        pass

    # Strategy 3: default function calling mode
    try:
        structured_llm = llm.with_structured_output(CADIRDocument)
        doc = structured_llm.invoke([("system", sys_msg), ("user", prompt)])
        if isinstance(doc, CADIRDocument) and doc.features:
            return doc
    except Exception:
        pass

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
            "Use only these feature_type values: box, cylinder, sphere, extrude, revolve, hole, pocket, fillet, chamfer, "
            "linear_pattern, polar_pattern, mirror, boolean_union, boolean_cut, boolean_intersect.\n"
            f"Here are reference examples from the mechanical dataset:\n{context_str}\n"
        )

        doc = _try_llm_structured_output(llm, sys_msg, prompt)
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

    doc = CADIRDocument(
        id=f"doc_{uid}",
        name=f"Component {design_id[:12]}",
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
    if any(kw in family or kw in prompt_lower for kw in ["shaft", "rod", "pin", "bar", "axle"]):
        diameter = dims[0] if len(dims) > 0 else 20.0
        length = dims[1] if len(dims) > 1 else max(diameter * 4.0, 80.0)
        f1 = CADIRFeature(
            id=f"f_{uid}_cylinder",
            name="Shaft Body",
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
            distance=1.5,
            length=1.5,
            edge_selector="top",
            operation="join",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # ── 2. Washer / Disc / Gasket / Ring ────────────────────────────────────────
    elif any(kw in family or kw in prompt_lower for kw in ["washer", "disc", "disk", "gasket", "ring"]):
        od = dims[0] if len(dims) > 0 else 30.0
        id_hole = dims[1] if len(dims) > 1 else round(od * 0.45, 1)
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
    elif any(kw in family or kw in prompt_lower for kw in ["nut", "hex", "lock_nut"]):
        af = dims[0] if len(dims) > 0 else 19.0
        height = dims[1] if len(dims) > 1 else max(4.0, round(af * 0.4, 1))
        hole_dia = dims[2] if len(dims) > 2 else round(af * 0.55, 1)
        f1 = CADIRFeature(
            id=f"f_{uid}_body",
            name="Nut Body",
            feature_type="cylinder",
            radius=af / 2.0,
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

    # ── 9. Default: Mounting Plate with 4-corner + centre holes ─────────────────
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
        f3 = CADIRFeature(
            id=f"f_{uid}_hole_1",
            name="Corner Hole 1",
            feature_type="hole",
            diameter=hole_dia * 0.5,
            depth=height * 1.5,
            position=Point3D(x=length * 0.35, y=width * 0.35, z=0.0),
            operation="cut",
            dependencies=[f2.id],
        )
        f4 = CADIRFeature(
            id=f"f_{uid}_hole_2",
            name="Corner Hole 2",
            feature_type="hole",
            diameter=hole_dia * 0.5,
            depth=height * 1.5,
            position=Point3D(x=-length * 0.35, y=width * 0.35, z=0.0),
            operation="cut",
            dependencies=[f3.id],
        )
        f5 = CADIRFeature(
            id=f"f_{uid}_hole_3",
            name="Corner Hole 3",
            feature_type="hole",
            diameter=hole_dia * 0.5,
            depth=height * 1.5,
            position=Point3D(x=length * 0.35, y=-width * 0.35, z=0.0),
            operation="cut",
            dependencies=[f4.id],
        )
        f6 = CADIRFeature(
            id=f"f_{uid}_hole_4",
            name="Corner Hole 4",
            feature_type="hole",
            diameter=hole_dia * 0.5,
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
