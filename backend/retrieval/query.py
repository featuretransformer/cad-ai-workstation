"""
Structured Query Interface for CADIR Knowledge Retrieval.
Translates user design intents or structured requirements into SQLite queries
and returns ranked, few-shot CADIR documents and build123d code snippets.
"""
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
import json
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.cadir.schema import CADIRDocument
from retrieval.index import KnowledgeIndex
from retrieval.ranker import rank_candidates


class CADIRQuery(BaseModel):
    """Structured query specification for retrieving relevant CAD models."""
    family: Optional[str] = Field(default=None, description="Component family category (e.g. 'washer', 'hex_nut', 'bracket')")
    features: Optional[List[str]] = Field(default=None, description="Desired feature types (e.g. ['extrude', 'hole', 'chamfer'])")
    keywords: Optional[List[str]] = Field(default=None, description="Free text keywords")
    difficulty: Optional[str] = Field(default=None, description="Desired complexity tier")
    source_dataset: Optional[str] = Field(default=None, description="Dataset filter (e.g. 'BenchCAD', 'DeepCAD')")
    limit: int = Field(default=5, ge=1, le=50)


KNOWN_FAMILIES = [
    "washer", "hex_nut", "nut", "bolt", "screw", "shaft", "flange",
    "bracket", "pulley", "gear", "bearing", "plate", "housing", "cylinder", "pin"
]

KNOWN_FEATURES = [
    "extrude", "revolve", "hole", "fillet", "chamfer", "box", "cylinder",
    "polygon", "cut", "union"
]


def parse_intent_to_query(prompt: str) -> CADIRQuery:
    """
    Extracts structured query parameters from a natural language design prompt.
    E.g. 'Create a washer with a 30mm hole and chamfered edges'
    -> family='washer', features=['hole', 'chamfer'], keywords=['washer', 'chamfered']
    """
    clean_p = prompt.lower()
    words = clean_p.replace(",", " ").replace(".", " ").split()

    detected_family = None
    for fam in KNOWN_FAMILIES:
        if fam in words or fam in clean_p:
            detected_family = fam
            break

    detected_features = []
    for feat in KNOWN_FEATURES:
        if feat in clean_p:
            detected_features.append(feat)

    # Keywords from words with length > 3
    keywords = [w for w in words if len(w) > 3 and w not in ["with", "from", "that", "this", "create", "make", "need"]]

    return CADIRQuery(
        family=detected_family,
        features=detected_features if detected_features else None,
        keywords=keywords[:5] if keywords else None,
        limit=5,
    )


def search_knowledge_base(
    index: KnowledgeIndex,
    query: Union[CADIRQuery, str],
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Executes a multi-tier search across the SQLite knowledge index:
    1. Filter candidates using SQL conditions.
    2. Rank candidates using multi-factor relevance scoring.
    3. Return top-k exemplars with CADIR models.
    """
    if isinstance(query, str):
        query_obj = parse_intent_to_query(query)
    else:
        query_obj = query

    max_results = limit if limit is not None else query_obj.limit

    raw_rows = []
    with index._get_connection() as conn:
        cursor = conn.cursor()

        # Fast path 1: If family is specified, query directly by indexed family column
        if query_obj.family:
            family_conds = ["family = ?"]
            family_params = [query_obj.family.lower().strip()]
            if query_obj.source_dataset:
                family_conds.append("source_dataset = ?")
                family_params.append(query_obj.source_dataset)
            if query_obj.difficulty:
                family_conds.append("difficulty = ?")
                family_params.append(query_obj.difficulty.lower())

            cursor.execute(f"""
                SELECT id, source_dataset, family, variant, difficulty,
                       feature_types, feature_count, sketch_count,
                       param_summary, cadir_json, description, code_snippet
                FROM cad_examples
                WHERE {' AND '.join(family_conds)}
                LIMIT 100
            """, family_params)
            raw_rows = cursor.fetchall()

            # Fast path 2: Prefix match on family index (e.g. 'pipe_')
            if not raw_rows:
                cursor.execute(f"""
                    SELECT id, source_dataset, family, variant, difficulty,
                           feature_types, feature_count, sketch_count,
                           param_summary, cadir_json, description, code_snippet
                    FROM cad_examples
                    WHERE family LIKE ?
                    LIMIT 100
                """, [f"{query_obj.family.lower().strip()}%"])
                raw_rows = cursor.fetchall()

        # Fallback path if no family or no rows found yet
        if not raw_rows:
            sql_conditions = []
            params: List[Any] = []
            if query_obj.source_dataset:
                sql_conditions.append("source_dataset = ?")
                params.append(query_obj.source_dataset)
            if query_obj.difficulty:
                sql_conditions.append("difficulty = ?")
                params.append(query_obj.difficulty.lower())

            where_clause = f"WHERE {' AND '.join(sql_conditions)}" if sql_conditions else ""
            cursor.execute(f"""
                SELECT id, source_dataset, family, variant, difficulty,
                       feature_types, feature_count, sketch_count,
                       param_summary, cadir_json, description, code_snippet
                FROM cad_examples
                {where_clause}
                LIMIT 100
            """, params)
            raw_rows = cursor.fetchall()

    candidate_dicts = [dict(row) for row in raw_rows]

    # Rank candidates by relevance
    ranked = rank_candidates(
        candidates=candidate_dicts,
        family=query_obj.family,
        features=query_obj.features,
        keywords=query_obj.keywords,
        difficulty=query_obj.difficulty,
    )

    top_results = ranked[:max_results]

    # Parse CADIRDocuments on returned results
    for r in top_results:
        try:
            r["cadir_document"] = CADIRDocument.from_json(r["cadir_json"])
        except Exception:
            r["cadir_document"] = None

    return top_results
