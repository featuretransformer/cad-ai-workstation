"""
V2 Golden Benchmark loader.

The V2 "final test" set ships as:
  tests/final test/golden_cad_prompts_v2.jsonl     -> 40 records (one per part)
  tests/final test/renders_v2_all/renders_v2/      -> 512x512 isometric reference renders
  tests/final test/renders_v2_all/renders_v2_annotated/ -> same renders + dimension callouts

Every record carries its own ground-truth geometry contract in ``expected``:
  bbox_mm, volume_mm3, placement_min_xyz_mm, placement_max_xyz_mm, features
so scoring never has to parse the prompt text, and the reference render provides
a scale/translation-invariant shape check.

This module only locates and normalises records; it performs no scoring.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = PROJECT_ROOT / "tests" / "final test"
DATASET_FILE = TESTS_DIR / "golden_cad_prompts_v2.jsonl"
RENDERS_DIR = TESTS_DIR / "renders_v2_all"

LEVELS = ("L0", "L1", "L2", "L3")
LEVEL_NAMES = {
    "L0": "Abstract noun phrase - no dimensions",
    "L1": "Coarse dimensions - partial specification",
    "L2": "Complete parametric engineering specification",
    "L3": "Step-by-step construction instructions (sketch/extrude)",
}
TIER_ORDER = {"easy": 0, "medium": 1, "hard": 2, "complex": 3}


@dataclass(frozen=True)
class Case:
    """One part of the benchmark, independent of prompt level."""

    id: str
    tier: str
    family: str
    params: Dict[str, Any]
    expected: Dict[str, Any]
    prompts: Dict[str, str]
    notes: Optional[str] = None
    iso_image: Optional[Path] = None
    iso_image_annotated: Optional[Path] = None

    @property
    def bbox(self) -> List[float]:
        return [float(v) for v in self.expected["bbox_mm"]]

    @property
    def volume(self) -> float:
        return float(self.expected["volume_mm3"])

    @property
    def placement_min(self) -> List[float]:
        return [float(v) for v in self.expected.get("placement_min_xyz_mm", [0, 0, 0])]

    @property
    def placement_max(self) -> List[float]:
        return [float(v) for v in self.expected.get("placement_max_xyz_mm", self.bbox)]

    @property
    def features(self) -> Dict[str, Any]:
        return dict(self.expected.get("features") or {})

    @property
    def hole_diameters(self) -> List[float]:
        raw = self.features.get("hole_d") or []
        return [float(v) for v in raw]

    @property
    def hole_count(self) -> int:
        return int(self.features.get("holes", len(self.hole_diameters)) or 0)

    def prompt(self, level: str) -> str:
        return self.prompts[level]

    def image(self, annotated: bool = False) -> Optional[Path]:
        p = self.iso_image_annotated if annotated else self.iso_image
        if p and p.exists():
            return p
        return None


def _resolve_image(rel: Optional[str]) -> Optional[Path]:
    if not rel:
        return None
    p = (RENDERS_DIR / rel).resolve()
    return p if p.exists() else None


def load_cases(path: Path | str = DATASET_FILE) -> List[Case]:
    """Loads and validates every record in the V2 benchmark file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"V2 benchmark file not found: {path}")

    cases: List[Case] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            _validate_record(raw, line_no)
            cases.append(
                Case(
                    id=raw["id"],
                    tier=raw["tier"],
                    family=raw["family"],
                    params=dict(raw.get("params") or {}),
                    expected=dict(raw["expected"]),
                    prompts=dict(raw["prompts"]),
                    notes=raw.get("notes"),
                    iso_image=_resolve_image(raw.get("iso_image")),
                    iso_image_annotated=_resolve_image(raw.get("iso_image_annotated")),
                )
            )

    cases.sort(key=lambda c: (TIER_ORDER.get(c.tier, 9), c.id))
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case ids in benchmark file")
    return cases


def _validate_record(raw: Dict[str, Any], line_no: int) -> None:
    required = ("id", "tier", "family", "expected", "prompts")
    missing = [k for k in required if k not in raw]
    if missing:
        raise ValueError(f"Record {line_no} missing keys: {missing}")
    exp = raw["expected"]
    for key in ("bbox_mm", "volume_mm3"):
        if key not in exp:
            raise ValueError(f"Record {raw['id']} missing expected.{key}")
    if len(exp["bbox_mm"]) != 3:
        raise ValueError(f"Record {raw['id']} bbox_mm must have 3 axes")
    for lvl in LEVELS:
        if not raw["prompts"].get(lvl):
            raise ValueError(f"Record {raw['id']} missing prompt level {lvl}")


def select_cases(
    cases: Iterable[Case],
    ids: Optional[List[str]] = None,
    tiers: Optional[List[str]] = None,
    families: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Case]:
    """Applies CLI-style filters while preserving canonical order."""
    out = list(cases)
    if ids:
        wanted = {i.upper() for i in ids}
        out = [c for c in out if c.id.upper() in wanted]
    if tiers:
        wanted_t = {t.lower() for t in tiers}
        out = [c for c in out if c.tier.lower() in wanted_t]
    if families:
        wanted_f = {f.lower() for f in families}
        out = [c for c in out if c.family.lower() in wanted_f]
    if limit:
        out = out[:limit]
    return out


def dataset_fingerprint(cases: List[Case]) -> str:
    """Stable SHA-256 over the scored ground truth (for report provenance)."""
    import hashlib

    blob = json.dumps(
        [
            {
                "id": c.id,
                "tier": c.tier,
                "family": c.family,
                "expected": c.expected,
            }
            for c in cases
        ],
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
