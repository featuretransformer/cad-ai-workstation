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
import hashlib

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


def extract_dimensions_from_text(text: str) -> List[float]:
    """
    Extract numeric dimensions from natural language prompt.
    Looks for patterns like: "20mm", "5.5 cm", "10 x 20", "diameter 30"
    Returns list of floats in mm.
    """
    dimensions = []
    
    # Pattern 1: Number followed by unit (20mm, 5.5cm, 10 inches)
    pattern_with_unit = r'(\d+\.?\d*)\s*(mm|millimeter|cm|centimeter|m|meter|in|inch|inches)'
    matches = re.findall(pattern_with_unit, text.lower())
    
    for value, unit in matches:
        val = float(value)
        # Convert to mm
        if unit in ['cm', 'centimeter']:
            val *= 10
        elif unit in ['m', 'meter']:
            val *= 1000
        elif unit in ['in', 'inch', 'inches']:
            val *= 25.4
        dimensions.append(val)
    
    # Pattern 2: Dimension keywords (diameter, length, width, height, thickness, radius)
    dimension_keywords = r'(diameter|length|width|height|thickness|depth|radius|hole)\s*[:=]?\s*(\d+\.?\d*)'
    dim_matches = re.findall(dimension_keywords, text.lower())
    for _, value in dim_matches:
        dimensions.append(float(value))
    
    # Pattern 3: Simple "X by Y" or "X x Y" patterns
    xy_pattern = r'(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)'
    xy_matches = re.findall(xy_pattern, text)
    for x, y in xy_matches:
        dimensions.extend([float(x), float(y)])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_dims = []
    for d in dimensions:
        if d not in seen:
            seen.add(d)
            unique_dims.append(d)
    
    return unique_dims


