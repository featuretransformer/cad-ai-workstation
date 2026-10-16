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
    llm_attempted = False
    llm_error = None
    
    try:
        llm = get_design_llm()
        llm_attempted = True
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
    except Exception as e:
        llm_error = str(e)
        doc = None

    # Deterministic parametric synthesis if LLM is offline or output unparseable
    if doc is None:
        print(f"[design_agent] LLM parsing failed (attempted={llm_attempted}, error={llm_error}), using parametric fallback")
        doc = _synthesize_parametric_cadir(design_id, prompt, intent, retrieved)

    return {
        "cadir_document": doc,
        "current_agent": "design_agent",
    }


def _classify_component_family(prompt: str, intent: Dict[str, Any]) -> str:
    """
    Improved component family classification using both intent and prompt keywords.
    Returns a specific family or 'custom_part' if classification fails.
    """
    prompt_lower = prompt.lower()
    family = (intent.get("component_family") or "").lower()
    
    # Priority 1: Explicit intent
    if family and family != "custom_part":
        return family
    
    # Priority 2: Keyword matching with specificity
    if any(kw in prompt_lower for kw in ["washer", "flat washer", "spring washer"]):
        return "washer"
    
    if any(kw in prompt_lower for kw in ["hex nut", "hexnut", "nut"]):
        return "nut"
    
    if any(kw in prompt_lower for kw in ["bracket", "mounting bracket", "l-bracket", "angle bracket"]):
        return "bracket"
    
    if any(kw in prompt_lower for kw in ["shaft", "axle", "rod", "spindle"]):
        return "shaft"
    
    if any(kw in prompt_lower for kw in ["plate", "mounting plate", "base plate", "flat plate"]):
        return "plate"
    
    if any(kw in prompt_lower for kw in ["gear", "sprocket", "pulley"]):
        return "gear"
    
    if any(kw in prompt_lower for kw in ["housing", "enclosure", "case", "box"]):
        return "housing"
    
    # Default
    return "custom_part"


def _extract_dimensions_robust(prompt: str, intent: Dict[str, Any]) -> List[float]:
    """
    Robust dimension extraction with multiple strategies.
    Returns list of extracted dimensions or empty list if none found.
    """
    dims = []
    
    # Strategy 1: Use intent dimensions if available
    intent_dims = intent.get("dimensions", [])
    if intent_dims:
        return intent_dims
    
    # Strategy 2: Regex extraction with units
    # Match patterns like: 50mm, 20 mm, 30.5mm, 2.5 in, 100
    patterns = [
        r"(\d+\.?\d*)\s*mm",          # 50mm, 50.5mm
        r"(\d+\.?\d*)\s*millimeters?",
        r"(\d+\.?\d*)\s*in(?:ch(?:es)?)?",  # 2in, 2 inches
        r"diameter\s*[:=]?\s*(\d+\.?\d*)",
        r"length\s*[:=]?\s*(\d+\.?\d*)",
        r"width\s*[:=]?\s*(\d+\.?\d*)",
        r"height\s*[:=]?\s*(\d+\.?\d*)",
        r"thickness\s*[:=]?\s*(\d+\.?\d*)",
        r"(?:^|\s)(\d+\.?\d*)(?:\s*(?:mm|in))?(?:\s|$)",  # Bare numbers with optional units
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, prompt.lower())
        for match in matches:
            try:
                val = float(match)
                if 0.1 <= val <= 10000:  # Reasonable range
                    dims.append(val)
            except ValueError:
                continue
    
    # Remove duplicates while preserving order
    seen = set()
    unique_dims = []
    for d in dims:
        if d not in seen:
            seen.add(d)
            unique_dims.append(d)
    
    return unique_dims[:5]  # Max 5 dimensions


def _generate_unique_dimensions(prompt: str, base_dims: List[float], count: int = 3) -> List[float]:
    """
    Generate unique dimensions based on prompt hash when explicit dimensions are missing.
    This ensures different prompts produce different default dimensions.
    
    Args:
        prompt: The user's prompt text
        base_dims: Base dimension set (e.g., [60, 40, 12])
        count: Number of dimensions needed
        
    Returns:
        List of dimensions derived from prompt hash
    """
    # Create deterministic but unique hash from prompt
    prompt_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    
    # Use hash to create variation factors (0.5 to 1.5 range)
    variation_factors = []
    for i in range(count):
        # Take different parts of hash for each dimension
        hash_segment = int(prompt_hash[i*8:(i+1)*8], 16)
        # Normalize to 0.5-1.5 range
        factor = 0.5 + (hash_segment % 1000) / 1000.0
        variation_factors.append(factor)
    
    # Apply variations to base dimensions
    varied_dims = []
    for i in range(count):
        base = base_dims[i] if i < len(base_dims) else base_dims[-1]
        varied = base * variation_factors[i]
        # Round to reasonable precision
        varied_dims.append(round(varied, 1))
    
    print(f"[design_agent] Generated unique dimensions from prompt: {varied_dims}")
    return varied_dims


