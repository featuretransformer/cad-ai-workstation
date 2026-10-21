"""
Prompt Complexity Classifier Agent.
Analyzes natural language mechanical prompts to quantify geometric complexity
and determine whether hierarchical feature decomposition is required.
"""
from typing import Dict, Any, List, Tuple
from pathlib import Path
import re
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.state import AgentState

GEOMETRIC_FEATURE_NOUNS = [
    "bore", "hole", "holes", "boss", "bosses", "flange", "flanges",
    "pocket", "pockets", "fin", "fins", "rib", "ribs", "groove", "grooves",
    "slot", "slots", "fillet", "fillets", "chamfer", "chamfers", "thread", "threads",
    "keyway", "keyways", "lug", "lugs", "cutout", "cutouts", "taper", "step", "steps",
    "counterbore", "countersink", "recess", "recesses", "spigot", "web", "webs",
    "cavity", "channel", "channels", "port", "ports", "lip", "collar",
]

SPATIAL_RELATION_PHRASES = [
    r"on top of", r"inside", r"through", r"around", r"connected by",
    r"opposing", r"opposite", r"at each end", r"at the center", r"in the middle",
    r"evenly spaced", r"concentric", r"offset from", r"recessed into", r"radial",
    r"along the", r"protruding from", r"extending from", r"underneath", r"between",
]

COMPLEXITY_CONJUNCTIONS = [
    r"\bwith\b", r"\band\b", r"\bplus\b", r"\bas well as\b",
    r"\bfeaturing\b", r"\bhaving\b", r"\bequipped with\b", r"\bincluding\b",
]


def evaluate_prompt_complexity(prompt: str) -> Dict[str, Any]:
    """
    Evaluates mechanical prompt complexity to determine if sequential
    feature decomposition should be triggered.
    
    Returns structured scoring breakdown and boolean verdict.
    """
    p_lower = prompt.lower()
    
    # 1. Detect geometric feature nouns
    detected_features: List[str] = []
    for noun in GEOMETRIC_FEATURE_NOUNS:
        # Match whole word
        if re.search(rf"\b{noun}\b", p_lower):
            detected_features.append(noun)
    
    # Deduplicate singular/plural
    normalized_features = set()
    for feat in detected_features:
        base = feat.rstrip("es").rstrip("s")
        normalized_features.add(base)
    feature_count = len(normalized_features)

    # 2. Count spatial / positional relational constraints
    spatial_matches = []
    for phrase in SPATIAL_RELATION_PHRASES:
        if re.search(phrase, p_lower):
            spatial_matches.append(phrase)
    spatial_count = len(spatial_matches)

    # 3. Count explicit dimensions (e.g. 35mm, M8, ⌀30, 100x80x60)
    dimension_patterns = [
        r"\b\d+(?:\.\d+)?\s*(?:mm|cm|in|m)\b",
        r"[⌀ø]\s*\d+(?:\.\d+)?",
        r"\bm\d+(?:x\d+(?:\.\d+)?)?\b",
        r"\b\d+\s*[x×]\s*\d+(?:\s*[x×]\s*\d+)?\b",
        r"\b\d+\s*deg(?:ree)?s?\b",
        r"\bpcd\b",
    ]
    dims_found = set()
    for pat in dimension_patterns:
        for m in re.finditer(pat, p_lower):
            dims_found.add(m.group(0))
    dim_count = len(dims_found)

    # 4. Word count & conjunction structure
    words = re.findall(r"\b\w+\b", prompt)
    word_count = len(words)
    conjunction_count = sum(1 for c in COMPLEXITY_CONJUNCTIONS if re.search(c, p_lower))

    # 5. Calculate weighted score
    score = (
        (feature_count * 1.2) +
        (spatial_count * 1.5) +
        (dim_count * 0.4) +
        (conjunction_count * 0.6) +
        (1.5 if word_count > 25 else 0.0) +
        (2.0 if word_count > 50 else 0.0)
    )

    # Trigger threshold:
    # Requires at least 3 distinct features AND score >= 4.0, or >= 4 features
    is_complex = bool((feature_count >= 3 and score >= 4.0) or (feature_count >= 4))

    return {
        "complexity_score": round(score, 2),
        "is_complex": is_complex,
        "feature_count": feature_count,
        "detected_features": sorted(list(normalized_features)),
        "spatial_constraints": spatial_matches,
        "dimensions_detected": sorted(list(dims_found)),
        "word_count": word_count,
    }


def complexity_classifier_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node to assess prompt complexity."""
    prompt = state.get("user_prompt", "")
    res = evaluate_prompt_complexity(prompt)
    
    return {
        "complexity_score": res["complexity_score"],
        "is_complex_part": res["is_complex"] and not state.get("is_assembly", False),
    }
