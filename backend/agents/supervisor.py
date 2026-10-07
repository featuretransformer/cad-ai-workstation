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
