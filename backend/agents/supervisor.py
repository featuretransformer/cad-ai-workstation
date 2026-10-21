"""
Supervisor Agent Node.
Parses mechanical engineering intent, extracts parametric constraints,
and queries the SQLite knowledge base for relevant few-shot CADIR exemplars.
"""
from typing import Dict, Any, List
from pathlib import Path
import json
import re
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.state import AgentState
from retrieval.index import KnowledgeIndex
from retrieval.query import search_knowledge_base, parse_intent_to_query, CADIRQuery
from config import settings


def _extract_semantic_dimensions(prompt: str) -> Dict[str, Any]:
    """
    Extracts semantic engineering dimensions and geometric grounding constraints from user prompts.
    Provides canonical dimensions for box envelopes, cylinders, fasteners, bores, and bolt circles.
    """
    p_lower = prompt.lower()
    res: Dict[str, Any] = {}

    # 1. Box / Block dimensions (e.g., 100x80x10mm, 100 × 80 × 10 mm, 50x50x5)
    box_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*[x×*by\s]+\s*(\d+(?:\.\d+)?)\s*(?:mm)?(?:\s*[x×*by\s]+\s*(\d+(?:\.\d+)?))?', p_lower)
    if box_m:
        lx = float(box_m.group(1))
        ly = float(box_m.group(2))
        lz = float(box_m.group(3)) if box_m.group(3) else 10.0
        res["box"] = {"length": lx, "width": ly, "height": lz}
        res["envelope"] = [lx, ly, lz]

    # 2. Cylindrical dimensions (e.g., 80mm diameter or diameter 80mm, 120mm tall / long / length)
    dia_m = re.search(r'(?:(?:[⌀ø]|diameter|dia|od)\s*[:=]?\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:diameter|dia|od\b))', p_lower)
    len_m = re.search(r'(?:(\d+(?:\.\d+)?)\s*(?:mm)?[\s\-]*(?:long|length|tall|height)|(?:height|tall|length|long)\s*[:=]?\s*(\d+(?:\.\d+)?))', p_lower)
    if dia_m:
        od_str = dia_m.group(1) or dia_m.group(2)
        od = float(od_str)
        hgt_val = None
        if len_m:
            hgt_val = float(len_m.group(1) or len_m.group(2))
        hgt = hgt_val if hgt_val else (res.get("envelope", [od, od, 50.0])[2])
        res["cylinder"] = {"diameter": od, "radius": od / 2.0, "height": hgt}
        res.setdefault("envelope", [od, od, hgt])

    # 3. Standard Metric Fastener Hole sizing (ISO clearance standard)
    FASTENER_STANDARDS = {
        "m3": {"clearance_dia": 3.4, "cbore_dia": 6.5, "cbore_depth": 3.5},
        "m4": {"clearance_dia": 4.5, "cbore_dia": 8.0, "cbore_depth": 4.5},
        "m5": {"clearance_dia": 5.5, "cbore_dia": 10.0, "cbore_depth": 5.5},
        "m6": {"clearance_dia": 6.6, "cbore_dia": 11.0, "cbore_depth": 6.5},
        "m8": {"clearance_dia": 9.0, "cbore_dia": 15.0, "cbore_depth": 8.5},
        "m10": {"clearance_dia": 11.0, "cbore_dia": 18.0, "cbore_depth": 10.5},
        "m12": {"clearance_dia": 13.5, "cbore_dia": 20.0, "cbore_depth": 12.5},
    }
    for m_key, spec in FASTENER_STANDARDS.items():
        if re.search(rf'\b{m_key}\b', p_lower):
            res["fastener"] = m_key.upper()
            res["hole_diameter"] = spec["clearance_dia"]
            res["hole_radius"] = round(spec["clearance_dia"] / 2.0, 2)
            res["cbore_spec"] = spec
            break

    # 4. Central Bore / Internal Pocket (e.g. 40mm bore, 30 mm through-bore)
    bore_m = re.search(r'(?:bore|bearing|through-bore)\s*[:=]?\s*(?:[⌀ø])?\s*(\d+(?:\.\d+)?)', p_lower)
    if bore_m:
        b_dia = float(bore_m.group(1))
        res["bore"] = {"diameter": b_dia, "radius": b_dia / 2.0}

    # 5. Pitch Circle Diameter (PCD / Bolt Circle)
    pcd_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:pcd|bolt\s*circle)', p_lower)
    if pcd_m:
        pcd_val = float(pcd_m.group(1))
        res["pcd"] = {"diameter": pcd_val, "radius": pcd_val / 2.0}

    # 6. Across Flats (Hex nut / hex bolt, e.g. 13mm across flats, 17mm af)
    af_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:across[\s\-]*flats|af\b)', p_lower)
    if af_m:
        af_val = float(af_m.group(1))
        res["across_flats"] = af_val
        res["hex_radius"] = round(af_val / 1.73205, 2)

    # 7. Pre-compute corner hole coordinates if box and 4 corner holes requested
    if "box" in res and any(k in p_lower for k in ["corner", "4 holes", "four holes", "four corner"]):
        b_len = res["box"]["length"]
        b_wid = res["box"]["width"]
        margin = max(8.0, min(b_len, b_wid) * 0.12)
        hx = round(b_len / 2.0 - margin, 2)
        hy = round(b_wid / 2.0 - margin, 2)
        res["suggested_corner_hole_positions"] = [
            [hx, hy, 0.0],
            [-hx, hy, 0.0],
            [-hx, -hy, 0.0],
            [hx, -hy, 0.0],
        ]

    return res


def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Parses design intent and queries the local knowledge base for relevant CADIR exemplars.
    """
    prompt = state.get("user_prompt", "")
    existing_cadir = state.get("cadir_document")

    # 1. Parse engineering intent
    parsed_intent: Dict[str, Any] = state.get("parsed_intent") or {}
    query_obj = parse_intent_to_query(prompt)

    if query_obj.family:
        parsed_intent["component_family"] = query_obj.family
    elif existing_cadir and existing_cadir.component_family:
        parsed_intent["component_family"] = existing_cadir.component_family
    else:
        parsed_intent["component_family"] = "custom_part"

    if query_obj.features:
        parsed_intent["target_features"] = query_obj.features

    # Semantic dimensional extraction
    sem_dims = _extract_semantic_dimensions(prompt)
    if sem_dims:
        parsed_intent["semantic_parameters"] = sem_dims

    # Extract dimensions from prompt (e.g. 50mm, 20 mm, diameter 30)
    dim_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:mm|in)?", prompt)
    if dim_matches:
        parsed_intent["dimensions"] = [float(d) for d in dim_matches if float(d) > 0][:5]

    # 2. Query Knowledge Base for Few-Shot Exemplars
    retrieved_examples: List[Dict[str, Any]] = []
    try:
        kb_path = Path(settings.knowledge_db_path)
        if kb_path.exists():
            index = KnowledgeIndex(kb_path)
            results = search_knowledge_base(index, query_obj, limit=3)
            for r in results:
                retrieved_examples.append({
                    "id": r["id"],
                    "source_dataset": r.get("source_dataset"),
                    "family": r.get("family"),
                    "difficulty": r.get("difficulty"),
                    "feature_types": r.get("feature_types"),
                    "score": r.get("_score"),
                    "code_snippet": r.get("code_snippet", "")[:400],
                    "cadir_json": r.get("cadir_json"),
                })
    except Exception as e:
        parsed_intent["retrieval_warning"] = str(e)

    return {
        "parsed_intent": parsed_intent,
        "retrieved_examples": retrieved_examples,
        "current_agent": "supervisor",
    }