def get_prompt_seed(prompt: str) -> int:
    """
    Generate deterministic integer seed from prompt text.
    Same prompt -> same seed. Different prompt -> different seed.
    """
    # Use SHA256 hash of normalized prompt text
    normalized = prompt.lower().strip()
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    # Convert first 8 bytes to integer
    return int.from_bytes(hash_obj.digest()[:8], byteorder='big')


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
            f"Here are reference examples from the mechanical dataset:\n{context_str}\n"
            "Respond ONLY with valid JSON for a CADIRDocument."
        )
        resp = llm.invoke([("system", sys_msg), ("user", prompt)])
        content = resp.content if hasattr(resp, "content") else str(resp)
        # Parse JSON
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            doc = CADIRDocument.from_json(m.group(0))
    except Exception:
        doc = None

    # Deterministic parametric synthesis if LLM is offline or output unparseable
    if doc is None:
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
    Uses retrieved exemplars and prompt text to adapt geometry.
    
    CRITICAL FIX: Extract dimensions from prompt and use deterministic seeding
    to ensure different prompts produce different geometries.
    """
    family = (intent.get("component_family") or "custom_part").lower()
    
    # CRITICAL FIX: Extract dimensions from prompt text if not in intent
    explicit_dims = intent.get("dimensions", [])
    if not explicit_dims:
        explicit_dims = extract_dimensions_from_text(prompt)
        print(f"[DESIGN_AGENT] Extracted dimensions from prompt: {explicit_dims}")
    else:
        print(f"[DESIGN_AGENT] Using explicit dimensions from intent: {explicit_dims}")
    
    # Generate deterministic seed from prompt for variation
    seed = get_prompt_seed(prompt)
    print(f"[DESIGN_AGENT] Prompt seed: {seed}, Family: {family}")
    
    # Use seed to create variation in default dimensions (0-50% variation)
    variation = (seed % 1000) / 2000.0  # 0.0 to 0.5
    
    doc = CADIRDocument(
        id=f"doc_{design_id}",
        name=f"Component {design_id}",
        component_family=family,
        difficulty="L2",
        units="mm",
        engineering_intent={
            "prompt": prompt,
            "synthesized": True,
            "retrieved_count": len(retrieved),
            "prompt_seed": seed,
            "extracted_dimensions": explicit_dims,
        },
    )

    # Classify component type by keywords in prompt (more specific matching)
    prompt_lower = prompt.lower()
    is_washer = any(kw in prompt_lower for kw in ["washer", "ring", "annulus"])
    is_nut = any(kw in prompt_lower for kw in ["nut", "hex nut", "hexagonal nut"])
    is_bracket = any(kw in prompt_lower for kw in ["bracket", "mounting", "angle bracket", "l-bracket"])
    is_plate = any(kw in prompt_lower for kw in ["plate", "flat plate", "base plate"])
    is_shaft = any(kw in prompt_lower for kw in ["shaft", "rod", "cylinder", "pin"])
    is_box = any(kw in prompt_lower for kw in ["box", "cube", "rectangular", "block"])

    # 1. Washer
    if is_washer or "washer" in family:
        # Use explicit dims or generate varied defaults
        od = explicit_dims[0] if len(explicit_dims) > 0 else (20.0 + variation * 40.0)
        id_hole = explicit_dims[1] if len(explicit_dims) > 1 else (od * 0.4)
        thickness = explicit_dims[2] if len(explicit_dims) > 2 else (2.0 + variation * 6.0)

        sk = CADIRSketchProfile(
            id="sk_1",
            plane=CADIRPlane(),
            primitives=[CADIRCircle(radius=od / 2.0)],
            is_closed=True,
        )
        doc.sketches.append(sk)

        f1 = CADIRFeature(
            id="f_1_extrude",
            name="Washer Body",
            feature_type="extrude",
            sketch_id=sk.id,
            distance=thickness,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id="f_2_hole",
            name="Washer Hole",
            feature_type="hole",
            diameter=id_hole,
            depth=thickness * 2.0,
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id="f_3_chamfer",
            name="Edge Chamfer",
            feature_type="chamfer",
            distance=0.5,
            length=0.5,
            edge_selector="top",
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # 2. Hex Nut
    elif is_nut or "nut" in family:
        diameter = explicit_dims[0] if len(explicit_dims) > 0 else (15.0 + variation * 25.0)
        hole_dia = explicit_dims[1] if len(explicit_dims) > 1 else (diameter * 0.5)
        height = explicit_dims[2] if len(explicit_dims) > 2 else (8.0 + variation * 12.0)

        sk = CADIRSketchProfile(
            id="sk_1",
            plane=CADIRPlane(),
            primitives=[CADIRCircle(radius=diameter / 2.0)],
            is_closed=True,
        )
        doc.sketches.append(sk)

        f1 = CADIRFeature(
            id="f_1_extrude",
            name="Nut Body",
            feature_type="extrude",
            sketch_id=sk.id,
            distance=height,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id="f_2_hole",
            name="Thread Hole",
            feature_type="hole",
            diameter=hole_dia,
            depth=height * 2.0,
            operation="cut",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # 3. Shaft/Cylinder
    elif is_shaft:
        diameter = explicit_dims[0] if len(explicit_dims) > 0 else (10.0 + variation * 30.0)
        length = explicit_dims[1] if len(explicit_dims) > 1 else (50.0 + variation * 100.0)
        
        f1 = CADIRFeature(
            id="f_1_cylinder",
            name="Shaft Body",
            feature_type="cylinder",
            radius=diameter / 2.0,
            height=length,
            operation="new_body",
            dependencies=[],
        )
        # Optional chamfer on ends
        f2 = CADIRFeature(
            id="f_2_chamfer",
            name="End Chamfer",
            feature_type="chamfer",
            distance=diameter * 0.05,
            length=diameter * 0.05,
            edge_selector="top",
            operation="join",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # 4. Mounting Bracket (L-shaped)
    elif is_bracket:
        length = explicit_dims[0] if len(explicit_dims) > 0 else (40.0 + variation * 60.0)
        width = explicit_dims[1] if len(explicit_dims) > 1 else (30.0 + variation * 40.0)
        height = explicit_dims[2] if len(explicit_dims) > 2 else (10.0 + variation * 15.0)
        hole_dia = explicit_dims[3] if len(explicit_dims) > 3 else (min(length, width) * 0.2)

        # Base plate
        f1 = CADIRFeature(
            id="f_1_box",
            name="Base Plate",
            feature_type="box",
            length=length,
            width=width,
            height=height,
            operation="new_body",
            dependencies=[],
        )
        # Mounting holes
        f2 = CADIRFeature(
            id="f_2_hole",
            name="Mounting Hole 1",
            feature_type="hole",
            diameter=hole_dia,
            depth=height * 1.5,
            position=Point3D(x=length * 0.25, y=width * 0.25, z=0),
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id="f_3_hole",
            name="Mounting Hole 2",
            feature_type="hole",
            diameter=hole_dia,
            depth=height * 1.5,
            position=Point3D(x=length * 0.75, y=width * 0.75, z=0),
            operation="cut",
            dependencies=[f2.id],
        )
        f4 = CADIRFeature(
            id="f_4_fillet",
            name="Edge Fillet",
            feature_type="fillet",
            radius=2.0,
            edge_selector="vertical",
            operation="join",
            dependencies=[f3.id],
        )
        doc.features.extend([f1, f2, f3, f4])

    # 5. Simple Plate with Holes
    elif is_plate:
        length = explicit_dims[0] if len(explicit_dims) > 0 else (50.0 + variation * 100.0)
        width = explicit_dims[1] if len(explicit_dims) > 1 else (40.0 + variation * 80.0)
        thickness = explicit_dims[2] if len(explicit_dims) > 2 else (5.0 + variation * 10.0)
        hole_dia = explicit_dims[3] if len(explicit_dims) > 3 else (min(length, width) * 0.15)

        f1 = CADIRFeature(
            id="f_1_box",
            name="Plate Body",
            feature_type="box",
            length=length,
            width=width,
            height=thickness,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id="f_2_hole",
            name="Center Hole",
            feature_type="hole",
            diameter=hole_dia,
            depth=thickness * 1.5,
            operation="cut",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # 6. Box/Block (default fallback with variation)
    else:
        length = explicit_dims[0] if len(explicit_dims) > 0 else (40.0 + variation * 80.0)
        width = explicit_dims[1] if len(explicit_dims) > 1 else (30.0 + variation * 60.0)
        height = explicit_dims[2] if len(explicit_dims) > 2 else (20.0 + variation * 40.0)

        f1 = CADIRFeature(
            id="f_1_box",
            name="Base Box",
            feature_type="box",
            length=length,
            width=width,
            height=height,
            operation="new_body",
            dependencies=[],
        )
        # Add a feature to differentiate from other boxes
        hole_dia = min(length, width, height) * 0.25
        f2 = CADIRFeature(
            id="f_2_hole",
            name="Feature Hole",
            feature_type="hole",
            diameter=hole_dia,
            depth=height * 1.2,
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id="f_3_fillet",
            name="Corner Fillet",
            feature_type="fillet",
            radius=min(2.0, min(length, width, height) * 0.1),
            edge_selector="vertical",
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    print(f"[DESIGN_AGENT] Generated {family} with features: {[f.name for f in doc.features]}")
    return doc
