"""
Deterministic placement-frame extraction.

CAD prompts state where the part sits in world space: "base on the XY plane,
centred on the origin in X and Y", "outer corner at the origin", "z = 0 to 40".
Language models frequently ignore that sentence and leave primitives centred on
the origin (build123d's default), which is why a geometrically perfect part can
still be reported as "floating 5 mm below the base plane".

Instead of blanket-normalising every model (which would break the parts that are
genuinely built from a corner), this module reads the frame sentence and returns
the minimal rigid translation the interpreter should apply:

    z_base      -> lowest point of the solid sits on z = 0
    xy_centre   -> bounding box centre sits on x = y = 0

Everything else is left untouched so corner-origin and explicitly-placed parts
keep the coordinates the prompt asked for.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

_Z_BASE_PATTERNS = [
    r"base\s+(?:on|sitting\s+on|at)\s+(?:the\s+)?xy\s*plane",
    r"base\s+bottom\s+on\s+z\s*=\s*0",
    r"bottom\s+(?:of\s+the\s+web|flange)\s+(?:on|at)\s+z\s*=\s*0",
    r"standing\s+along\s+z\s+with\s+its\s+base",
    r"base\s+on\s+(?:the\s+)?xy",
]

_CENTRE_WORD = r"cent(?:re|er)(?:ed|d)"  # accepts "centred" and "centered"

_XY_CENTRE_PATTERNS = [
    rf"{_CENTRE_WORD}\s+on\s+the\s+origin\s+in\s+x\s+and\s+y",
    rf"{_CENTRE_WORD}\s+on\s+the\s+origin",
    r"centre\s+at\s+the\s+origin",
]

_Z_RANGE_RE = re.compile(r"z\s*=\s*(-?\d+(?:\.\d+)?)\s*(?:to|\.\.|–|-)\s*(-?\d+(?:\.\d+)?)")


def _z_ranges_start_at_zero(text: str) -> bool:
    """True when the lowest explicitly stated z start is 0 (e.g. 'z = 0 to 30')."""
    starts = [float(m.group(1)) for m in _Z_RANGE_RE.finditer(text)]
    return bool(starts) and min(starts) == 0.0


def derive_frame(prompt: str) -> Dict[str, object]:
    """
    Returns ``{"z_base": bool, "center_x": bool, "center_y": bool, "evidence": [..]}``.

    The rules are deliberately conservative: when the prompt does not clearly
    establish a frame, the model is left in its natural construction frame.
    """
    text = re.sub(r"\s+", " ", prompt.lower())
    evidence: List[str] = []

    z_base = False
    for pat in _Z_BASE_PATTERNS:
        if re.search(pat, text):
            z_base = True
            evidence.append(f"z_base<-/{pat}/")
            break
    if not z_base and _z_ranges_start_at_zero(text):
        z_base = True
        evidence.append("z_base<-z-range starts at 0")

    center_x = center_y = False
    # "centred on the origin [in X and Y]" centres both axes.  A star/gear whose
    # *feature* is centred at the origin ("star centre at the origin") must keep
    # its natural frame: its bounding box is not symmetric about that centre.
    feature_centre_only = bool(re.search(r"(?:star|gear|pattern)\s+cent(?:re|er)", text))
    if not feature_centre_only:
        for pat in _XY_CENTRE_PATTERNS:
            if re.search(pat, text):
                center_x = center_y = True
                evidence.append(f"center_xy<-/{pat}/")
                break
    # Axis-specific: "web centred on x = 0" centres X only.
    if re.search(rf"{_CENTRE_WORD}\s+on\s+x\s*=\s*0", text):
        center_x = True
        evidence.append("center_x<-'centred on x = 0'")
    if re.search(rf"{_CENTRE_WORD}\s+on\s+y\s*=\s*0", text):
        center_y = True
        evidence.append("center_y<-'centred on y = 0'")

    # Corner framing: "outer corner at the origin", "back face on x = 0",
    # "y = 0 to 80" (a range that starts at the origin means the part grows
    # from that face).
    corner_x = corner_y = False
    if re.search(r"outer\s+corner\s+at\s+the\s+origin", text) or re.search(
        r"corner\s+at\s+the\s+origin", text
    ):
        corner_x = corner_y = True
        # "Corner at the origin" pins the part to the XY plane as well.
        z_base = True
        evidence.append("corner_xy<-'corner at the origin'")
    if re.search(r"back\s+face\s+on\s+x\s*=\s*0", text) or re.search(r"from\s+x\s*=\s*0", text):
        corner_x = True
        evidence.append("corner_x<-'x = 0 face'")
    for axis in ("x", "y"):
        m = re.search(rf"{axis}\s*=\s*(-?\d+(?:\.\d+)?)\s*(?:to|\.\.)\s*(-?\d+(?:\.\d+)?)", text)
        if m and float(m.group(1)) == 0.0:
            if axis == "x":
                corner_x = True
            else:
                corner_y = True
            evidence.append(f"corner_{axis}<-range starts at 0")

    # A corner frame wins over centring on that axis.
    if corner_x:
        center_x = False
    if corner_y:
        center_y = False

    # "centred at the origin" for a full 3-D body (sphere, torus) also means the
    # part is centred vertically; do not force its base onto z = 0.
    if re.search(rf"{_CENTRE_WORD}\s+(?:at|on)\s+the\s+origin", text) and not re.search(
        r"base\s+(?:on|sitting)", text
    ):
        if z_base and not re.search(r"z\s*=\s*0", text):
            z_base = False
            evidence.append("z_base disabled (3-D centred body)")

    return {
        "z_base": bool(z_base),
        "center_x": bool(center_x),
        "center_y": bool(center_y),
        "corner_x": bool(corner_x),
        "corner_y": bool(corner_y),
        "evidence": evidence,
    }


def apply_frame(doc, prompt: str):
    """Writes the derived placement frame onto a CADIRDocument."""
    frame = derive_frame(prompt)
    doc.frame_z_base = bool(frame["z_base"])
    doc.frame_center_x = bool(frame["center_x"])
    doc.frame_center_y = bool(frame["center_y"])
    doc.frame_corner_x = bool(frame["corner_x"])
    doc.frame_corner_y = bool(frame["corner_y"])
    return doc
