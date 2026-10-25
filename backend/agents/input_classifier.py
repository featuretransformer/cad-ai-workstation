"""
Input Classifier Node.
Detects input modality (text prompt, engineering drawing, rough sketch, or reference photo)
and triggers the appropriate multimodal or drawing understanding pipeline.

Enhancements (v2):
- Multi-image support: accepts state["images"] list (up to 3 images)
- Uses rich MechanicalDesignIntent extractor (intent_extractor.py)
- Populates state["design_intent"] for downstream use
- Issues clarification question if intent.needs_clarification is True
- Falls back to deterministic heuristics when LLM is unavailable
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
import re
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.state import AgentState
from drawing.parser import DrawingParser
from drawing.view_identifier import ViewIdentifier
from drawing.dimension_extractor import DimensionExtractor
from drawing.feature_recognizer import FeatureRecognizer

from agents.intent_extractor import extract_design_intent, build_clarification_question


def _collect_images(state: AgentState) -> List[Any]:
    """Gather all image sources from state into a unified list."""
    imgs: List[Any] = []

    # Priority 1: explicit multi-image list
    state_images = state.get("images")
    if isinstance(state_images, list):
        imgs.extend(state_images)

    # Priority 2: single image_data field
    img_data = state.get("image_data")
    if img_data and img_data not in imgs:
        imgs.append(img_data)

    # Priority 3: file_path pointing to an image
    file_path = state.get("file_path")
    if file_path:
        fp = Path(str(file_path))
        if fp.exists() and fp.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"):
            if str(fp) not in [str(i) for i in imgs]:
                imgs.append(fp)

    return imgs[:3]  # Cap at 3


def classify_input_node(state: AgentState) -> Dict[str, Any]:
    """
    Classifies input modality and runs the appropriate understanding pipeline.

    Outputs:
      - input_type: "text" | "drawing" | "sketch" | "photo"
      - design_intent: rich MechanicalDesignIntent dict (always populated)
      - parsed_intent: backward-compatible simplified dict
      - clarification_needed: str if needs_clarification else None
    """
    prompt = (state.get("user_prompt") or "")
    prompt_lower = prompt.lower()
    file_path = state.get("file_path")
    explicit_type = state.get("input_type")

    # ── 1. Determine input type ──────────────────────────────────────────────
    input_type = "text"
    if explicit_type in ("drawing", "sketch", "photo"):
        input_type = explicit_type
    elif "<svg" in prompt or (file_path and str(file_path).lower().endswith(".svg")):
        input_type = "drawing"
    elif "sketch" in prompt_lower or "hand-drawn" in prompt_lower:
        input_type = "sketch"
    elif "photo" in prompt_lower or "photograph" in prompt_lower or "picture" in prompt_lower:
        input_type = "photo"
    else:
        # If any images are attached, treat as photo/sketch
        imgs = _collect_images(state)
        if imgs:
            input_type = "sketch" if "sketch" in prompt_lower else "photo"

    updates: Dict[str, Any] = {"input_type": input_type}
    parsed_intent: Dict[str, Any] = state.get("parsed_intent", {}).copy()

    # ── 2. Collect images ────────────────────────────────────────────────────
    all_images = _collect_images(state)

    # ── 3. Drawing (SVG) pipeline ────────────────────────────────────────────
    drawing_source = None
    if "<svg" in prompt:
        drawing_source = state.get("user_prompt")
    elif file_path and Path(str(file_path)).exists():
        drawing_source = Path(str(file_path))

    if drawing_source and (
        "<svg" in prompt or (file_path and str(file_path).lower().endswith(".svg"))
    ):
        try:
            parser = DrawingParser()
            parsed = parser.parse(drawing_source)
            if parsed.primitives:
                v_identifier = ViewIdentifier()
                views = v_identifier.identify_views(parsed)

                dim_extractor = DimensionExtractor()
                dims = dim_extractor.extract_dimensions(
                    parsed.text_elements, primitives=parsed.primitives
                )

                recognizer = FeatureRecognizer()
                cadir_doc = recognizer.recognize_features(
                    drawing=parsed,
                    views=views,
                    dimensions=dims,
                    input_type=input_type,
                    doc_id=f"doc_{state.get('design_id', 'design')}",
                )
                updates["cadir_document"] = cadir_doc
                if "clarification_needed" in cadir_doc.engineering_intent:
                    updates["clarification_needed"] = cadir_doc.engineering_intent[
                        "clarification_needed"
                    ]
        except Exception as e:
            updates["drawing_parse_error"] = str(e)

    # ── 4. Rich Intent Extraction (for all modalities) ───────────────────────
    design_intent = extract_design_intent(
        images=all_images if all_images else None,
        user_prompt=prompt,
    )
    updates["design_intent"] = design_intent

    # ── 5. Populate backward-compatible parsed_intent ────────────────────────
    if design_intent.get("component_family"):
        parsed_intent["component_family"] = design_intent["component_family"]
    if design_intent.get("is_assembly") is not None:
        parsed_intent["is_assembly"] = design_intent["is_assembly"]

    env = design_intent.get("envelope") or {}
    raw_dims = [v for v in [env.get("length"), env.get("width"), env.get("height")] if v]
    if raw_dims:
        parsed_intent["dimensions"] = raw_dims

    # Assembly components
    if design_intent.get("assembly_components"):
        parsed_intent["detected_components"] = [
            c.get("name", "") for c in design_intent["assembly_components"] if c.get("name")
        ]

    # Feature types
    if design_intent.get("feature_tree"):
        parsed_intent["features"] = list({
            f.get("feature_type", "") for f in design_intent["feature_tree"] if f.get("feature_type")
        })

    # Material hint
    if design_intent.get("material_hint"):
        parsed_intent["material"] = design_intent["material_hint"]

    # Manufacturing process
    if design_intent.get("manufacturing_process"):
        parsed_intent["manufacturing_process"] = design_intent["manufacturing_process"]

    # Units
    if design_intent.get("units"):
        parsed_intent["units"] = design_intent["units"]

    updates["parsed_intent"] = parsed_intent

    # ── 6. Clarification request ─────────────────────────────────────────────
    clarification = build_clarification_question(design_intent)
    if clarification and not updates.get("clarification_needed"):
        updates["clarification_needed"] = clarification

    # ── 7. Confidence scores ─────────────────────────────────────────────────
    conf = {**state.get("confidence_scores", {})}
    conf["input_classifier"] = design_intent.get("confidence", 0.8)
    updates["confidence_scores"] = conf
    updates["current_agent"] = "input_classifier"

    return updates
