"""
Mechanical Design Intent Extractor.

Replaces the shallow 5-field vision_analyzer with a rich, structured
MechanicalDesignIntent extraction following CAD-MLLM / CadVLM best practices:
- Structured JSON output (not free-text)
- Null for ambiguous dimensions — never hallucinate
- Multi-image support (sketch + product photo + reference drawing, up to 3)
- Offline deterministic fallback using regex + heuristics
- Clarification request when intent is underspecified (confidence < 0.6)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import base64
import json
import math
import mimetypes
import re
import sys
import uuid

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.llm import get_design_llm, get_supervisor_llm, _google_api_reachable
from config import get_settings


# ---------------------------------------------------------------------------
# Pydantic-free dataclass-style dict schema (avoids adding pydantic dependency
# to already-imported modules; validated via _validate_intent below).
# ---------------------------------------------------------------------------

INTENT_SCHEMA_EXAMPLE = {
    "part_name": "Three-Finger Pneumatic Gripper",
    "component_family": "gripper",          # bracket|shaft|flange|gripper|gear|bearing_housing|manifold|fastener|custom
    "is_assembly": True,
    "manufacturing_process": "CNC milling", # CNC milling|turning|casting|3D printing|welding|sheet metal|unknown
    "material_hint": "Aluminum 6061-T6",    # or null if unknown
    "units": "mm",                          # mm|inch|unknown
    "envelope": {                           # overall bounding box — null fields = unknown
        "length": 150.0,
        "width": 150.0,
        "height": 80.0,
    },
    "primary_operation": "extrude",         # extrude|revolve|loft|unknown
    "feature_tree": [
        {
            "step": 1,
            "name": "Mounting Plate",
            "feature_type": "cylinder",     # cylinder|box|hole|pocket|fillet|chamfer|thread|...
            "operation": "new_body",         # new_body|join|cut
            "dimensions": {
                "diameter": 120.0,
                "thickness": 12.0,
            },
            "tolerances": None,             # e.g. "H7/g6" or null
            "spatial_relation": "centered at origin",
            "notes": None,
        },
    ],
    "assembly_components": [
        {
            "name": "Mounting Plate",
            "role": "base",
            "quantity": 1,
            "key_dims": {"diameter": 120.0, "thickness": 12.0},
        },
    ],
    "standard_parts_detected": [
        {"standard": "ISO 4762", "nominal_size": "M6", "quantity": 4},
    ],
    "gdt_notes": [],                        # list of GD&T / tolerance callouts from drawing
    "views_detected": [],                   # "top"|"front"|"right"|"isometric"|"section"
    "ambiguities": [
        "Finger length not specified — using 75mm estimate",
    ],
    "confidence": 0.82,                     # 0.0-1.0
    "needs_clarification": False,
}


# ---------------------------------------------------------------------------
# System prompt — follows CAD-MLLM / CadVLM / CAD-GPT best practices
# ---------------------------------------------------------------------------

_VISION_SYSTEM_PROMPT = """You are an expert mechanical CAD/CAM computer vision engineer and dimensioning specialist.
Your task: analyse the provided image(s) — which may be rough sketches, engineering drawings, product photos, or a combination — and extract a complete structured mechanical design intent.

CRITICAL RULES:
1. OUTPUT ONLY valid JSON matching the schema below. No markdown fences, no explanations outside JSON.
2. If a dimension is not visible or cannot be confidently read: output null, DO NOT guess.
3. Ambiguous items must be listed in "ambiguities" array with a short explanation.
4. Set "confidence" (0.0-1.0) based on how completely you could extract intent.
5. Set "needs_clarification": true if confidence < 0.6 or if critical dimensions are null.
6. Detect drawing views present: "top", "front", "right", "isometric", "section".
7. For GD&T symbols: extract them verbatim into "gdt_notes".
8. For standard parts (bolts, bearings, pins): identify standard + nominal size.
9. For assemblies: list every visible sub-component in "assembly_components".
10. Preserve engineering units as written on drawing; default to "mm" if ambiguous.

