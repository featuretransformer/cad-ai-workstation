"""
Hybrid CAD Asset Retriever.
Combines:
1. Tokenized text & semantic keyword matching (names, descriptions, tags, standards)
2. Tolerance-aware dimensional metadata proximity scoring
3. Bounding-box aspect ratio / geometric signature matching
4. Automated mechanical compatibility verification and unknowns recording
5. 4-mode engineering classification (reuse vs reference vs generate vs assemble)
"""
import re
import math
from typing import Dict, Any, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from retrieval.asset_schema import (
    CADAssetMetadata,
    CADAssetFormat,
    GeometryNature,
    AssetUsageRole,
    VerificationStatus,
)
from retrieval.asset_library import CADAssetLibrary
from retrieval.compatibility_verifier import CompatibilityVerifier, CompatibilityReport


class CADRetrievalQuery(BaseModel):
    """Specification for hybrid CAD asset retrieval."""
    query_text: str = Field(..., description="Free text prompt or component specification")
    category: Optional[str] = Field(default=None, description="fastener, bearing, gear, flange, pin, etc.")
    subcategory: Optional[str] = None
    desired_role: Optional[AssetUsageRole] = None
    required_dimensions: Optional[Dict[str, float]] = Field(
        default=None,
        description="Key dimensional requirements (e.g. bore_diameter, thread_size, pitch_diameter, pcd)"
    )
    dimensional_tolerance: float = Field(default=0.15, description="Relative tolerance for dimensional matching")
    desired_aspect_ratio: Optional[Tuple[float, float]] = Field(
        default=None,
        description="Optional aspect ratios (L/W, W/H)"
    )
    format_filter: Optional[CADAssetFormat] = None
    limit: int = Field(default=5, ge=1, le=50)


class ScoredAssetResult(BaseModel):
    """Ranked retrieval candidate with explainable scoring breakdown."""
    asset: CADAssetMetadata
    rank: int
    total_score: float
    text_score: float
    dimensional_score: float
    geometric_score: float
    compatibility: CompatibilityReport
    match_reasons: List[str]


