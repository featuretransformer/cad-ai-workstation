"""
Relevance Scoring and Ranking for CADIR Exemplar Retrieval.
Scores candidate mechanical models based on component family affinity,
feature set overlap, keyword matching, and complexity alignment.
"""
from typing import Dict, Any, List, Optional
import json


def rank_candidates(
    candidates: List[Dict[str, Any]],
    family: Optional[str] = None,
    features: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    difficulty: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Ranks candidate exemplars by computing a multi-factor relevance score.
    Returns sorted list of candidates with attached '_score' and '_match_reasons'.
    """
    target_family = family.lower().strip() if family else None
    target_features = [f.lower().strip() for f in features] if features else []
    target_keywords = [k.lower().strip() for k in keywords] if keywords else []
    target_diff = difficulty.lower().strip() if difficulty else None

    scored_candidates = []

    for c in candidates:
        score = 0.0
        reasons = []

        cand_fam = (c.get("family") or "").lower()
        cand_desc = (c.get("description") or "").lower()
        cand_id = (c.get("id") or "").lower()
        cand_diff = (c.get("difficulty") or "").lower()

        raw_feat = c.get("feature_types", [])
        if isinstance(raw_feat, str):
            try:
                cand_features = [f.lower() for f in json.loads(raw_feat)]
            except Exception:
                cand_features = []
        else:
            cand_features = [str(f).lower() for f in raw_feat]

        # 1. Component Family Matching (Highest weight)
        if target_family:
            if cand_fam == target_family:
                score += 50.0
                reasons.append(f"exact_family_match({target_family})")
            elif target_family in cand_fam or cand_fam in target_family:
                score += 30.0
                reasons.append(f"partial_family_match({cand_fam})")

        # 2. Feature Type Overlap
        if target_features:
            matched_features = [f for f in target_features if f in cand_features]
            if matched_features:
                f_score = len(matched_features) * 15.0
                score += f_score
                reasons.append(f"features_matched({','.join(matched_features)})")

        # 3. Keyword Matching
        if target_keywords:
            matched_kw = [
                kw for kw in target_keywords
                if kw in cand_fam or kw in cand_desc or kw in cand_id
            ]
            if matched_kw:
                k_score = len(matched_kw) * 10.0
                score += k_score
                reasons.append(f"keywords_matched({','.join(matched_kw)})")

        # 4. Difficulty Alignment
        if target_diff and cand_diff == target_diff:
            score += 10.0
            reasons.append(f"difficulty_matched({target_diff})")

        # 5. Quality Bonus: Executable build123d code exists
        if c.get("code_snippet"):
            score += 5.0

        item = dict(c)
        item["_score"] = round(score, 2)
        item["_match_reasons"] = reasons
        scored_candidates.append(item)

    # Sort descending by score, then ascending by feature count for simpler models
    scored_candidates.sort(
        key=lambda x: (x["_score"], -x.get("feature_count", 0)),
        reverse=True,
    )

    return scored_candidates