OUTPUT SCHEMA (use exact field names; null for unknown values):
{
  "part_name": string or null,
  "component_family": string,
  "is_assembly": boolean,
  "manufacturing_process": string or null,
  "material_hint": string or null,
  "units": "mm" | "inch" | "unknown",
  "envelope": {"length": number|null, "width": number|null, "height": number|null},
  "primary_operation": "extrude" | "revolve" | "loft" | "unknown",
  "feature_tree": [
    {
      "step": integer,
      "name": string,
      "feature_type": string,
      "operation": "new_body" | "join" | "cut",
      "dimensions": {key: number|null, ...},
      "tolerances": string or null,
      "spatial_relation": string or null,
      "notes": string or null
    }
  ],
  "assembly_components": [
    {"name": string, "role": string, "quantity": integer, "key_dims": {key: number|null, ...}}
  ],
  "standard_parts_detected": [
    {"standard": string, "nominal_size": string, "quantity": integer}
  ],
  "gdt_notes": [string],
  "views_detected": [string],
  "ambiguities": [string],
  "confidence": float,
  "needs_clarification": boolean
}"""

_TEXT_ONLY_SYSTEM_PROMPT = """You are an expert mechanical CAD/CAM computer vision engineer and dimensioning specialist.
Your task: analyse the user's natural language mechanical prompt and extract a complete structured mechanical design intent.

CRITICAL RULES:
1. OUTPUT ONLY valid JSON matching the schema below. No markdown fences, no explanations outside JSON.
2. If a dimension is not specified in the prompt: output null, DO NOT guess or hallucinate.
3. Ambiguous items must be listed in "ambiguities" array.
4. Set "confidence" (0.0-1.0) based on how completely intent is specified.
5. Set "needs_clarification": true if confidence < 0.6 or if critical dimensions are missing.
6. For standard parts (bolts, bearings, pins): identify standard + nominal size.
7. For assemblies: list every sub-component in "assembly_components".
8. Preserve engineering units; default to "mm" if ambiguous.

