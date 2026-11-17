"""
Vision Analyzer Module (Deprecated Wrapper).
Legacy compatibility layer wrapping agents.intent_extractor.extract_design_intent.
"""
from typing import Dict, Any, Tuple
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.intent_extractor import extract_design_intent, _encode_image


def encode_image_to_base64(image_path_or_data: Any) -> Tuple[str, str]:
    """Encodes file path, raw bytes, or string to (base64_string, mime_type)."""
    return _encode_image(image_path_or_data)


def analyze_mechanical_image(
    image_source: Any,
    user_prompt: str = "",
) -> Dict[str, Any]:
    """
    Extracts mechanical features and dimensions from drawing, sketch, or photograph.
    Emits structured metadata including detected components, dimensions, and assembly cues
    via the canonical MechanicalDesignIntent pipeline.
    """
    intent = extract_design_intent(images=[image_source], user_prompt=user_prompt)

    env = intent.get("envelope") or {}
    dims = [v for v in [env.get("length"), env.get("width"), env.get("height")] if v is not None]

    features = []
    for f in intent.get("feature_tree", []):
        ft = f.get("feature_type")
        if ft and ft not in features:
            features.append(ft)

    components = [c.get("name") for c in intent.get("assembly_components", []) if c.get("name")]
    if not components:
        components = ["Main Body"]

    return {
        "success": True,
        "component_family": intent.get("component_family", "custom_part"),
        "is_assembly": intent.get("is_assembly", False),
        "dimensions": dims if dims else [60.0, 40.0, 15.0],
        "detected_components": components,
        "features": features if features else ["box", "hole"],
        "confidence": intent.get("confidence", 0.8),
        "source": intent.get("source", "intent_extractor_wrapper"),
        "design_intent": intent,
    }
