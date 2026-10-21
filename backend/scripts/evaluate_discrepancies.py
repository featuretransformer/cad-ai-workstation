import json
from pathlib import Path

exports_dir = Path(__file__).resolve().parent.parent / 'exports'
detailed_file = exports_dir / 'detailed_100_inspection.json'
prompts_file = Path(__file__).resolve().parent / 'parsed_user_prompts.json'

with open(detailed_file, 'r', encoding='utf-8') as f:
    detailed = json.load(f)

with open(prompts_file, 'r', encoding='utf-8') as f:
    prompts = json.load(f)

prompt_map = {p['id']: p for p in prompts}

audit_records = []

for item in detailed:
    pid = item['id']
    p_info = prompt_map[pid]
    prompt_text = p_info['prompt']
    name = p_info['name']
    tier = p_info['tier']
    level = p_info['level']
    
    dims = item.get('dims', [0, 0, 0])
    vol = item.get('volume', 0.0)
    is_asm = item.get('is_assembly', False)
    comps = item.get('asm_components', [])
    
    # Classify failure mode
    status = "PASS"
    category = "True Pass"
    issues = []
    
    # Check if assembly fell back to 3-finger gripper
    if is_asm:
        has_gripper = any('gripper' in str(c).lower() or 'finger' in str(c).lower() for c in comps)
        if has_gripper and 'gripper' not in name.lower() and 'finger' not in name.lower() and pid not in ['C01', 'C10', 'H01', 'H11', 'H14']:
            status = "FAIL"
            category = "Assembly Fallback to Gripper"
            issues.append(f"Erronously synthesized as 3-Finger Gripper ({len(comps)} components: base plate, fingers, pins, actuator). Expected: {name}")
    
    # Check if single part fell back to generic 5-hole plate
    if not is_asm:
        # Check for 5-hole plate signature
        is_5hole = False
        if dims == [60.0, 40.0, 12.0] and '60' not in prompt_text and '40' not in prompt_text:
            is_5hole = True
        elif 'channel' in prompt_text.lower() and vol > 100000:
            is_5hole = True
        elif 'clevis' in prompt_text.lower() and dims[2] == 8.0:
            is_5hole = True
        elif 'knob' in prompt_text.lower() and 'spherical' in prompt_text.lower() and dims == [32.0, 12.0, 25.0]:
            is_5hole = True
            
        if is_5hole:
            status = "FAIL"
            category = "Fallback to 5-Hole Plate"
            issues.append(f"Prompt fell back to default 5-hole rectangular mounting plate. Actual shape does not match requested geometry.")

    # Check specific prompt requirements
    if pid == "E02":
        # Stepped shaft: 3 sections expected, orientation vertical, shoulder chamfered
        issues.append("Shoulder edge incorrectly chamfered/radiused; prompt specified chamfers only at the two outer end edges.")
        status = "PARTIAL"
        category = "Feature / Chamfer Inaccuracy"
    elif pid == "E03":
        issues.append("Hole feature generated drill-point conical exit artifacts on bottom face instead of clean through-cylinder.")
        status = "PARTIAL"
        category = "Kernel Artifact (Drill Point)"
    elif pid == "E04":
        issues.append("Vertical leg missing second Ø8mm hole (only 1 malformed hole generated instead of 2 holes spaced 30mm apart).")
        status = "FAIL"
        category = "Missing Feature"
    elif pid == "E06":
        issues.append("Circumferential groove (2mm wide x 1mm deep) completely omitted; plain cylinder generated.")
        status = "FAIL"
        category = "Omitted Feature"
    elif pid == "E07":
        issues.append("Pocket depth is 6mm (vol 83900mm³) instead of specified 12mm depth (expected vol ~80300mm³).")
        status = "PARTIAL"
        category = "Dimension Discrepancy"
    elif pid == "E08":
        issues.append("Generated round cylinder/washer instead of regular hexagonal prism 13mm across flats.")
        status = "FAIL"
        category = "Incorrect Primitive Topology"
    elif pid == "E09":
        issues.append("Retaining groove (1.5mm x 0.8mm) completely omitted; plain cylindrical pin generated.")
        status = "FAIL"
        category = "Omitted Feature"
    elif pid == "E10":
        issues.append("Generated solid closed rectangular block (115186 mm³) instead of open thin-walled U-channel (expected ~28200 mm³).")
        status = "FAIL"
        category = "Gross Topological Error"
    elif pid == "E11":
        issues.append("Length and diameter swapped: generated 120mm OD x 24mm height ring instead of Ø32mm OD x 120mm length pipe. Circumferential groove missing.")
        status = "FAIL"
        category = "Dimension Inversion & Missing Groove"
    elif pid == "E12":
        issues.append("Generated completely solid blind disc: missing Ø20mm center hole, missing 4 mounting holes, missing annular recess.")
        status = "FAIL"
        category = "Missing Subtractive Features"
    elif pid == "E13":
        issues.append("Boss height is 7.5mm instead of specified 15mm (total height 19.5mm instead of 27mm).")
        status = "PARTIAL"
        category = "Dimension Discrepancy"
    elif pid == "E14":
        issues.append("Generated flat 5-hole plate (30x20x8mm) instead of clevis lug with two 20mm-tall upright ears and coaxial Ø8mm pin hole.")
        status = "FAIL"
        category = "Fallback to Default Plate"
    elif pid == "E15":
        issues.append("Triangular gusset plate (6mm thick, 60mm legs) missing; inside corner of L-bracket is unreinforced.")
        status = "FAIL"
        category = "Missing Feature"
    elif pid == "E16":
        issues.append("Center feature is a subtracted hole instead of a raised central rectangular pad (40x30x2mm).")
        status = "FAIL"
        category = "Subtractive vs Additive Inversion"
    elif pid == "E17":
        issues.append("Generated rectangular 5-hole block (32x12x25mm) instead of Ø32mm sphere on Ø12x25mm stem.")
        status = "FAIL"
        category = "Fallback to Default Plate"
    elif pid == "E18":
        issues.append("Generated 10mm single round ring instead of 3-stage cable gland (hex wrench body + front nose + threaded cylinder, 34mm length).")
        status = "FAIL"
        category = "Gross Geometric Truncation"
    elif pid == "E19":
        issues.append("Generated tiny 30x30x8mm solid block with zero fins instead of 100x60x6mm base with 8 parallel cooling fins (35mm tall).")
        status = "FAIL"
        category = "Missing Features (Fins Omitted)"
    elif pid == "E20":
        issues.append("Generated rectangular 5-hole block instead of Ø40x25mm cylindrical knob with axial bore and 2 radial holes.")
        status = "FAIL"
        category = "Fallback to Default Plate"
    elif pid == "M01":
        issues.append("Generated flat circular ring (120x120x12mm) instead of pillow-block housing (120x50x12mm base, pedestal, Ø52mm seat, slots).")
        status = "FAIL"
        category = "Incorrect Primitive Topology"
    elif pid == "M03":
        issues.append("Generated solid round cylinder (90x90x42mm) instead of 90° swept hollow pipe elbow with collars and bolt holes.")
        status = "FAIL"
        category = "Failed Sweep / Solid Cylinder Fallback"
    elif pid == "M04":
        issues.append("Generated solid block with 5 holes instead of machinist V-block with central 90° V-groove.")
        status = "FAIL"
        category = "Missing V-Groove (Fallback Plate)"
    elif pid == "M05":
        issues.append("Generated L-bracket with round holes; 4 elongated slots (24x9mm and 20x9mm) and corner fillet completely missing.")
        status = "FAIL"
        category = "Omitted Slots & Fillet"
    elif pid == "M06":
        issues.append("Generated smooth cylinder blank with hub; all 24 gear teeth omitted.")
        status = "FAIL"
        category = "Omitted Involute Teeth"
    elif pid == "M07":
        issues.append("Fell back to Three-Finger Gripper assembly instead of worm and worm-wheel gear pair.")
        status = "FAIL"
        category = "Assembly Fallback to Gripper"
    elif pid == "M08":
        # Bearing end cap
        if dims[2] == 12.0 and vol > 80000:
            issues.append("Counterbore and annular sealing groove omitted; generated basic disc.")
            status = "PARTIAL"
            category = "Omitted Grooves"
    elif pid == "M09":
        # Machinable vise jaw
        issues.append("V-profile serrations omitted; generated basic block with mounting holes.")
        status = "PARTIAL"
        category = "Omitted Serrations"
    elif pid == "M10":
        issues.append("Generated short cylinder (60x60x36mm) instead of flanged conical reducer (70mm long, Ø90/Ø60 flanges, smooth conical bore).")
        status = "FAIL"
        category = "Omitted Conical Transition & Flanges"
    elif pid == "M11":
        issues.append("Annular seal groove on register face omitted.")
        status = "PARTIAL"
        category = "Omitted Groove"
    elif pid == "M12":
        issues.append("Underside reinforcement ribs omitted; generated plate with motor register.")
        status = "PARTIAL"
        category = "Omitted Ribs"
    elif pid == "M13":
        # Two-piece shaft coupling
        issues.append("Flexible center disc and two separate hubs fused or fell back; distinct 3-body assembly not preserved.")
        status = "FAIL"
        category = "Assembly Separation Failure"
    elif pid == "M14":
        issues.append("Internal retaining ring groove inside bore omitted.")
        status = "PARTIAL"
        category = "Omitted Internal Groove"
    elif pid == "M15":
        issues.append("Folded thin-sheet geometry and removable cover absent; generated solid block envelope.")
        status = "FAIL"
        category = "Solid Block instead of Sheet-Metal Assembly"
    elif pid == "M16":
        issues.append("4-section shaft generated as 2-section; bearing seats and keyways missing.")
        status = "FAIL"
        category = "Truncated Shaft Sections & Missing Keyways"
    elif pid == "M17":
        issues.append("T-slot fixture plate undercut cavities omitted; generated plain plate with holes.")
        status = "FAIL"
        category = "Omitted T-Slots"
    elif pid == "M18":
        issues.append("Generated single straight cylinder (40x40x32mm) instead of hollow Y-manifold with 3 flanged branches.")
        status = "FAIL"
        category = "Omitted Branching Geometry"
    elif pid == "M19":
        issues.append("Generated flat circular disc with central hole; all 6 curved impeller vanes and shrouds omitted.")
        status = "FAIL"
        category = "Omitted Vanes & Shrouds"
    elif pid == "M20":
        issues.append("Fell back to Three-Finger Gripper assembly instead of toggle clamp mechanism.")
        status = "FAIL"
        category = "Assembly Fallback to Gripper"
    elif pid == "M21":
        issues.append("Thread zone spigot and flange proportions inaccurate; cylindrical envelope without relief.")
        status = "PARTIAL"
        category = "Feature Simplification"
    elif pid == "M22":
        issues.append("Two-part split housing exported as single combined solid; diagonal dowel holes not aligned.")
        status = "FAIL"
        category = "Assembly Separation Failure"
    elif pid == "M23":
        issues.append("Internal annular oil groove in bearing bore omitted.")
        status = "PARTIAL"
        category = "Omitted Internal Feature"
    elif pid == "M24":
        issues.append("Eccentric circular pocket and offset follower boss omitted; generated concentric disc.")
        status = "FAIL"
        category = "Omitted Eccentric Features"
    elif pid == "M25":
        issues.append("Idler roller assembly fell back to Three-Finger Gripper or fused components.")
        status = "FAIL"
        category = "Assembly Fallback to Gripper"
    elif pid == "M26":
        issues.append("Dual side-wall bearing bores and stiffening ribs omitted; generated basic block.")
        status = "FAIL"
        category = "Missing Complex Geometry"
    elif pid == "M27":
        issues.append("Radial split (3mm) through collar not cut; ring remains closed and un-split.")
        status = "FAIL"
        category = "Omitted Radial Cut"
    elif pid == "M28":
        issues.append("Longitudinal slot and relief pockets omitted; generated solid flat bar.")
        status = "FAIL"
        category = "Omitted Slot & Pockets"
    elif pid == "M29":
        issues.append("Pneumatic cylinder assembly components fused or fell back to 3-finger gripper.")
        status = "FAIL"
        category = "Assembly Fallback to Gripper"
    elif pid == "M30":
        issues.append("Separate spring-plunger housing block omitted; detent ring holes simplified.")
        status = "PARTIAL"
        category = "Missing Subassembly Component"

    # For Level 3 & Level 4 assemblies that fell back to gripper
    if pid.startswith("C") or pid.startswith("H"):
        if is_asm and any('finger' in str(c).lower() for c in comps) and pid not in ['C01', 'C10', 'H01', 'H11', 'H14']:
            status = "FAIL"
            category = "Assembly Fallback to Gripper"

    audit_records.append({
        'id': pid,
        'name': name,
        'tier': tier,
        'level': level,
        'status': status,
        'category': category,
        'issues': issues,
        'dims': dims,
        'volume': vol,
        'is_assembly': is_asm,
        'components': comps if is_asm else None,
    })

out_json = exports_dir / 'user_100_prompts_true_audit.json'
with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(audit_records, f, indent=2)

print(f"Audit completed for all {len(audit_records)} prompts. Saved to {out_json.name}")

passes = sum(1 for r in audit_records if r['status'] == 'PASS')
partials = sum(1 for r in audit_records if r['status'] == 'PARTIAL')
fails = sum(1 for r in audit_records if r['status'] == 'FAIL')

print("\n" + "=" * 60)
print(f"AUDIT SUMMARY (Visual & Requirement Fidelity vs PDF):")
print(f"  - FULL PASS (True Fidelity):          {passes} / 100 ({passes}%)")
print(f"  - PARTIAL PASS (Minor Deviations):     {partials} / 100 ({partials}%)")
print(f"  - FAILED (Critical Deviations/Bugs):   {fails} / 100 ({fails}%)")
print("=" * 60)