class HybridRetriever:
    """Hybrid multi-factor search engine for local CAD assets."""

    def __init__(self, library: Optional[CADAssetLibrary] = None):
        self.library = library or CADAssetLibrary()
        # Ensure library is seeded
        if self.library.count_assets() == 0:
            self.library.seed_curated_library()

    def search(self, query: CADRetrievalQuery) -> List[ScoredAssetResult]:
        """
        Executes hybrid retrieval:
        1. Candidates fetched from library.
        2. Textual matching scored.
        3. Dimensional proximity scored.
        4. Geometric aspect ratio scored.
        5. Compatibility verifier evaluated.
        6. Candidates sorted and returned.
        """
        candidates = self.library.list_assets(
            category=query.category,
            format=query.format_filter,
        )
        if not candidates and query.category:
            # Fallback to all candidates if category filter was overly strict
            candidates = self.library.list_assets(format=query.format_filter)

        tokens = self._tokenize(query.query_text)
        req_dims = query.required_dimensions or {}
        scored_items: List[Dict[str, Any]] = []

        for asset in candidates:
            # 1. Text score (0 - 100)
            text_score, text_reasons = self._score_text(asset, tokens, query.category)

            # 2. Dimensional proximity score (0 - 100)
            dim_score, dim_reasons = self._score_dimensions(asset, req_dims, query.dimensional_tolerance)

            # 3. Geometric aspect ratio score (0 - 100)
            geo_score = self._score_geometry(asset, query.desired_aspect_ratio)

            # 4. Mechanical compatibility & verification report
            target_role = query.desired_role or (
                AssetUsageRole.STANDARD_COMPONENT_REUSE if asset.is_brep_editable() else AssetUsageRole.DESIGN_REFERENCE
            )
            compat_report = CompatibilityVerifier.verify_asset_compatibility(
                asset=asset,
                target_role=target_role,
                design_requirements=req_dims,
            )

            # 5. Weighted combination
            # Text (35%), Dimensions (35%), Compatibility (20%), Geometry (10%)
            compat_weight = 100.0 * compat_report.compatibility_score
            total = (
                0.35 * text_score +
                0.35 * dim_score +
                0.20 * compat_weight +
                0.10 * geo_score
            )

            # Disqualify incompatible assets if standard component reuse was explicitly requested
            if query.desired_role == AssetUsageRole.STANDARD_COMPONENT_REUSE and not compat_report.is_compatible:
                total *= 0.2

            all_reasons = text_reasons + dim_reasons
            if compat_report.is_compatible:
                all_reasons.append("passed_mechanical_compatibility")
            else:
                all_reasons.extend([f"failed_compat: {f}" for f in compat_report.failed_checks[:2]])

            scored_items.append({
                "asset": asset,
                "total_score": round(total, 2),
                "text_score": round(text_score, 2),
                "dimensional_score": round(dim_score, 2),
                "geometric_score": round(geo_score, 2),
                "compatibility": compat_report,
                "match_reasons": all_reasons,
            })

        # Sort descending by total score
        scored_items.sort(key=lambda x: x["total_score"], reverse=True)

        results: List[ScoredAssetResult] = []
        for rank, item in enumerate(scored_items[:query.limit], start=1):
            results.append(ScoredAssetResult(
                asset=item["asset"],
                rank=rank,
                total_score=item["total_score"],
                text_score=item["text_score"],
                dimensional_score=item["dimensional_score"],
                geometric_score=item["geometric_score"],
                compatibility=item["compatibility"],
                match_reasons=item["match_reasons"],
            ))

        return results

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9_\-\.]", " ", text.lower())
        stopwords = {"with", "from", "that", "this", "create", "make", "need", "standard", "a", "an", "the", "for"}
        return [w for w in cleaned.split() if len(w) > 1 and w not in stopwords]

    def _score_text(
        self,
        asset: CADAssetMetadata,
        tokens: List[str],
        category_hint: Optional[str] = None,
    ) -> Tuple[float, List[str]]:
        score = 0.0
        reasons = []

        asset_name = asset.name.lower()
        asset_desc = asset.description.lower()
        asset_cat = asset.category.lower()
        asset_subcat = (asset.subcategory or "").lower()
        asset_tags = [t.lower() for t in asset.tags]

        # Category match
        if category_hint and (category_hint.lower() == asset_cat or category_hint.lower() in asset_subcat):
            score += 30.0
            reasons.append(f"category_match({asset_cat})")

        # Token matches
        matched_tokens = []
        for t in tokens:
            if t in asset_name:
                score += 20.0
                matched_tokens.append(f"name:{t}")
            elif t in asset_tags:
                score += 15.0
                matched_tokens.append(f"tag:{t}")
            elif t in asset_desc:
                score += 10.0
                matched_tokens.append(f"desc:{t}")
            elif t in asset_subcat:
                score += 12.0
                matched_tokens.append(f"subcat:{t}")

        if matched_tokens:
            reasons.append(f"tokens_matched({','.join(matched_tokens[:3])})")

        # Standard compliance bonus
        if any(std in asset_name for std in ["iso", "din", "en", "skf"]):
            score += 10.0

        return min(100.0, score), reasons

    def _score_dimensions(
        self,
        asset: CADAssetMetadata,
        req_dims: Dict[str, float],
        tolerance: float,
    ) -> Tuple[float, List[str]]:
        if not req_dims:
            return 50.0, ["no_dimensional_constraints_specified"]

        nom = asset.nominal_dimensions or {}
        dim_scores = []
        reasons = []

        for req_key, req_val in req_dims.items():
            if req_key not in nom:
                # Check alternative key names (e.g. diameter vs bore_diameter)
                alt_keys = [k for k in nom.keys() if req_key in k or k in req_key]
                if alt_keys:
                    asset_val = nom[alt_keys[0]]
                else:
                    dim_scores.append(20.0)  # Unrecorded dimension penalty
                    continue
            else:
                asset_val = nom[req_key]

            diff = abs(float(req_val) - float(asset_val))
            sigma = max(1.0, float(req_val) * tolerance)
            # Gaussian proximity: 1.0 when diff=0, decaying with distance
            proximity = math.exp(-0.5 * (diff / sigma) ** 2)
            d_score = proximity * 100.0
            dim_scores.append(d_score)

            if diff <= 0.05:
                reasons.append(f"exact_dim_match({req_key}={req_val})")
            elif proximity > 0.5:
                reasons.append(f"close_dim_match({req_key}: req={req_val}, asset={asset_val})")

        if not dim_scores:
            return 50.0, ["dimensions_unmatched"]

        avg_dim_score = sum(dim_scores) / len(dim_scores)
        return min(100.0, avg_dim_score), reasons

    def _score_geometry(
        self,
        asset: CADAssetMetadata,
        desired_ar: Optional[Tuple[float, float]],
    ) -> float:
        if not desired_ar:
            return 70.0

        bb = asset.bounding_box or {}
        l = bb.get("length", 1.0)
        w = bb.get("width", 1.0)
        h = bb.get("height", 1.0)

        ar1 = l / max(0.1, w)
        ar2 = w / max(0.1, h)

        target_ar1, target_ar2 = desired_ar
        diff1 = abs(ar1 - target_ar1)
        diff2 = abs(ar2 - target_ar2)

        prox = math.exp(-0.5 * (diff1**2 + diff2**2))
        return min(100.0, prox * 100.0)
