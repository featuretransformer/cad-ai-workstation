"""
Input Classifier Node.
Detects input modality (text prompt, engineering drawing, rough sketch, or reference photo)
and triggers the appropriate multimodal or drawing understanding pipeline.
"""
from typing import Dict, Any, Optional
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


def classify_input_node(state: AgentState) -> Dict[str, Any]:
    """
    Classifies input modality and runs drawing pipeline if vector/image input is detected.
    """
    prompt = (state.get("user_prompt") or "").lower()
    img_data = state.get("image_data")
    file_path = state.get("file_path")
    explicit_type = state.get("input_type")

    input_type = "text"
    if explicit_type in ("drawing", "sketch", "photo"):
        input_type = explicit_type
    elif "<svg" in prompt or (file_path and str(file_path).lower().endswith(".svg")):
        input_type = "drawing"
    elif "sketch" in prompt or "hand-drawn" in prompt:
        input_type = "sketch"
    elif "photo" in prompt or "photograph" in prompt or "picture" in prompt:
        input_type = "photo"
    elif img_data or (file_path and any(str(file_path).lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg"])):
        input_type = "photo"

    updates: Dict[str, Any] = {"input_type": input_type}

    # If drawing/sketch/photo with active drawing payload, invoke Drawing Understanding
    drawing_source = None
    if "<svg" in prompt:
        drawing_source = state.get("user_prompt")
    elif file_path and Path(file_path).exists():
        drawing_source = Path(file_path)
    elif img_data:
        drawing_source = img_data

    if drawing_source and input_type in ("drawing", "sketch", "photo"):
        try:
            parser = DrawingParser()
            parsed = parser.parse(drawing_source)
            if parsed.primitives:
                v_identifier = ViewIdentifier()
                views = v_identifier.identify_views(parsed)

                dim_extractor = DimensionExtractor()
                dims = dim_extractor.extract_dimensions(parsed.text_elements, primitives=parsed.primitives)

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
                    updates["clarification_needed"] = cadir_doc.engineering_intent["clarification_needed"]
        except Exception as e:
            updates["drawing_parse_error"] = str(e)

    conf = {**state.get("confidence_scores", {})}
    conf["input_classifier"] = 0.98
    updates["confidence_scores"] = conf
    updates["current_agent"] = "input_classifier"

    return updates
