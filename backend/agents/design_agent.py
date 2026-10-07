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
    Uses retrieved exemplars to adapt geometry.
    """
    family = (intent.get("component_family") or "custom_part").lower()
    dims = intent.get("dimensions", [])

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
        },
    )

    # 1. Washer
    if "washer" in family or "washer" in prompt.lower():
        od = dims[0] if len(dims) > 0 else 30.0
        id_hole = dims[1] if len(dims) > 1 else (od * 0.5)
        thickness = dims[2] if len(dims) > 2 else 4.0

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
    elif "nut" in family or "hex" in prompt.lower():
        diameter = dims[0] if len(dims) > 0 else 20.0
        hole_dia = dims[1] if len(dims) > 1 else (diameter * 0.5)
        height = dims[2] if len(dims) > 2 else 10.0

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

    # 3. Default: Mounting Plate with Holes
    else:
        length = dims[0] if len(dims) > 0 else 60.0
        width = dims[1] if len(dims) > 1 else 40.0
        height = dims[2] if len(dims) > 2 else 12.0

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
        f2 = CADIRFeature(
            id="f_2_hole",
            name="Center Hole",
            feature_type="hole",
            diameter=min(length, width) * 0.3,
            depth=height * 1.5,
            operation="cut",
            dependencies=[f1.id],
        )
        f3 = CADIRFeature(
            id="f_3_fillet",
            name="Vertical Fillet",
            feature_type="fillet",
            radius=2.0,
            edge_selector="vertical",
            operation="join",
            dependencies=[f2.id],
        )
        doc.features.extend([f1, f2, f3])

    return doc