OUTPUT SCHEMA (use exact field names; null for unknown values):
{
  "part_name": string or null,
  "component_family": string,
  "is_assembly": boolean,
  "manufacturing_process": string or null,
  "material_hint": string or null,
  "units": "mm" | "inch" | "unknown",
  "envelope": {"length": number|null, "width": number|null, "height": number|null},
  "primary_operation": "extrude" | "revolve" | "loft" | "unknown",
  "feature_tree": [
    {
      "step": integer,
      "name": string,
      "feature_type": string,
      "operation": "new_body" | "join" | "cut",
      "dimensions": {},
      "tolerances": string or null,
      "spatial_relation": string or null,
      "notes": string or null
    }
  ],
  "assembly_components": [
    {"name": string, "role": string, "quantity": integer, "key_dims": {}}
  ],
  "standard_parts_detected": [
    {"standard": string, "nominal_size": string, "quantity": integer}
  ],
  "gdt_notes": [],
  "views_detected": [],
  "ambiguities": [string],
  "confidence": float,
  "needs_clarification": boolean
}"""


# ---------------------------------------------------------------------------
# Image encoding helpers
# ---------------------------------------------------------------------------

def _encode_image(source: Any) -> Tuple[str, str]:
    """Return (base64_string, mime_type) from path, bytes, or data-URL."""
    if isinstance(source, (str, Path)) and Path(str(source)).exists():
        p = Path(str(source))
        mime, _ = mimetypes.guess_type(str(p))
        mime = mime or "image/png"
        with open(p, "rb") as fh:
            return base64.b64encode(fh.read()).decode(), mime
    if isinstance(source, bytes):
        return base64.b64encode(source).decode(), "image/png"
    if isinstance(source, str):
        if source.startswith("data:"):
            header, encoded = source.split(",", 1)
            mime = header.split(";")[0].replace("data:", "")
            return encoded.strip(), mime
        # Assume already base64
        return source.strip(), "image/png"
    return "", "image/png"


# ---------------------------------------------------------------------------
# Deterministic fallback extractor
# ---------------------------------------------------------------------------

_FAMILY_KEYWORDS: Dict[str, List[str]] = {
    "gripper": ["gripper", "claw", "finger", "jaw", "robotic hand"],
    "gearbox": ["gearbox", "gear pair", "transmission", "reducer", "gears"],
    "bearing_housing": ["bearing housing", "pillow block", "plummer block"],
    "manifold": ["manifold", "distribution block", "valve block"],
    "shaft": ["shaft", "axle", "spindle", "rod", "bar"],
    "bracket": ["bracket", "mount", "clamp", "fixture", "brace"],
    "flange": ["flange", "coupling flange", "pipe flange"],
    "fastener": ["bolt", "nut", "screw", "washer", "stud", "pin"],
    "bearing": ["bearing", "ball bearing", "roller bearing"],
    "gear": ["gear", "pinion", "sprocket", "worm"],
    "plate": ["plate", "base plate", "mounting plate", "panel"],
}

_PROCESS_KEYWORDS: Dict[str, List[str]] = {
    "CNC milling": ["mill", "milling", "machined", "cnc", "pocket", "slot"],
    "turning": ["turned", "lathe", "turning", "shaft", "cylindrical"],
    "3D printing": ["3d print", "fdm", "sla", "additive"],
    "casting": ["cast", "casting", "foundry"],
    "sheet metal": ["sheet metal", "stamped", "bent", "press brake"],
}

_MATERIAL_KEYWORDS: Dict[str, List[str]] = {
    "Aluminum 6061-T6": ["aluminum", "aluminium", "al6061", "6061"],
    "Aluminum 7075-T6": ["al7075", "7075"],
    "Steel 1045": ["steel", "carbon steel", "mild steel"],
    "Stainless Steel 304": ["stainless", "ss304", "304 ss"],
    "Alloy Steel 4140": ["4140", "alloy steel", "chrome-moly"],
    "Cast Iron": ["cast iron", "grey iron", "gray iron"],
    "Nylon PA66": ["nylon", "polyamide", "pa66"],
    "PEEK": ["peek", "polyetheretherketone"],
}


def _detect_family(text: str) -> str:
    t = text.lower()
    for family, kws in _FAMILY_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return family
    return "custom_part"


def _detect_process(text: str) -> Optional[str]:
    t = text.lower()
    for process, kws in _PROCESS_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return process
    return None


def _detect_material(text: str) -> Optional[str]:
    t = text.lower()
    for mat, kws in _MATERIAL_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return mat
    return None


def _extract_dimensions_from_text(text: str) -> Dict[str, Any]:
    """Extract envelope and key dimensions from natural language."""
    dims: Dict[str, Any] = {}
    t = text.lower()

    # Box dimensions: 100x80x10, 100 × 80 × 10
    box_m = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*[x×*by\s]+\s*(\d+(?:\.\d+)?)\s*(?:mm)?'
        r'(?:\s*[x×*by\s]+\s*(\d+(?:\.\d+)?))?',
        t,
    )
    if box_m:
        dims["envelope"] = {
            "length": float(box_m.group(1)),
            "width": float(box_m.group(2)),
            "height": float(box_m.group(3)) if box_m.group(3) else None,
        }

    # Diameter
    dia_m = re.search(
        r'(?:[⌀ø]|diameter|dia|od)\s*[:=]?\s*(\d+(?:\.\d+)?)'
        r'|(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:diameter|dia|od\b)',
        t,
    )
    if dia_m:
        dims["diameter"] = float(dia_m.group(1) or dia_m.group(2))

    # Height / length
    ht_m = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:tall|height|high)'
        r'|(?:height|tall|long|length)\s*[:=]?\s*(\d+(?:\.\d+)?)',
        t,
    )
    if ht_m:
        dims["height"] = float(ht_m.group(1) or ht_m.group(2))

    # Collect raw numbers
    raw_nums = [float(n) for n in re.findall(r'\b(\d+(?:\.\d+)?)\b', t) if float(n) > 0]
    dims["raw_numbers"] = raw_nums[:32]

    return dims


def _build_deterministic_intent(
    user_prompt: str,
    image_count: int = 0,
) -> Dict[str, Any]:
    """Offline deterministic intent extraction from text + image count heuristics."""
    family = _detect_family(user_prompt)
    process = _detect_process(user_prompt)
    material = _detect_material(user_prompt)
    extracted = _extract_dimensions_from_text(user_prompt)

    is_asm = any(
        kw in user_prompt.lower()
        for kw in ["assembly", "gripper", "gearbox", "clamp", "fingers", "mechanism", "manifold"]
    )
    if family in ("gripper", "gearbox", "manifold"):
        is_asm = True

    envelope = extracted.get("envelope")
    if not envelope and extracted.get("diameter"):
        d = extracted["diameter"]
        h = extracted.get("height", d)
        envelope = {"length": d, "width": d, "height": h}
    if not envelope:
        envelope = {"length": None, "width": None, "height": None}

    # Confidence: higher with more context
    base_conf = 0.40 if image_count == 0 else (0.55 if image_count == 1 else 0.65)
    if family != "custom_part":
        base_conf += 0.10
    if process:
        base_conf += 0.05
    if envelope.get("length"):
        base_conf += 0.10
    confidence = min(base_conf, 0.75)

    ambiguities = []
    if not envelope.get("length"):
        ambiguities.append("Overall envelope dimensions not found in prompt")
    if not material:
        ambiguities.append("Material not specified — defaulting based on component family")
    if not process:
        ambiguities.append("Manufacturing process not specified")

    return {
        "part_name": None,
        "component_family": family,
        "is_assembly": is_asm,
        "manufacturing_process": process,
        "material_hint": material,
        "units": "mm" if "inch" not in user_prompt.lower() else "inch",
        "envelope": envelope,
        "primary_operation": "revolve" if family in ("shaft", "gear", "bearing") else "extrude",
        "feature_tree": [],
        "assembly_components": [],
        "standard_parts_detected": [],
        "gdt_notes": [],
        "views_detected": [],
        "ambiguities": ambiguities,
        "confidence": round(confidence, 2),
        "needs_clarification": confidence < 0.60 or not envelope.get("length"),
        "source": "deterministic_fallback",
    }


# ---------------------------------------------------------------------------
# LLM-backed extraction
# ---------------------------------------------------------------------------

def _build_llm_content(
    images: List[Any],
    user_prompt: str,
) -> List[Dict[str, Any]]:
    """Build LangChain HumanMessage content list with system prompt + images + user context."""
    content: List[Dict[str, Any]] = [
        {"type": "text", "text": _VISION_SYSTEM_PROMPT},
    ]

    for img in images[:3]:  # Cap at 3 images
        b64, mime = _encode_image(img)
        if b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            })

    if user_prompt:
        content.append({
            "type": "text",
            "text": (
                f"User description / additional context:\n{user_prompt}\n\n"
                "Now output the structured JSON intent exactly matching the schema above."
            ),
        })
    else:
        content.append({
            "type": "text",
            "text": "Output the structured JSON intent exactly matching the schema above.",
        })

    return content


def _parse_intent_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """Extract and validate JSON from LLM response."""
    cleaned = raw_text.strip()
    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()

    # Try direct parse
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "component_family" in data:
            return data
    except json.JSONDecodeError:
        pass

    # Balanced-brace extraction
    start = cleaned.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(cleaned)):
            c = cleaned[i]
            if esc:
                esc = False
                continue
            if c == "\\" and in_str:
                esc = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(cleaned[start : i + 1])
                        if isinstance(obj, dict) and "component_family" in obj:
                            return obj
                    except Exception:
                        break
        start = cleaned.find("{", start + 1)

    return None


def _merge_intent_with_fallback(
    llm_intent: Dict[str, Any],
    fallback: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge LLM intent with deterministic fallback — LLM wins for non-null fields."""
    merged = fallback.copy()
    for k, v in llm_intent.items():
        if v is not None and v != [] and v != {}:
            merged[k] = v
    # Ensure required fields
    merged.setdefault("ambiguities", [])
    merged.setdefault("confidence", fallback.get("confidence", 0.5))
    merged.setdefault("needs_clarification", merged["confidence"] < 0.6)
    merged.pop("source", None)
    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_design_intent(
    images: Optional[Any] = None,
    user_prompt: str = "",
    raise_on_error: bool = False,
) -> Dict[str, Any]:
    """
    Primary entry point for structured design intent extraction.

    Args:
        images: Single image or list of images. Each may be:
                - file path (str/Path)
                - raw bytes
                - base64 data-URL string ("data:image/png;base64,...")
        user_prompt: Natural language description from the user.
        raise_on_error: If True, re-raises LLM exceptions instead of falling back.

    Returns:
        A dict conforming to the MechanicalDesignIntent schema.
        Always returns a valid dict — never raises in default mode.
    """
    # Normalise images to list
    if images is None:
        img_list: List[Any] = []
    elif isinstance(images, list):
        img_list = images
    else:
        img_list = [images]

    # Filter valid images
    valid_images = []
    for img in img_list:
        b64, _ = _encode_image(img)
        if b64:
            valid_images.append(img)

    # Build deterministic baseline (always available)
    fallback_intent = _build_deterministic_intent(user_prompt, image_count=len(valid_images))

    # Attempt LLM extraction
    if valid_images:
        try:
            from langchain_core.messages import HumanMessage
            llm = get_design_llm()

            content = _build_llm_content(valid_images, user_prompt)
            msg = HumanMessage(content=content)
            res = llm.invoke([msg])
            raw_text = res.content if hasattr(res, "content") else str(res)

            llm_intent = _parse_intent_response(raw_text)
            if llm_intent:
                # Merge: LLM result enriched by fallback for any missing fields
                merged = _merge_intent_with_fallback(llm_intent, fallback_intent)
                merged["source"] = "llm_vision"
                return merged
        except Exception as exc:
            print(f"Intent extractor vision-LLM notice: {exc}", file=sys.stderr)
            if raise_on_error:
                raise

    # Text-only LLM path (no images but prompt provided)
    if not valid_images and user_prompt:
        try:
            llm = get_supervisor_llm()

            res = llm.invoke([
                ("system", _TEXT_ONLY_SYSTEM_PROMPT),
                ("user", f"User description:\n{user_prompt}\n\nOutput the structured JSON intent.")
            ])
            raw_text = res.content if hasattr(res, "content") else str(res)
            llm_intent = _parse_intent_response(raw_text)
            if llm_intent:
                merged = _merge_intent_with_fallback(llm_intent, fallback_intent)
                merged["source"] = "llm_text"
                return merged
        except Exception as exc:
            print(f"Intent extractor text-LLM notice: {exc}", file=sys.stderr)

    # Pure deterministic fallback
    return fallback_intent


