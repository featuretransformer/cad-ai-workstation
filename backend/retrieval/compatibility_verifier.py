"""
Engineering Compatibility and Unknowns Verifier.
Validates physical, dimensional, interfacial, and licensing compatibility
between retrieved CAD assets and design requirements.
Records unknowns and prohibits unverified assumptions.
"""
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
import math

from retrieval.asset_schema import (
    CADAssetMetadata,
    CADAssetFormat,
    GeometryNature,
    AssetUsageRole,
    VerificationStatus,
)


class CompatibilityReport(BaseModel):
    """Evaluation of mechanical fit, licensing compliance, and recorded engineering unknowns."""
    is_compatible: bool
    compatibility_score: float = Field(ge=0.0, le=1.0)
    recommended_role: AssetUsageRole = AssetUsageRole.STANDARD_COMPONENT_REUSE
    passed_checks: List[str] = Field(default_factory=list)
    failed_checks: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    license_permitted: bool = True
    license_details: Dict[str, Any] = Field(default_factory=dict)
    fit_details: Dict[str, Any] = Field(default_factory=dict)


class CompatibilityVerifier:
    """
    Evaluates physical fit, interface mating, dimensional tolerances,
    licensing restrictions, and engineering unknowns.
    """

    @classmethod
    def verify_asset_compatibility(
        cls,
        asset: CADAssetMetadata,
        target_role: AssetUsageRole,
        design_requirements: Dict[str, Any],
    ) -> CompatibilityReport:
        """
        Verifies whether an asset can be used in the design based on:
        1. Role & geometry nature (B-Rep solid vs mesh)
        2. License and copyright restrictions
        3. Unit normalization and dimensional constraints
        4. Interfacial mating fits (bores, PCDs, threads, center distances)
        5. Records explicit engineering unknowns
        """
        passed: List[str] = []
        failed: List[str] = []
        unknowns: List[str] = []
        fit_details: Dict[str, Any] = {}

        # ── 1. License & Legal Restrictions Check ─────────────────────
        lic = asset.provenance
        license_permitted = True
        license_details = {
            "license": lic.license,
            "commercial_allowed": lic.commercial_reuse_allowed,
            "attribution_required": lic.attribution_required,
            "terms_restricted": lic.terms_restricted,
            "source_url": lic.source_url,
        }

        if lic.terms_restricted:
            failed.append(f"Licensing terms restricted by vendor/terms: {lic.source_url}")
            license_permitted = False
        else:
            passed.append(f"License permitted for workstation reuse ({lic.license})")

        # ── 2. Format & Geometric Nature for Role ─────────────────────
        if target_role == AssetUsageRole.STANDARD_COMPONENT_REUSE:
            if asset.format in [CADAssetFormat.STL]:
                failed.append("STL mesh cannot be used for standard component solid reuse; must be STEP B-Rep.")
            elif asset.geometry_nature != GeometryNature.BREP_SOLID:
                failed.append(f"Non-solid geometry nature ({asset.geometry_nature}) cannot be reused as standard solid.")
            elif asset.verification_status != VerificationStatus.VERIFIED_BREP:
                failed.append(f"Asset geometry not verified as valid B-Rep solid ({asset.verification_status}).")
            else:
                passed.append("Verified B-Rep solid geometry confirmed for standard component reuse.")
        elif target_role == AssetUsageRole.DESIGN_REFERENCE:
            passed.append(f"Asset geometry format '{asset.format.value}' accepted as design reference envelope.")

        # ── 3. Unit Verification & Normalization ──────────────────────
        req_units = str(design_requirements.get("units", "mm")).lower()
        asset_units = str(asset.units).lower()
        if asset_units != req_units:
            failed.append(f"Unit mismatch: Asset uses '{asset_units}' while design requires '{req_units}'.")
        else:
            passed.append(f"Units matched ({asset_units}).")

        # ── 4. Dimensional Fit Checks ─────────────────────────────────
        nom = asset.nominal_dimensions or {}

        # 4a. Bore / Shaft Fit Check
        req_shaft_dia = design_requirements.get("shaft_diameter") or design_requirements.get("bore_diameter")
        asset_bore = nom.get("bore_diameter")
        if req_shaft_dia is not None and asset_bore is not None:
            diff = abs(float(req_shaft_dia) - float(asset_bore))
            fit_details["shaft_to_bore_diff_mm"] = round(diff, 4)
            if diff <= 0.05:
                passed.append(f"Shaft-bore coaxial fit exact (shaft={req_shaft_dia}mm, bore={asset_bore}mm)")
            elif diff <= 0.25:
                passed.append(f"Shaft-bore transition fit within tolerance (diff={diff}mm)")
            else:
                failed.append(f"Shaft-bore dimensional mismatch: required shaft {req_shaft_dia}mm != asset bore {asset_bore}mm (diff={diff}mm)")
        elif req_shaft_dia is not None and asset_bore is None:
            unknowns.append("Shaft diameter specified in requirements but asset bore diameter is unrecorded.")

        # 4b. Bolt Circle / PCD Fit Check
        req_pcd = design_requirements.get("pcd") or design_requirements.get("bolt_circle_diameter")
        asset_pcd = nom.get("pcd") or nom.get("bolt_circle_diameter")
        if req_pcd is not None and asset_pcd is not None:
            diff = abs(float(req_pcd) - float(asset_pcd))
            fit_details["pcd_diff_mm"] = round(diff, 4)
            if diff <= 0.5:
                passed.append(f"Flange bolt circle PCD matched (req={req_pcd}mm, asset={asset_pcd}mm)")
            else:
                failed.append(f"Flange PCD mismatch: required {req_pcd}mm != asset {asset_pcd}mm")

        # 4c. Fastener Thread Size Check
        req_thread = design_requirements.get("thread_size")
        asset_thread = nom.get("thread_size")
        if req_thread is not None and asset_thread is not None:
            if float(req_thread) == float(asset_thread):
                passed.append(f"Thread nominal size matched (M{req_thread})")
            else:
                failed.append(f"Thread size mismatch: required M{req_thread} != asset M{asset_thread}")

        # 4d. Gear Module & Meshing Verification
        req_module = design_requirements.get("module")
        asset_module = nom.get("module")
        if req_module is not None and asset_module is not None:
            if float(req_module) == float(asset_module):
                passed.append(f"Gear module matched (m={req_module}mm)")
            else:
                failed.append(f"Gear module mismatch: required m={req_module} != asset m={asset_module}")

        # ── 5. Record Explicit Unknowns (No Unsubstantiated Assumptions)
        if not asset.material or asset.material == "Unknown":
            unknowns.append("Material grade and tensile yield strength not certified.")
        if asset.mass_kg is None:
            unknowns.append("Physical component mass is unmeasured; density estimate used.")
        if "tolerance_class" not in nom:
            unknowns.append("Manufacturing tolerance class (e.g. ISO 2768-m or ISO 286 IT grade) uncertified.")
        if not asset.mating_interfaces:
            unknowns.append("Explicit kinematic mating datum interfaces not predefined.")

        # ── 6. Final Compatibility Determination ──────────────────────
        is_compatible = (len(failed) == 0) and license_permitted

        # Score computation: passed / total checks
        total_evals = len(passed) + len(failed)
        base_score = len(passed) / max(1, total_evals) if is_compatible else 0.0

        # Penalty for excessive unknowns
        unknown_penalty = min(0.15, len(unknowns) * 0.03)
        final_score = max(0.0, round(base_score - unknown_penalty, 3))

        # Recommended Role
        if not is_compatible:
            rec_role = AssetUsageRole.CUSTOM_GEOMETRY_GENERATION
        elif asset.is_mesh_only():
            rec_role = AssetUsageRole.DESIGN_REFERENCE
        else:
            rec_role = target_role

        return CompatibilityReport(
            is_compatible=is_compatible,
            compatibility_score=final_score,
            recommended_role=rec_role,
            passed_checks=passed,
            failed_checks=failed,
            unknowns=unknowns,
            license_permitted=license_permitted,
            license_details=license_details,
            fit_details=fit_details,
        )

    @classmethod
    def verify_gear_pair_meshing(
        cls,
        gear1: CADAssetMetadata,
        gear2: CADAssetMetadata,
        center_distance_mm: Optional[float] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validates meshing between two gear assets:
        1. Both must share the same module: m1 == m2
        2. Pitch diameters d1 = m*z1, d2 = m*z2
        3. Operating center distance must satisfy a = (d1 + d2) / 2 = m*(z1 + z2)/2
        """
        nom1 = gear1.nominal_dimensions
        nom2 = gear2.nominal_dimensions

        m1 = nom1.get("module")
        m2 = nom2.get("module")
        z1 = nom1.get("teeth")
        z2 = nom2.get("teeth")

        if m1 is None or m2 is None or z1 is None or z2 is None:
            return False, {"error": "Missing gear module or teeth count in assets"}

        if float(m1) != float(m2):
            return False, {"error": f"Gear module mismatch: {m1} != {m2}"}

        calc_center_dist = float(m1) * (float(z1) + float(z2)) / 2.0
        details = {
            "module": float(m1),
            "teeth_1": int(z1),
            "teeth_2": int(z2),
            "pitch_dia_1": float(m1) * float(z1),
            "pitch_dia_2": float(m2) * float(z2),
            "theoretical_center_distance_mm": calc_center_dist,
        }

        if center_distance_mm is not None:
            diff = abs(float(center_distance_mm) - calc_center_dist)
            details["center_distance_error_mm"] = round(diff, 4)
            if diff > 0.1:
                return False, {
                    **details,
                    "error": f"Specified center distance {center_distance_mm}mm deviates from theoretical {calc_center_dist}mm",
                }

        return True, details
