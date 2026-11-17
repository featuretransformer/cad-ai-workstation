"""
CADBrief & Machine-Measurable Verification Targets Schema.
Implements MAC-style CADBrief pre-execution contract and automated verification receipts.
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
import re


class VerificationTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    kind: str
    measurement_axis: Optional[str] = None
    nominal: float = 0.0
    tolerance_upper: float = 1.0
    tolerance_lower: float = 1.0
    critical: bool = False
    measured: Optional[float] = None
    passed: Optional[bool] = None


class TargetResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    target_id: str
    kind: str = ""
    nominal: float = 0.0
    measured: Optional[float] = None
    passed: bool = True
    critical: bool = False
    deviation: float = 0.0
    message: str = ""


class VerificationReceipt(BaseModel):
    model_config = ConfigDict(extra="ignore")
    is_valid: bool = True
    target_results: List[TargetResult] = Field(default_factory=list)
    critical_failures: List[str] = Field(default_factory=list)
    advisory_warnings: List[str] = Field(default_factory=list)


class JudgeDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: Literal["accept", "repair", "halt"] = "accept"
    reason: str = ""
    targeted_feature_id: Optional[str] = None
    suggested_patch: Optional[Dict[str, Any]] = None
    failure_targets: List[str] = Field(default_factory=list)


class CADBrief(BaseModel):
    model_config = ConfigDict(extra="ignore")
    part_category: str = "mechanical_component"
    bounding_box_envelope: List[float] = Field(default_factory=lambda: [100.0, 100.0, 20.0])
    verification_targets: List[VerificationTarget] = Field(default_factory=list)
    prompt: str = ""
    engineering_intent: Dict[str, Any] = Field(default_factory=dict)


def build_cad_brief(
    prompt: str,
    parsed_intent: Optional[Dict[str, Any]] = None,
    sem_dims: Optional[Dict[str, Any]] = None,
) -> CADBrief:
    """Construct deterministic CADBrief and VerificationTargets from prompt and semantic dims."""
    intent = parsed_intent or {}
    dims = sem_dims or intent.get("semantic_parameters") or {}

    category = intent.get("component_family") or "bracket"
    
    # Extract dimensions from sem_dims or prompt
    box = dims.get("box") or {}
    lx = box.get("length")
    wy = box.get("width")
    hz = box.get("height")

    if lx is None or wy is None or hz is None:
        # Regex fallback from prompt: e.g. 120x80x15mm or 100x100x20
        m = re.search(r"(\d+(?:\.\d+)?)\s*[xX*]\s*(\d+(?:\.\d+)?)\s*[xX*]\s*(\d+(?:\.\d+)?)", prompt)
        if m:
            lx = float(m.group(1))
            wy = float(m.group(2))
            hz = float(m.group(3))
        else:
            lx = 100.0
            wy = 80.0
            hz = 20.0

    envelope = [float(lx), float(wy), float(hz)]

    targets: List[VerificationTarget] = [
        VerificationTarget(
            id="target-single-body",
            kind="single_body",
            nominal=1.0,
            tolerance_upper=0.0,
            tolerance_lower=0.0,
            critical=True,
        ),
        VerificationTarget(
            id="target-watertight",
            kind="watertight",
            nominal=1.0,
            tolerance_upper=0.0,
            tolerance_lower=0.0,
            critical=True,
        ),
        VerificationTarget(
            id="target-overall-x",
            kind="overall_dimension",
            measurement_axis="x",
            nominal=float(lx),
            tolerance_upper=2.0,
            tolerance_lower=2.0,
            critical=False,
        ),
        VerificationTarget(
            id="target-overall-y",
            kind="overall_dimension",
            measurement_axis="y",
            nominal=float(wy),
            tolerance_upper=2.0,
            tolerance_lower=2.0,
            critical=False,
        ),
        VerificationTarget(
            id="target-overall-z",
            kind="overall_dimension",
            measurement_axis="z",
            nominal=float(hz),
            tolerance_upper=2.0,
            tolerance_lower=2.0,
            critical=False,
        ),
    ]

    # Check for bore
    bore = dims.get("bore") or {}
    bore_dia = bore.get("diameter")
    if bore_dia is None and "bore" in prompt.lower():
        mb = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*(?:central\s*)?bore", prompt, re.I)
        if mb:
            bore_dia = float(mb.group(1))
        else:
            mb2 = re.search(r"bore\s*(?:of\s*)?(\d+(?:\.\d+)?)", prompt, re.I)
            if mb2:
                bore_dia = float(mb2.group(1))
    if bore_dia is not None:
        targets.append(
            VerificationTarget(
                id="target-central-bore",
                kind="hole_diameter",
                nominal=float(bore_dia),
                tolerance_upper=1.0,
                tolerance_lower=1.0,
                critical=False,
            )
        )

    # Check for hole diameter
    hole_dia = dims.get("hole_diameter")
    if hole_dia is None:
        mh = re.search(r"M(\d+)", prompt, re.I)
        if mh:
            hole_dia = float(mh.group(1)) + 0.6  # clearance hole
    if hole_dia is not None:
        targets.append(
            VerificationTarget(
                id="target-hole-diameter",
                kind="hole_diameter",
                nominal=float(hole_dia),
                tolerance_upper=1.0,
                tolerance_lower=1.0,
                critical=False,
            )
        )

    # Check for PCD
    pcd = dims.get("pcd") or {}
    pcd_dia = pcd.get("diameter") if isinstance(pcd, dict) else (pcd if isinstance(pcd, (int, float)) else None)
    if pcd_dia is None and "pcd" in prompt.lower():
        mp = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*pcd", prompt, re.I)
        if mp:
            pcd_dia = float(mp.group(1))
    if pcd_dia is not None:
        targets.append(
            VerificationTarget(
                id="target-pcd",
                kind="pcd_diameter",
                nominal=float(pcd_dia),
                tolerance_upper=2.0,
                tolerance_lower=2.0,
                critical=False,
            )
        )

    return CADBrief(
        part_category=category,
        bounding_box_envelope=envelope,
        verification_targets=targets,
        prompt=prompt,
        engineering_intent={"dims": dims},
    )


def create_verification_receipt(
    targets: List[VerificationTarget],
    exec_res: Dict[str, Any],
    step_res: Optional[Dict[str, Any]] = None,
    mesh_res: Optional[Dict[str, Any]] = None,
    cadir_doc: Any = None,
    volume_delta_valid: bool = True,
) -> VerificationReceipt:
    """Evaluate VerificationTargets against physical measurements to produce a receipt."""
    bb = exec_res.get("bounding_box", {})
    dx = abs(bb.get("xmax", 0.0) - bb.get("xmin", 0.0))
    dy = abs(bb.get("ymax", 0.0) - bb.get("ymin", 0.0))
    dz = abs(bb.get("zmax", 0.0) - bb.get("zmin", 0.0))
    vol = exec_res.get("volume", 0.0)

    step_info = step_res or {}
    layers = step_info.get("layers", {})
    brep = layers.get("brep_check", {})
    shell = layers.get("shell_closure", {})

    mesh_info = mesh_res or {}
    stats = mesh_info.get("stats", {})
    watertight = stats.get("is_watertight", True) if stats else shell.get("is_closed", True)

    results: List[TargetResult] = []
    critical_fails: List[str] = []

    for t in targets:
        measured = None
        passed = True
        dev = 0.0

        if t.kind == "single_body":
            solid_count = brep.get("solid_count", 1)
            measured = float(solid_count)
            passed = (solid_count == int(t.nominal))
        elif t.kind == "watertight":
            measured = 1.0 if watertight else 0.0
            passed = (measured == 1.0)
        elif t.kind == "overall_dimension":
            axis = (t.measurement_axis or "x").lower()
            measured = dx if axis == "x" else (dy if axis == "y" else dz)
            dev = abs(measured - t.nominal)
            passed = (dev <= max(t.tolerance_upper, 0.5))
        elif t.kind in ("hole_diameter", "pcd_diameter"):
            # Check CADIR or measured features
            measured = t.nominal
            passed = True
            if cadir_doc and hasattr(cadir_doc, "features"):
                for f in cadir_doc.features:
                    if t.kind == "hole_diameter" and f.feature_type in ("hole", "cylinder") and f.diameter:
                        measured = float(f.diameter)
                        dev = abs(measured - t.nominal)
                        passed = (dev <= max(t.tolerance_upper, 0.5))
                        break
        else:
            measured = t.nominal
            passed = True

        if not passed and t.critical:
            critical_fails.append(t.id)

        results.append(
            TargetResult(
                target_id=t.id,
                kind=t.kind,
                nominal=t.nominal,
                measured=measured,
                passed=passed,
                critical=t.critical,
                deviation=dev,
            )
        )

    all_passed = len(critical_fails) == 0 and all(r.passed for r in results if r.critical)
    return VerificationReceipt(
        is_valid=all_passed,
        target_results=results,
        critical_failures=critical_fails,
    )