def build_clarification_question(intent: Dict[str, Any]) -> Optional[str]:
    """
    If the intent has needs_clarification=True, return a targeted question string.
    Returns None if no clarification needed.
    """
    if not intent.get("needs_clarification"):
        return None

    parts = [
        "I need a bit more information to generate an accurate CAD model. "
        "Could you please clarify the following?\n"
    ]

    # Missing envelope
    env = intent.get("envelope", {})
    if not env.get("length") and not env.get("height"):
        parts.append("• **Overall size**: What are the approximate length × width × height (or diameter × height) of this part in mm?")

    # Missing family
    if intent.get("component_family") == "custom_part":
        parts.append("• **Part type**: What kind of mechanical component is this? (e.g. bracket, shaft, housing, gripper, gear, flange)")

    # List all detected ambiguities
    for amb in intent.get("ambiguities", [])[:4]:
        parts.append(f"• {amb}")

    return "\n".join(parts)


def intent_to_supervisor_hints(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts extracted intent into supervisor query hints for asset retrieval.
    Returns a dict of category, keyword, and dimensional search terms.
    """
    hints: Dict[str, Any] = {}

    family = intent.get("component_family", "")
    hints["primary_category"] = family

    # Build keyword list for BM25 retrieval
    keywords = [family]
    for std_part in intent.get("standard_parts_detected", []):
        if std_part.get("nominal_size"):
            keywords.append(std_part["nominal_size"].lower())
        if std_part.get("standard"):
            keywords.append(std_part["standard"].lower())
    hints["keywords"] = keywords

    # Dimensional constraints for retrieval
    dim_constraints: Dict[str, float] = {}
    env = intent.get("envelope") or {}
    if env.get("length"):
        dim_constraints["length"] = float(env["length"])
    if env.get("height"):
        dim_constraints["height"] = float(env["height"])
    for feat in intent.get("feature_tree", []):
        dims = feat.get("dimensions") or {}
        for k, v in dims.items():
            if v and isinstance(v, (int, float)):
                dim_constraints.setdefault(k, float(v))
    hints["dimensional_constraints"] = dim_constraints

    # Sub-component names for assembly retrieval
    sub_comp_names = [c["name"] for c in intent.get("assembly_components", []) if c.get("name")]
    hints["sub_component_names"] = sub_comp_names

    return hints
