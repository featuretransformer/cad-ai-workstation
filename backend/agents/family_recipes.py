"""
Mechanical family knowledge base for prompt grounding.

Why this exists
---------------
A language model asked to "build a U-channel" has to invent the feature
decomposition from scratch, and it routinely picks the wrong axis or adds
unrequested chamfers.  Mechanical engineering already knows the canonical
construction for these families: a U-channel is a block minus an open-top
pocket, a hex nut is a regular-polygon prism minus a bore, and so on.

This module maps a prompt to (a) the most likely mechanical family and (b) a
short, authoritative build recipe written in terms of the CADIR operations the
interpreter can execute deterministically.  The recipe is injected into the
design agent's system prompt, so the model spends its capacity on *reading the
numbers correctly* rather than on re-deriving standard topology.

The recipes are general engineering knowledge, not answers to a specific test
case: every dimension still comes from the user's prompt.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

# Each entry:
#   name       canonical family key
#   keywords   regex fragments used for detection
#   recipe     authoritative construction guidance (CADIR operations)
#   single_pass True when one design-agent call is better than decomposition
FAMILIES: List[Dict] = [
    {
        "name": "filleted_hub_flange",
        "keywords": [r"hubbed\s*flange", r"hub.*flange", r"flange.*hub"],
        "recipe": "Single feature feature_type 'filleted_hub_flange' with params {outer_radius, flange_thickness, hub_diameter, height, bore_d, radius}.",
        "single_pass": True,
    },
    {
        "name": "u_channel",
        "keywords": [r"u[\s-]?channel", r"\bchannel\b", r"c[\s-]?channel"],
        "recipe": "Single feature feature_type 'u_channel' with params {width, height, length, wall_thickness}.",
        "single_pass": True,
    },
    {
        "name": "l_bracket",
        "keywords": [r"l[\s-]?bracket", r"angle bracket", r"corner bracket"],
        "recipe": (
            "Single feature feature_type 'l_bracket' with params {leg_x, leg_z, thickness, width}: "
            "leg_x = the horizontal leg along X, leg_z = the vertical leg along Z, thickness = plate "
            "thickness, width = the width along Y. (Do not model it as two boxes; that double-counts "
            "material in the corner.)"
        ),
        "single_pass": True,
    },
    {
        "name": "gusset_bracket",
        "keywords": [r"gusset", r"ribbed bracket"],
        "recipe": "Single feature feature_type 'gusset_bracket' with params {leg_x, leg_z, thickness, width, gusset_leg, gusset_thickness}.",
        "single_pass": True,
    },
    {
        "name": "hex_nut",
        "keywords": [r"hex(?:agonal)?\s*nut", r"\bnut\b.*\bhex", r"lock nut"],
        "recipe": (
            "feature_type regular_polygon with side_count 6 and radius = across_flats / 1.7320508 "
            "(regular_polygon radius is the CIRCUMRADIUS, not the across-flats half-width), "
            "extruded to the nut height. Cut a Hole of the thread/clearance diameter through the axis."
        ),
        "single_pass": True,
    },
    {
        "name": "hex_bolt",
        "keywords": [r"hex(?:agonal)?\s*(?:head\s*)?bolt", r"hex head", r"\bbolt\b"],
        "recipe": (
            "feature_type regular_polygon, side_count 6, radius = across_flats / 1.7320508, height = head "
            "height, with one corner on +X. Join a Cylinder of the shank diameter, length = shank length, "
            "directly above the head (z = head_height .. head_height + shank_length). Threads are omitted."
        ),
        "single_pass": True,
    },
    {
        "name": "socket_cap_screw",
        "keywords": [r"socket\s*(?:head\s*)?cap\s*screw", r"socket head", r"cap screw"],
        "recipe": "Single feature feature_type 'socket_cap_screw' with params {head_diameter, head_height, shank_diameter, shank_length, socket_af, socket_depth}.",
        "single_pass": True,
    },
    {
        "name": "round_flange",
        "keywords": [r"flange", r"bolt circle", r"\bpcd\b"],
        "recipe": (
            "Cylinder(radius = OD/2, height = thickness) plus a Hole of the bore diameter through Z. "
            "Add one Hole feature per bolt hole, positioned at PCD/2 * (cos(theta), sin(theta)) with "
            "theta = 360/n * i, first hole on +X. Do NOT use a polar_pattern feature; emit each hole."
        ),
        "single_pass": True,
    },
    {
        "name": "pillow_block",
        "keywords": [r"pillow\s*block", r"bearing block", r"plummer"],
        "recipe": "Single feature feature_type 'pillow_block' with params {length, width, flange_thickness, upright_width, height, bore_d, bore_z, hole_x, hole_d}.",
        "single_pass": True,
    },
    {
        "name": "counterbore_plate",
        "keywords": [r"counterbore", r"counter-bore", r"cbore", r"socket[- ]head.*hole"],
        "recipe": (
            "Box plate, then one counterbore_hole per hole with diameter = through diameter, "
            "cbore_diameter and cbore_depth, operation cut, positioned on the top face (z = plate thickness). "
            "Emit one feature per hole."
        ),
        "single_pass": True,
    },
    {
        "name": "stepped_shaft",
        "keywords": [r"stepped\s*shaft", r"shoulder", r"step(?:ped)?\s*(?:shaft|diameter)"],
        "recipe": (
            "Join one Cylinder per section, concentric on the Z axis. Each section's height is its axial "
            "length and its base sits at the top of the previous section (z_start = sum of previous lengths). "
            "Do not centre sections at z=0."
        ),
        "single_pass": True,
    },
    {
        "name": "grooved_shaft",
        "keywords": [r"grooved?\s*shaft", r"circlip", r"retaining ring", r"snap ring"],
        "recipe": (
            "Stack the shaft Cylinders along Z, then a groove feature: a ring cut of (outer_radius = shaft "
            "radius, inner_radius = groove radius, groove_width = width) at the given z."
        ),
        "single_pass": False,
    },
    {
        "name": "slotted_plate",
        "keywords": [r"slotted?\s*plate", r"obround", r"slot"],
        "recipe": (
            "Box plate, then cut one SlotOverall per slot: width = overall slot length, height = slot width, "
            "long axis along X, through the thickness. A slot is NOT a round hole."
        ),
        "single_pass": True,
    },
    {
        "name": "plate_4_holes",
        "keywords": [r"four\s*(?:corner\s*)?holes", r"4\s*(?:corner\s*)?holes", r"corner holes"],
        "recipe": (
            "Box plate (L X, W Y, T Z). One Hole feature per corner at "
            "(+/- (L/2 - edge_margin), +/- (W/2 - edge_margin), 0), diameter as specified. "
            "Emit four separate hole features."
        ),
        "single_pass": True,
    },
    {
        "name": "pocket_block",
        "keywords": [r"pocket", r"recess(?:ed)?\s*block", r"cavity"],
        "recipe": (
            "Box block, then cut a Box pocket of (pocket_L, pocket_W, pocket_depth) whose TOP face is flush "
            "with the top of the block: position z = block_height - pocket_depth/2."
        ),
        "single_pass": True,
    },
    {
        "name": "staircase_block",
        "keywords": [r"staircase", r"stepped block", r"\bsteps?\b"],
        "recipe": (
            "Union N boxes of equal footprint width (L/N) with increasing heights (i*H/N), each sitting on "
            "the XY plane and offset along +X, forming ascending steps."
        ),
        "single_pass": True,
    },
    {
        "name": "v_block",
        "keywords": [r"v[\s-]?block", r"v[\s-]?groove"],
        "recipe": "Single feature feature_type 'v_block' with params {width, height, length, groove_depth, groove_angle}.",
        "single_pass": True,
    },
    {
        "name": "t_section_bar",
        "keywords": [r"t[\s-]?section", r"tee section"],
        "recipe": (
            "Join two boxes: flange (L along X, W along Y, t thick at the bottom) plus a web "
            "(t along X, W along Y, H - t tall) centred on X and standing on the flange."
        ),
        "single_pass": True,
    },
    {
        "name": "i_beam",
        "keywords": [r"i[\s-]?beam", r"h[\s-]?beam", r"universal beam"],
        "recipe": "Single feature feature_type 'i_beam' with params {flange_width, height, length, flange_thickness, web_thickness}.",
        "single_pass": True,
    },
    {
        "name": "torus",
        "keywords": [r"\btorus\b", r"donut", r"ring.*circular cross"],
        "recipe": "Single feature feature_type 'torus' with params {major_r, minor_r}.",
        "single_pass": True,
    },
    {
        "name": "helix_spring",
        "keywords": [r"spring", r"helical coil", r"coil spring"],
        "recipe": (
            "Single feature feature_type 'helix_spring' with params {wire_d, mean_d, pitch, turns}. "
            "mean_d is the coil CENTRELINE diameter (outer diameter minus one wire diameter)."
        ),
        "single_pass": True,
    },
    {
        "name": "spur_gear",
        "keywords": [r"spur gear", r"\bgear\b", r"pinion"],
        "recipe": (
            "Single feature feature_type 'spur_gear' with params {module, teeth, pressure_angle, "
            "face_width, bore_d}. The interpreter generates the tooth profile; do NOT approximate the gear "
            "with a plain cylinder or polygon."
        ),
        "single_pass": True,
    },
    {
        "name": "gear_rack",
        "keywords": [r"rack", r"gear rack"],
        "recipe": "Single feature feature_type 'gear_rack' with params {module, teeth, pressure_angle, face_width, wall_thickness, height}.",
        "single_pass": True,
    },
    {
        "name": "pipe_bend",
        "keywords": [r"elbow", r"pipe bend", r"bend\b.*\bpipe"],
        "recipe": (
            "Single feature feature_type 'pipe_bend' with params {od, id, bend_radius, bend_angle, leg1, leg2}. "
            "Do not approximate an elbow with two cylinders."
        ),
        "single_pass": True,
    },
    {
        "name": "star_plate",
        "keywords": [r"star", r"five[\s-]?point"],
        "recipe": "Single feature feature_type 'star_prism' with params {points, outer_r, inner_r, thickness, bore_d}.",
        "single_pass": True,
    },
    {
        "name": "v_pulley",
        "keywords": [r"pulley", r"sheave", r"v[\s-]?belt"],
        "recipe": "Single feature feature_type 'v_pulley' with params {od, face_width, groove_angle, groove_depth, rim_id, hub_diameter, bore_d, web_thickness}.",
        "single_pass": True,
    },
    {
        "name": "domed_cap",
        "keywords": [r"dome", r"hemispher", r"cap\b.*\bhollow"],
        "recipe": "Single feature feature_type 'domed_cap' with params {outer_r, wall_thickness, flange_od, flange_thickness}.",
        "single_pass": True,
    },
    {
        "name": "connecting_rod",
        "keywords": [r"connecting[\s-]?rod", r"conrod", r"link rod"],
        "recipe": "Single feature feature_type 'connecting_rod' with params {outer_r, inner_r, center_dist, face_width, bore_d, small_bore}.",
        "single_pass": True,
    },
    {
        "name": "flanged_bushing",
        "keywords": [r"bushing", r"flanged bush", r"sleeve"],
        "recipe": (
            "Join a flange Cylinder (flange diameter, flange thickness) and a body Cylinder (outside diameter) "
            "above it, then cut a through Hole of the bore diameter."
        ),
        "single_pass": True,
    },
    {
        "name": "plate_center_hole",
        "keywords": [r"plate\b.*\bhole", r"centre hole", r"center hole"],
        "recipe": "Box plate (L, W, T) centred on XY, then a Hole of the specified diameter through Z at (0,0).",
        "single_pass": True,
    },
    {
        "name": "washer",
        "keywords": [r"washer", r"spacer", r"shim"],
        "recipe": "Extrude an annulus: outer Circle minus inner Circle, thickness as specified; equals Cylinder minus Hole.",
        "single_pass": True,
    },
    {
        "name": "tube",
        "keywords": [r"\btube\b", r"pipe", r"hollow cylinder"],
        "recipe": "Cylinder(OD/2, length) minus a through Hole of the ID along the same axis.",
        "single_pass": True,
    },
    {
        "name": "cone_frustum",
        "keywords": [r"cone", r"frustum", r"taper(?:ed)?\b"],
        "recipe": (
            "Single feature feature_type 'cone_frustum' with params {base_d, top_d, height}. "
            "base_d is the bottom diameter, top_d the top diameter; the interpreter revolves the profile."
        ),
        "single_pass": True,
    },
    {
        "name": "sphere",
        "keywords": [r"\bsphere\b", r"ball\b"],
        "recipe": "Sphere feature with the stated radius/diameter.",
        "single_pass": True,
    },
    {
        "name": "cube",
        "keywords": [r"\bcube\b"],
        "recipe": "Single Box of equal length/width/height.",
        "single_pass": True,
    },
    {
        "name": "cylinder",
        "keywords": [r"cylinder", r"\bdisc\b", r"\bdisk\b", r"\brod\b", r"\bpin\b"],
        "recipe": "Single Cylinder (axis along Z unless stated) with radius = diameter/2 and the stated height.",
        "single_pass": True,
    },
    {
        "name": "tapered_shaft",
        "keywords": [r"taper(?:ed)?\s*shaft", r"taper(?:ed)?\s*pin", r"morse taper", r"conical shaft"],
        "recipe": (
            "Use a 'cone_frustum' feature with params {base_d, top_d, height} for the tapered section. "
            "If multiple sections: stack Cylinders along Z, then add a cone_frustum for the taper transition. "
            "Do NOT use a plain cylinder with taper_angle if cone_frustum is supported."
        ),
        "single_pass": True,
    },
    {
        "name": "d_shaft",
        "keywords": [r"d[- ]?(?:flat|profile|shaft|bore)", r"flat[\s-]on[\s-]shaft"],
        "recipe": (
            "Main shaft as a Cylinder (radius, height, operation: new_body). "
            "Then cut a flat: a Box pocket (length = shaft_height+2, width = shaft_diameter, "
            "height = shaft_radius * 0.15) positioned at x = shaft_radius * 0.85, y = 0, z = 0, operation: cut. "
            "The flat runs the full shaft length along Z."
        ),
        "single_pass": True,
    },
    {
        "name": "keyway_shaft",
        "keywords": [r"key(?:way)?", r"keyed\s*shaft", r"woodruff"],
        "recipe": (
            "Main shaft Cylinder (radius, height, new_body). "
            "Then cut a keyway: a Box pocket (length = keyway_length, width = keyway_width, height = keyway_depth + 2) "
            "positioned on the outer surface at (shaft_radius - keyway_depth/2, 0, z_position), operation: cut. "
            "The keyway runs along the shaft axis (Z direction)."
        ),
        "single_pass": False,
    },
    {
        "name": "offset_plate",
        "keywords": [r"offset\s*plate", r"eccentric\s*plate", r"off[- ]?centre"],
        "recipe": (
            "Box plate centred at origin. Any holes NOT at centre are placed at their specified offset coordinates. "
            "Do NOT auto-centre holes — use the explicit offset distances from the prompt as the hole positions."
        ),
        "single_pass": True,
    },
    {
        "name": "ratchet",
        "keywords": [r"ratchet", r"pawl"],
        "recipe": (
            "Cylinder (OD, height) as body. Cut a central bore. "
            "Ratchet teeth: use polar_pattern with a triangular pocket feature (right-angle profile). "
            "Alternatively model as a regular_polygon prism with asymmetric tooth profile in the 'params' dict."
        ),
        "single_pass": False,
    },
    {
        "name": "compound_bracket",
        "keywords": [r"compound\s*bracket", r"multi[- ]?arm\s*bracket", r"spider\s*bracket"],
        "recipe": (
            "Central hub Cylinder, then join arm Boxes extending radially outward (one per arm). "
            "Each arm has a mounting hole at its outer end. "
            "Gusset ribs: thin Box features joining arm base to hub at 45 degrees."
        ),
        "single_pass": False,
    },
    {
        "name": "elliptical_boss",
        "keywords": [r"ellips(?:e|oid|tical)?\s*(?:boss|pad|flange)", r"oval\s*boss"],
        "recipe": (
            "Approximate ellipse as an extrude of a Circle scaled on one axis: "
            "use params {semi_major, semi_minor, height} in an extrude feature. "
            "The interpreter will build the elliptical profile. Operation: join onto the base body."
        ),
        "single_pass": True,
    },
    {
        "name": "sweep_profile",
        "keywords": [r"\bsweep\b", r"swept\s*(?:path|tube|section)", r"along\s*(?:a\s*)?path"],
        "recipe": (
            "Use feature_type 'sweep' with sketch_id pointing to the cross-section sketch "
            "and path_sketch_id pointing to the sweep path sketch. "
            "Define the cross-section sketch (circle or rectangle) and the path sketch (arc or polyline) "
            "as separate CADIRSketchProfile entries."
        ),
        "single_pass": False,
    },
]

GENERAL_RULES = (
    "GENERAL CONSTRUCTION RULES:\n"
    "1. Coordinate frame: X = width/across, Y = length/depth, Z = height/axis. Build the part sitting on "
    "the XY plane (lowest z = 0) and centred in X/Y unless the prompt gives explicit coordinates. The "
    "export stage re-origins the final solid, so absolute placement is not critical, but the AXIS "
    "assignment is.\n"
    "2. AXIS MAPPING - translate the prompt's words into feature parameters, never swap them:\n"
    "   - 'N mm wide' / 'width' / horizontal extent in X  -> X dimension\n"
    "   - 'N mm long' with 'along +Y' / 'length along Y' / 'y = 0 to N' -> Y dimension\n"
    "   - 'N mm long' with 'axis along Z' / 'standing along Z' -> Z height\n"
    "   - 'N mm tall' / 'high' / 'height' -> Z dimension\n"
    "   - explicit ranges 'x = -30 to 30' / 'y = 0 to 50' / 'z = 12 to 52' are authoritative; derive the "
    "extent from them.\n"
    "   - a leading triplet 'A x B x C mm' is normally X x Y x Z; if a later clause adds a feature on top "
    "   ('... on top, a 40 x 40 x 40 upright'), the OVERALL height is the top of that upright, not C.\n"
    "3. Emit one feature per physical instance (one hole feature per hole). Do not use linear_pattern, "
    "polar_pattern, mirror or boolean_* features.\n"
    "4. Do NOT add fillets or chamfers unless the prompt explicitly asks for them; they change volume and "
    "defeat dimensional accuracy.\n"
    "5. Use the high-level parametric feature types (torus, helix_spring, spur_gear, pipe_bend, star_prism) "
    "with their 'params' dict for those families; never approximate them with boxes/cylinders.\n"
    "6. Every feature needs 'id', 'feature_type', 'operation' (new_body/join/cut) and 'dependencies'.\n"
)


def _norm(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt.lower())


def detect_family(prompt: str) -> Optional[Dict]:
    """Returns the best-matching family entry, or None."""
    text = _norm(prompt)
    best = None
    best_score = 0
    for fam in FAMILIES:
        score = 0
        for pat in fam["keywords"]:
            if re.search(pat, text):
                score += 1
        if score > best_score:
            best, best_score = fam, score
    return best


def recipe_block(prompt: str) -> str:
    """Prompt fragment with general rules plus the detected family recipe."""
    fam = detect_family(prompt)
    if not fam:
        return GENERAL_RULES
    return (
        GENERAL_RULES
        + f"\nDETECTED FAMILY: {fam['name']}\n"
        + f"AUTHORITATIVE BUILD RECIPE FOR THIS FAMILY:\n{fam['recipe']}\n"
    )


def is_single_pass_family(prompt: str) -> bool:
    """True when the family is better built in one coherent CADIR pass."""
    fam = detect_family(prompt)
    return bool(fam and fam.get("single_pass"))
