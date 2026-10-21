"""
Mechanical Engineering Standards: Fasteners, Holes, Grooves, and Fits.
Provides standard ISO, DIN, and ASME dimensions for production CAD.
"""
from typing import Dict, Any, Optional
import math


# ==============================================================================
# 1. ISO 4762 / DIN 912: Socket Head Cap Screws (SHCS) Counterbores
# Dimensions in millimeters (mm)
# ==============================================================================
ISO_4762_COUNTERBORES: Dict[str, Dict[str, float]] = {
    "M2":   {"nominal_dia": 2.0,  "clearance_dia": 2.4,  "cbore_dia": 4.4,  "cbore_depth": 2.2, "tap_drill": 1.6,  "pitch": 0.4},
    "M2.5": {"nominal_dia": 2.5,  "clearance_dia": 2.9,  "cbore_dia": 5.0,  "cbore_depth": 2.7, "tap_drill": 2.05, "pitch": 0.45},
    "M3":   {"nominal_dia": 3.0,  "clearance_dia": 3.4,  "cbore_dia": 6.0,  "cbore_depth": 3.4, "tap_drill": 2.5,  "pitch": 0.5},
    "M4":   {"nominal_dia": 4.0,  "clearance_dia": 4.5,  "cbore_dia": 7.5,  "cbore_depth": 4.4, "tap_drill": 3.3,  "pitch": 0.7},
    "M5":   {"nominal_dia": 5.0,  "clearance_dia": 5.5,  "cbore_dia": 9.0,  "cbore_depth": 5.4, "tap_drill": 4.2,  "pitch": 0.8},
    "M6":   {"nominal_dia": 6.0,  "clearance_dia": 6.6,  "cbore_dia": 11.0, "cbore_depth": 6.5, "tap_drill": 5.0,  "pitch": 1.0},
    "M8":   {"nominal_dia": 8.0,  "clearance_dia": 9.0,  "cbore_dia": 14.5, "cbore_depth": 8.6, "tap_drill": 6.8,  "pitch": 1.25},
    "M10":  {"nominal_dia": 10.0, "clearance_dia": 11.0, "cbore_dia": 17.5, "cbore_depth": 10.6, "tap_drill": 8.5, "pitch": 1.5},
    "M12":  {"nominal_dia": 12.0, "clearance_dia": 13.5, "cbore_dia": 19.5, "cbore_depth": 12.6, "tap_drill": 10.2, "pitch": 1.75},
    "M14":  {"nominal_dia": 14.0, "clearance_dia": 15.5, "cbore_dia": 22.0, "cbore_depth": 14.6, "tap_drill": 12.0, "pitch": 2.0},
    "M16":  {"nominal_dia": 16.0, "clearance_dia": 17.5, "cbore_dia": 25.0, "cbore_depth": 16.6, "tap_drill": 14.0, "pitch": 2.0},
    "M20":  {"nominal_dia": 20.0, "clearance_dia": 22.0, "cbore_dia": 30.0, "cbore_depth": 20.6, "tap_drill": 17.5, "pitch": 2.5},
}


# ==============================================================================
# 2. DIN 7991 / ISO 10642: Flat Countersunk Head Cap Screws
# Standard 90-degree angle
# ==============================================================================
ISO_10642_COUNTERSINKS: Dict[str, Dict[str, float]] = {
    "M3":  {"clearance_dia": 3.4,  "csink_dia": 6.72,  "angle": 90.0},
    "M4":  {"clearance_dia": 4.5,  "csink_dia": 8.96,  "angle": 90.0},
    "M5":  {"clearance_dia": 5.5,  "csink_dia": 11.20, "angle": 90.0},
    "M6":  {"clearance_dia": 6.6,  "csink_dia": 13.44, "angle": 90.0},
    "M8":  {"clearance_dia": 9.0,  "csink_dia": 17.92, "angle": 90.0},
    "M10": {"clearance_dia": 11.0, "csink_dia": 22.40, "angle": 90.0},
    "M12": {"clearance_dia": 13.5, "csink_dia": 26.88, "angle": 90.0},
}