def _synthesize_parametric_cadir(
    design_id: str,
    prompt: str,
    intent: Dict[str, Any],
    retrieved: List[Dict[str, Any]],
) -> CADIRDocument:
    """
    Deterministic parametric fallback synthesizing CADIR when offline or parsing fails.
    Uses retrieved exemplars to adapt geometry.
    
    CRITICAL FIX: Never silently return identical default geometry for different prompts.
    """
    family = _classify_component_family(prompt, intent)
    dims = _extract_dimensions_robust(prompt, intent)
    
    # Log dimension extraction
    print(f"[design_agent] Family: {family}, Extracted dims: {dims}, Prompt: '{prompt[:60]}...'")
    
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
            "extracted_dimensions": dims,
            "warning": "LLM parsing failed, using deterministic fallback" if not dims else None,
        },
    )

    # 1. Washer
    if family == "washer":
        # Use unique dimensions or generate from prompt hash
        if len(dims) >= 2:
            od = dims[0]
            id_hole = dims[1]
            thickness = dims[2] if len(dims) > 2 else (od * 0.13)
        else:
            print(f"[design_agent] WARNING: Insufficient dimensions for washer, using prompt-derived defaults")
            base_dims = [30.0, 15.0, 4.0]
            unique_dims = _generate_unique_dimensions(prompt, base_dims, 3)
            od, id_hole, thickness = unique_dims[0], unique_dims[1], unique_dims[2]

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
    elif family == "nut":
        if len(dims) >= 2:
            diameter = dims[0]
            hole_dia = dims[1]
            height = dims[2] if len(dims) > 2 else (diameter * 0.5)
        else:
            print(f"[design_agent] WARNING: Insufficient dimensions for nut, using prompt-derived defaults")
            base_dims = [20.0, 10.0, 10.0]
            unique_dims = _generate_unique_dimensions(prompt, base_dims, 3)
            diameter, hole_dia, height = unique_dims[0], unique_dims[1], unique_dims[2]

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

    # 3. Shaft
    elif family == "shaft":
        if len(dims) >= 2:
            diameter = dims[0]
            length = dims[1]
        else:
            print(f"[design_agent] WARNING: Insufficient dimensions for shaft, using prompt-derived defaults")
            base_dims = [15.0, 80.0]
            unique_dims = _generate_unique_dimensions(prompt, base_dims, 2)
            diameter, length = unique_dims[0], unique_dims[1]
        
        f1 = CADIRFeature(
            id="f_1_cylinder",
            name="Shaft Body",
            feature_type="cylinder",
            radius=diameter / 2.0,
            height=length,
            operation="new_body",
            dependencies=[],
        )
        f2 = CADIRFeature(
            id="f_2_chamfer",
            name="End Chamfer",
            feature_type="chamfer",
            distance=1.0,
            edge_selector="top",
            operation="join",
            dependencies=[f1.id],
        )
        doc.features.extend([f1, f2])

    # 4. Bracket
    elif family == "bracket":
        if len(dims) >= 3:
            length = dims[0]
            width = dims[1]
            height = dims[2]
            thickness = dims[3] if len(dims) > 3 else (min(length, width) * 0.1)
        else:
            print(f"[design_agent] WARNING: Insufficient dimensions for bracket, using prompt-derived defaults")
            base_dims = [80.0, 60.0, 50.0, 6.0]
            unique_dims = _generate_unique_dimensions(prompt, base_dims, 4)
            length, width, height, thickness = unique_dims[0], unique_dims[1], unique_dims[2], unique_dims[3]

        # Base plate
        f1 = CADIRFeature(
            id="f_1_base",
            name="Base Plate",
            feature_type="box",
            length=length,
            width=width,
            height=thickness,
            operation="new_body",
            dependencies=[],
        )
        # Vertical plate
        f2 = CADIRFeature(
            id="f_2_vertical",
            name="Vertical Plate",
            feature_type="box",
            length=length,
            width=thickness,
            height=height,
            center=Point3D(x=0, y=width/2 - thickness/2, z=height/2 + thickness/2),
            operation="join",
            dependencies=[f1.id],
        )
        # Mounting holes
        hole_dia = min(length, width) * 0.15
        f3 = CADIRFeature(
            id="f_3_hole",
            name="Mounting Hole",
            feature_type="hole",
            diameter=hole_dia,
            depth=thickness * 2.0,
            position=Point3D(x=length/3, y=width/3, z=0),
            operation="cut",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # 5. Plate
    elif family == "plate":
        if len(dims) >= 3:
            length = dims[0]
            width = dims[1]
            height = dims[2]
        else:
            print(f"[design_agent] WARNING: Insufficient dimensions for plate, using prompt-derived defaults")
            base_dims = [100.0, 75.0, 10.0]
            unique_dims = _generate_unique_dimensions(prompt, base_dims, 3)
            length, width, height = unique_dims[0], unique_dims[1], unique_dims[2]

        f1 = CADIRFeature(
            id="f_1_box",
            name="Plate Body",
            feature_type="box",
            length=length,
            width=width,
            height=height,
            operation="new_body",
            dependencies=[],
        )
        hole_dia = min(length, width) * 0.2
        f2 = CADIRFeature(
            id="f_2_hole",
            name="Center Hole",
            feature_type="hole",
            diameter=hole_dia,
            depth=height * 1.5,
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id="f_3_fillet",
            name="Corner Fillet",
            feature_type="fillet",
            radius=2.0,
            edge_selector="vertical",
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    # 6. Generic fallback - MUST use prompt-unique dimensions
    else:
        print(f"[design_agent] WARNING: Unclassified family '{family}', using generic geometry with prompt-derived dimensions")
        
        # NEVER use fixed defaults - always derive from prompt
        base_dims = [50.0, 35.0, 8.0]
        unique_dims = _generate_unique_dimensions(prompt, base_dims, 3)
        length, width, height = unique_dims[0], unique_dims[1], unique_dims[2]

        f1 = CADIRFeature(
            id="f_1_box",
            name="Base Body",
            feature_type="box",
            length=length,
            width=width,
            height=height,
            operation="new_body",
            dependencies=[],
        )
        hole_dia = min(length, width) * 0.25
        f2 = CADIRFeature(
            id="f_2_hole",
            name="Center Feature",
            feature_type="hole",
            diameter=hole_dia,
            depth=height * 1.5,
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id="f_3_fillet",
            name="Edge Treatment",
            feature_type="fillet",
            radius=1.5,
            edge_selector="vertical",
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    return doc
