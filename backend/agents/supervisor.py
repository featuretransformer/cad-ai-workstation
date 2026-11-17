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
from utils.macro_rag import query_macro_rag
from cad.brief_schema import build_cad_brief


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

    # 7b. Taper / Angle
    taper_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:°|deg(?:ree)?s?)\s*(?:taper|included|half[\s-]*angle)', p_lower)
    if taper_m:
        res["taper_angle"] = float(taper_m.group(1))

    # 8. Keyway dimensions (e.g. 5mm wide x 3mm deep keyway)
    kw_m = re.search(r'(\d+(?:\.\d+)?)\s*mm\s*(?:wide|width).*?(\d+(?:\.\d+)?)\s*mm\s*(?:deep|depth)\s*(?:key(?:way)?|slot)', p_lower)
    if not kw_m:
        kw_m = re.search(r'key(?:way)?\s*(?:[:=])?\s*(\d+(?:\.\d+)?)\s*(?:mm)?\s*[xX×]\s*(\d+(?:\.\d+)?)', p_lower)
    if kw_m:
        res["keyway"] = {"width": float(kw_m.group(1)), "depth": float(kw_m.group(2))}

    # 9. D-flat / D-profile shaft
    d_flat_m = re.search(r'd[- ]?(?:flat|profile|shaft)', p_lower)
    if d_flat_m:
        res["d_profile"] = True

    return res