# ==============================================================================
# 3. DIN 471: External Retaining Ring (Circlip) Grooves for Shafts
# ==============================================================================
DIN_471_SHAFT_GROOVES: Dict[int, Dict[str, float]] = {
    6:  {"groove_dia": 5.7,  "groove_width": 0.8, "ring_thickness": 0.7},
    8:  {"groove_dia": 7.6,  "groove_width": 0.9, "ring_thickness": 0.8},
    10: {"groove_dia": 9.6,  "groove_width": 1.1, "ring_thickness": 1.0},
    12: {"groove_dia": 11.5, "groove_width": 1.1, "ring_thickness": 1.0},
    15: {"groove_dia": 14.3, "groove_width": 1.1, "ring_thickness": 1.0},
    17: {"groove_dia": 16.2, "groove_width": 1.1, "ring_thickness": 1.0},
    20: {"groove_dia": 19.0, "groove_width": 1.3, "ring_thickness": 1.2},
    25: {"groove_dia": 23.9, "groove_width": 1.3, "ring_thickness": 1.2},
    30: {"groove_dia": 28.6, "groove_width": 1.6, "ring_thickness": 1.5},
    35: {"groove_dia": 33.0, "groove_width": 1.6, "ring_thickness": 1.5},
    40: {"groove_dia": 37.5, "groove_width": 1.85,"ring_thickness": 1.75},
    50: {"groove_dia": 47.0, "groove_width": 2.15,"ring_thickness": 2.0},
}


def lookup_counterbore(screw_callout: str) -> Optional[Dict[str, float]]:
    """
    Given a callout like 'M6', 'm6', 'M8x1.25', or '6mm', returns ISO 4762 counterbore dimensions.
    """
    cleaned = screw_callout.upper().strip()
    if not cleaned.startswith("M") and cleaned.isdigit():
        cleaned = f"M{cleaned}"
    
    # Extract base nominal size e.g. M6 from M6X25
    if "X" in cleaned:
        cleaned = cleaned.split("X")[0]
        
    return ISO_4762_COUNTERBORES.get(cleaned)


def lookup_countersink(screw_callout: str) -> Optional[Dict[str, float]]:
    """Returns ISO 10642 90-degree countersink dimensions."""
    cleaned = screw_callout.upper().strip()
    if not cleaned.startswith("M") and cleaned.isdigit():
        cleaned = f"M{cleaned}"
    if "X" in cleaned:
        cleaned = cleaned.split("X")[0]
    return ISO_10642_COUNTERSINKS.get(cleaned)


def lookup_tap_drill(screw_callout: str) -> Optional[Dict[str, float]]:
    """
    Returns metric tap drill diameter and pitch.
    e.g. M6 -> tap drill 5.0mm (standard coarse pitch 1.0mm).
    """
    info = lookup_counterbore(screw_callout)
    if info:
        return {
            "nominal_dia": info["nominal_dia"],
            "tap_drill_dia": info["tap_drill"],
            "pitch": info["pitch"],
        }
    return None


def lookup_circlip_groove(shaft_diameter: float) -> Dict[str, float]:
    """
    Returns DIN 471 retaining ring groove diameter and width for a nominal shaft diameter.
    Interpolates if exact diameter is not in standard table.
    """
    rounded = int(round(shaft_diameter))
    if rounded in DIN_471_SHAFT_GROOVES:
        return DIN_471_SHAFT_GROOVES[rounded]
    
    # Closest key
    keys = sorted(DIN_471_SHAFT_GROOVES.keys())
    closest_key = min(keys, key=lambda k: abs(k - shaft_diameter))
    base = DIN_471_SHAFT_GROOVES[closest_key]
    
    # Calculate proportional depth
    depth = (closest_key - base["groove_dia"]) / 2.0
    return {
        "groove_dia": max(0.5, shaft_diameter - (2.0 * depth)),
        "groove_width": base["groove_width"],
        "ring_thickness": base["ring_thickness"],
    }