def _format_geometry_context(dims: Dict[str, Any], intent: Dict[str, Any], prompt: str) -> str:
    """Formats exact, pre-computed mathematical coordinates to ground LLM CAD generation."""
    lines = []
    p_lower = prompt.lower()
    import math

    # 1. Base Body Geometry & Dimensions
    if "box" in dims:
        b = dims["box"]
        lx, ly, lz = b['length'], b['width'], b['height']
        lines.append(f"• BASE ENVELOPE (BOX): Length={lx}mm, Width={ly}mm, Height={lz}mm.")
        lines.append(f"  Solid center is at [0.0, 0.0, 0.0]. X range: [{-lx/2.0:.1f}, {lx/2.0:.1f}], Y range: [{-ly/2.0:.1f}, {ly/2.0:.1f}].")
    elif "cylinder" in dims:
        c = dims["cylinder"]
        dia, rad, h = c['diameter'], c['radius'], c['height']
        lines.append(f"• BASE ENVELOPE (CYLINDER): Diameter={dia}mm (Radius={rad}mm), Height={h}mm.")
        lines.append(f"  Solid center is at [0.0, 0.0, 0.0]. Z range: [{-h/2.0:.1f}, {h/2.0:.1f}].")

    # 2. Fastener Specification
    if "fastener" in dims:
        lines.append(f"• FASTENER STANDARD: {dims['fastener']}. Use clearance hole diameter = {dims['hole_diameter']}mm (radius = {dims['hole_radius']}mm).")
        if "cbore_spec" in dims:
            cb = dims["cbore_spec"]
            lines.append(f"  Counterbore: dia = {cb['cbore_dia']}mm, depth = {cb['cbore_depth']}mm.")

    # 3. Central Bore
    if "bore" in dims:
        br = dims["bore"]
        lines.append(f"• CENTRAL BORE: Diameter={br['diameter']}mm (Radius={br['radius']}mm). Position = [0.0, 0.0, 0.0]. Operation = 'cut'.")

    # 4. Bolt Circle (PCD) Coordinates
    if "pcd" in dims:
        r = dims["pcd"]["radius"]
        dia = dims["pcd"]["diameter"]
        hole_count = 4
        hc_match = re.search(r'(\d+)\s*(?:x|holes?|bolts?)', p_lower)
        if hc_match:
            try:
                cnt = int(hc_match.group(1))
                if cnt in (3, 4, 5, 6, 8, 10, 12):
                    hole_count = cnt
            except ValueError:
                pass

        lines.append(f"• BOLT CIRCLE (PCD): Diameter={dia}mm (Radius={r}mm) with {hole_count} holes.")
        lines.append("  EXACT HOLE COORDINATES (pre-computed, do not alter):")
        for i in range(hole_count):
            angle = (2.0 * math.pi * i) / hole_count
            hx = round(r * math.cos(angle), 2)
            hy = round(r * math.sin(angle), 2)
            lines.append(f"    - PCD Hole {i+1}: position=[{hx}, {hy}, 0.0]")

    # 5. Corner Holes for Rectangular Parts
    if "suggested_corner_hole_positions" in dims:
        lines.append("• 4 CORNER HOLES (pre-computed inside box bounds):")
        for i, pos in enumerate(dims["suggested_corner_hole_positions"]):
            lines.append(f"    - Corner Hole {i+1}: position={pos}")

    # 6. Hexagonal Head / Nut
    if "across_flats" in dims:
        lines.append(f"• HEXAGONAL FEATURE: Across flats S={dims['across_flats']}mm -> circumradius R={dims['hex_radius']}mm, side_count=6.")

    # 7. Taper Angle
    if "taper_angle" in dims:
        lines.append(f"• TAPER ANGLE: {dims['taper_angle']}° — use taper_angle parameter in extrude/revolve feature.")

    # 8. Keyway
    if "keyway" in dims:
        kw = dims["keyway"]
        lines.append(f"• KEYWAY: width={kw['width']}mm, depth={kw['depth']}mm — add a 'pocket' feature cut along the shaft axis.")

    # 9. D-profile
    if dims.get("d_profile"):
        lines.append("• D-PROFILE: Cut a flat pocket tangent to the shaft surface along the full shaft length, depth = shaft_radius * 0.15.")

    return "\n".join(lines)


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
        parsed_intent["dimensions"] = [float(d) for d in dim_matches if float(d) > 0][:30]

    # 1b. Merge rich MechanicalDesignIntent (populated by input_classifier via intent_extractor)
    # This always takes precedence over bare regex results when available.
    design_intent: Dict[str, Any] = state.get("design_intent") or {}
    if design_intent:
        # Component family (LLM is more reliable than regex keyword matching)
        if design_intent.get("component_family"):
            parsed_intent["component_family"] = design_intent["component_family"]
        # Assembly flag
        if design_intent.get("is_assembly") is not None:
            parsed_intent["is_assembly"] = design_intent["is_assembly"]
        # Envelope dimensions from structured output
        env = design_intent.get("envelope") or {}
        raw_env_dims = [v for v in [env.get("length"), env.get("width"), env.get("height")] if v]
        if raw_env_dims:
            parsed_intent.setdefault("dimensions", raw_env_dims)
        # Material hint
        if design_intent.get("material_hint"):
            parsed_intent.setdefault("material", design_intent["material_hint"])
        # Manufacturing process
        if design_intent.get("manufacturing_process"):
            parsed_intent.setdefault("manufacturing_process", design_intent["manufacturing_process"])
        # Feature types extracted from image/text by intent extractor
        if design_intent.get("feature_tree"):
            parsed_intent.setdefault("features", [
                f.get("feature_type", "") for f in design_intent["feature_tree"] if f.get("feature_type")
            ])
        # Assembly components list
        if design_intent.get("assembly_components"):
            parsed_intent.setdefault("detected_components", [
                c.get("name", "") for c in design_intent["assembly_components"] if c.get("name")
            ])
        # Units
        if design_intent.get("units"):
            parsed_intent.setdefault("units", design_intent["units"])

    # 2. Query Knowledge Base for Few-Shot Exemplars
    if parsed_intent.get("component_family") and parsed_intent["component_family"] != "custom_part":
        query_obj.family = parsed_intent["component_family"]
    if parsed_intent.get("features"):
        query_obj.features = parsed_intent["features"]
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

    # 3. Query Local CAD Asset Library for Standard Components & Reference Models
    retrieved_assets: List[Dict[str, Any]] = []
    try:
        from retrieval.hybrid_retriever import HybridRetriever, CADRetrievalQuery
        from retrieval.asset_schema import AssetUsageRole

        retriever = HybridRetriever()
        search_queries = []
        p_lower = prompt.lower()

        if any(k in p_lower for k in ["pin", "dowel", "pivot", "gripper"]):
            search_queries.append(CADRetrievalQuery(
                query_text=prompt,
                category="pin",
                required_dimensions={"diameter": 6.0},
                desired_role=AssetUsageRole.STANDARD_COMPONENT_REUSE,
                limit=2,
            ))
        if any(k in p_lower for k in ["bolt", "screw", "fastener", "nut", "m4", "m8", "m10", "m12", "gripper", "gearbox", "housing", "manifold"]):
            f_dim = {}
            if "m4" in p_lower:
                f_dim["thread_size"] = 4.0
            elif "m8" in p_lower:
                f_dim["thread_size"] = 8.0
            elif "m10" in p_lower:
                f_dim["thread_size"] = 10.0
            elif "m12" in p_lower:
                f_dim["thread_size"] = 12.0
            search_queries.append(CADRetrievalQuery(
                query_text=prompt,
                category="fastener",
                required_dimensions=f_dim if f_dim else None,
                desired_role=AssetUsageRole.STANDARD_COMPONENT_REUSE,
                limit=4,
            ))
        if any(k in p_lower for k in ["bearing", "gearbox", "housing", "pillow block"]):
            b_dim = {}
            if "8mm" in p_lower or "608" in p_lower:
                b_dim["bore_diameter"] = 8.0
            elif "20mm" in p_lower or "6204" in p_lower or "housing" in p_lower:
                b_dim["bore_diameter"] = 20.0
            search_queries.append(CADRetrievalQuery(
                query_text=prompt,
                category="bearing",
                required_dimensions=b_dim if b_dim else None,
                desired_role=AssetUsageRole.STANDARD_COMPONENT_REUSE,
                limit=2,
            ))
        if any(k in p_lower for k in ["gear", "gearbox", "pinion", "spur"]):
            search_queries.append(CADRetrievalQuery(
                query_text=prompt,
                category="gear",
                required_dimensions={"module": 2.0},
                desired_role=AssetUsageRole.STANDARD_COMPONENT_REUSE,
                limit=3,
            ))
        if any(k in p_lower for k in ["flange", "pipe", "manifold"]):
            search_queries.append(CADRetrievalQuery(
                query_text=prompt,
                category="flange",
                required_dimensions={"pcd": 85.0} if "dn25" in p_lower else None,
                desired_role=AssetUsageRole.STANDARD_COMPONENT_REUSE,
                limit=2,
            ))
        if any(k in p_lower for k in ["nipple", "grease", "lubricat", "housing"]):
            search_queries.append(CADRetrievalQuery(
                query_text=prompt,
                category="lubrication",
                desired_role=AssetUsageRole.STANDARD_COMPONENT_REUSE,
                limit=1,
            ))
        if any(k in p_lower for k in ["finger", "linkage", "elbow", "reference"]):
            search_queries.append(CADRetrievalQuery(
                query_text=prompt,
                desired_role=AssetUsageRole.DESIGN_REFERENCE,
                limit=2,
            ))

        if not search_queries:
            search_queries.append(CADRetrievalQuery(
                query_text=prompt,
                limit=5,
            ))

        seen_assets = set()
        for sq in search_queries:
            res_items = retriever.search(sq)
            for item in res_items:
                aid = item.asset.asset_id
                if aid not in seen_assets:
                    seen_assets.add(aid)
                    retrieved_assets.append({
                        "asset_id": aid,
                        "name": item.asset.name,
                        "category": item.asset.category,
                        "subcategory": item.asset.subcategory,
                        "description": item.asset.description,
                        "format": item.asset.format.value,
                        "geometry_nature": item.asset.geometry_nature.value,
                        "file_path": item.asset.file_path,
                        "score": item.total_score,
                        "compatibility": item.compatibility.model_dump(),
                        "is_compatible": item.compatibility.is_compatible,
                        "recommended_role": item.compatibility.recommended_role.value,
                        "provenance": item.asset.provenance.model_dump(),
                        "nominal_dimensions": item.asset.nominal_dimensions,
                        "match_reasons": item.match_reasons,
                    })
    except Exception as e:
        parsed_intent["asset_retrieval_warning"] = str(e)

    # ── Macro RAG Query (Upgrade 6) ──────────────────────────────────────────
    macro_exemplars = []
    try:
        detected_ops = list(parsed_intent.get("features", []))
        macro_exemplars = query_macro_rag(prompt, operations=detected_ops, limit=3)
    except Exception:
        pass

    geom_ctx = _format_geometry_context(sem_dims, parsed_intent, prompt)
    if macro_exemplars:
        geom_ctx += "\n\n=== RETRIEVED ZERO-TO-CAD AND HARDWARE MACRO ANCHORS ===\n"
        for ex in macro_exemplars:
            geom_ctx += f"- {ex['title']} ({ex['category']}):\n  Build snippet: {ex['build123d_snippet'][:120]}...\n"

    # Pre-execution engineering contract (CADBrief & Machine-Measurable Targets)
    cad_brief = build_cad_brief(prompt, parsed_intent, sem_dims)
    v_targets = [t.model_dump() for t in cad_brief.verification_targets]

    return {
        "parsed_intent": parsed_intent,
        "geometry_context": geom_ctx,
        "cad_brief": cad_brief.model_dump(),
        "verification_targets": v_targets,
        "retrieved_examples": retrieved_examples,
        "retrieved_assets": retrieved_assets,
        "macro_exemplars": macro_exemplars,
        "current_agent": "supervisor",
    }
