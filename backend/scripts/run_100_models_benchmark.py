"""
100-Model Mechanical Design Evaluation & Benchmark Suite.
Tests 100 diverse mechanical models across 3 complexity tiers:
- 20 Easy: standard hardware, washers, pins, bolts, nuts, spacers, bushings, shafts.
- 30 Medium: stepped shafts, flanges with bolt patterns, brackets with stiffeners, pulleys, gears, enclosures.
- 50 Complex: multi-component mechanical assemblies (grippers, gearboxes, caster wheels, slides, couplings, valves, impellers).
"""
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.graph import cad_graph
from agents.state import AgentState

EVAL_CATALOG: List[Dict[str, Any]] = [
    # ══════════════════════════════════════════════════════════════════════════
    # TIER 1: 20 EASY MODELS (Basic Machine Elements & Standard Hardware)
    # ══════════════════════════════════════════════════════════════════════════
    {"id": "EASY-01", "category": "Easy", "name": "M10 Flat Washer", "prompt": "M10 flat washer outer diameter 20mm inner diameter 10.5mm thickness 2mm"},
    {"id": "EASY-02", "category": "Easy", "name": "Heavy Duty Washer", "prompt": "Heavy duty washer 30mm OD 15mm ID 3mm thickness"},
    {"id": "EASY-03", "category": "Easy", "name": "Flat Steel Spacer", "prompt": "Flat steel spacer 25mm diameter 10mm bore 5mm thick"},
    {"id": "EASY-04", "category": "Easy", "name": "Bronze Bushing", "prompt": "Bronze plain bushing 16mm OD 12mm ID 20mm length"},
    {"id": "EASY-05", "category": "Easy", "name": "Dowel Pin", "prompt": "Cylindrical dowel pin 8mm diameter 40mm length"},
    {"id": "EASY-06", "category": "Easy", "name": "Pivot Pin", "prompt": "Pivot pin 12mm diameter 50mm length with chamfered ends"},
    {"id": "EASY-07", "category": "Easy", "name": "M12 Hex Nut", "prompt": "Hex nut M12 across flats 19mm height 10mm"},
    {"id": "EASY-08", "category": "Easy", "name": "Metric M10 Nut", "prompt": "Hex nut 24mm outer diameter with M10 thread bore"},
    {"id": "EASY-09", "category": "Easy", "name": "Square Spacer Block", "prompt": "Square spacer block 30x30mm height 10mm with 8mm center hole"},
    {"id": "EASY-10", "category": "Easy", "name": "M8 Hex Head Bolt", "prompt": "M8 hex head bolt 13mm head 8mm shank 45mm length"},
    {"id": "EASY-11", "category": "Easy", "name": "Socket Cap Screw", "prompt": "Socket head cap screw 10mm head 6mm shank 30mm length"},
    {"id": "EASY-12", "category": "Easy", "name": "Solid Steel Shaft", "prompt": "Solid steel shaft 15mm diameter 100mm length"},
    {"id": "EASY-13", "category": "Easy", "name": "Hollow Tube Sleeve", "prompt": "Hollow sleeve 22mm OD 14mm ID 60mm length"},
    {"id": "EASY-14", "category": "Easy", "name": "Circular Mounting Disc", "prompt": "Circular mounting disc 60mm diameter 8mm thick with 10mm center hole"},
    {"id": "EASY-15", "category": "Easy", "name": "Rectangular Shim", "prompt": "Rectangular mounting shim 50x30x4mm"},
    {"id": "EASY-16", "category": "Easy", "name": "Centering Ring", "prompt": "Centering ring 40mm OD 28mm ID 6mm width"},
    {"id": "EASY-17", "category": "Easy", "name": "Small Flat Washer", "prompt": "Flat washer 18mm OD 8.4mm ID 1.6mm thickness"},
    {"id": "EASY-18", "category": "Easy", "name": "Step Spacer", "prompt": "Step spacer 20mm OD step to 14mm OD length 25mm"},
    {"id": "EASY-19", "category": "Easy", "name": "Flanged Bushing", "prompt": "Flanged bushing 20mm flange 15mm body 10mm bore length 18mm"},
    {"id": "EASY-20", "category": "Easy", "name": "Hex Standoff", "prompt": "Hex standoff 10mm hex height 25mm with M5 through hole"},

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 2: 30 MEDIUM MODELS (Intermediate Mechanical Components & Features)
    # ══════════════════════════════════════════════════════════════════════════
    {"id": "MED-01", "category": "Medium", "name": "Stepped Drive Shaft", "prompt": "Stepped drive shaft 25mm to 18mm diameter length 120mm with keyway slot"},
    {"id": "MED-02", "category": "Medium", "name": "Two-Step Shaft", "prompt": "Two-step shaft 30mm to 20mm diameter length 90mm with end chamfers"},
    {"id": "MED-03", "category": "Medium", "name": "Three-Step Transmission Shaft", "prompt": "Three-step transmission shaft 35mm 25mm 20mm length 150mm"},
    {"id": "MED-04", "category": "Medium", "name": "L-Shaped Mounting Bracket", "prompt": "L-shaped mounting bracket 60x50x6mm with two 8mm mounting holes"},
    {"id": "MED-05", "category": "Medium", "name": "Stiffened Angle Bracket", "prompt": "Angle bracket 70x40x8mm with stiffening fillet and 4 clearance holes"},
    {"id": "MED-06", "category": "Medium", "name": "Heavy Duty L-Bracket", "prompt": "Heavy duty L-bracket 80x60x10mm with 12mm bolt slots"},
    {"id": "MED-07", "category": "Medium", "name": "Four-Hole Pipe Flange", "prompt": "Pipe flange 90mm OD 40mm bore 12mm thick with 4 bolt circle holes"},
    {"id": "MED-08", "category": "Medium", "name": "Blind Pipe Flange", "prompt": "Blind pipe flange 80mm OD 14mm thick with 4 hole pattern"},
    {"id": "MED-09", "category": "Medium", "name": "Six-Hole Companion Flange", "prompt": "High pressure companion flange 100mm OD 50mm ID with 6 bolt holes"},
    {"id": "MED-10", "category": "Medium", "name": "Spur Gear 48mm PD", "prompt": "Spur gear 24 teeth 48mm pitch diameter 15mm bore with 5mm keyway"},
    {"id": "MED-11", "category": "Medium", "name": "Spur Gear 72mm PD", "prompt": "Spur gear 36 teeth 72mm pitch diameter 20mm bore face width 18mm"},
    {"id": "MED-12", "category": "Medium", "name": "Timing Belt Pulley", "prompt": "Timing belt pulley 50mm diameter 12mm bore with side retaining flanges"},
    {"id": "MED-13", "category": "Medium", "name": "V-Belt Pulley with Hub", "prompt": "V-belt pulley 80mm diameter with trapezoidal belt groove and hub"},
    {"id": "MED-14", "category": "Medium", "name": "Pillow Block Bearing Housing", "prompt": "Bearing pillow block 75x30x40mm with 25mm bearing bore and 2 base holes"},
    {"id": "MED-15", "category": "Medium", "name": "Flanged Bearing Cartridge", "prompt": "Flanged bearing cartridge 65mm OD 30mm bore with 3 mounting holes"},
    {"id": "MED-16", "category": "Medium", "name": "Split Bearing Cap", "prompt": "Split bearing cap 60x35x25mm with semi-circular bore"},
    {"id": "MED-17", "category": "Medium", "name": "Connecting Rod Link", "prompt": "Connecting rod link 110mm center-to-center with 20mm and 12mm pin bores"},
    {"id": "MED-18", "category": "Medium", "name": "Bellcrank Lever", "prompt": "Control arm bellcrank with three 8mm pivot holes at 90 degrees"},
    {"id": "MED-19", "category": "Medium", "name": "Clevis Mount Bracket", "prompt": "Clevis mount bracket 50x40x35mm with 10mm cross pin hole"},
    {"id": "MED-20", "category": "Medium", "name": "U-Bracket Channel", "prompt": "U-bracket channel 60x40x30mm wall thickness 5mm with 2 pivot holes"},
    {"id": "MED-21", "category": "Medium", "name": "NEMA 23 Motor Mount", "prompt": "Motor mounting plate 100x80x8mm with NEMA 23 mounting pattern"},
    {"id": "MED-22", "category": "Medium", "name": "Sensor Clamp Block", "prompt": "Sensor mounting clamp block 45x30x20mm with 18mm barrel clamp"},
    {"id": "MED-23", "category": "Medium", "name": "Castellated Lock Collar", "prompt": "Castellated lock collar 32mm OD 18mm ID with 4 radial slots"},
    {"id": "MED-24", "category": "Medium", "name": "Hex Fitting Adapter", "prompt": "Threaded adapter fitting 28mm hex with 1/2 inch through bore"},
    {"id": "MED-25", "category": "Medium", "name": "Shaft Clamping Collar", "prompt": "Shaft collar 35mm OD 20mm bore 12mm width with M5 clamping screw hole"},
    {"id": "MED-26", "category": "Medium", "name": "Electronics Enclosure Box", "prompt": "Electronics enclosure base 90x60x25mm wall thickness 3mm with 4 corner standoffs"},
    {"id": "MED-27", "category": "Medium", "name": "Enclosure Cover Lid", "prompt": "Enclosure lid 90x60x5mm with 4 perimeter counterbore holes"},
    {"id": "MED-28", "category": "Medium", "name": "T-Slot Sliding Nut", "prompt": "T-slot sliding nut block 20x15x8mm with M6 center tap hole"},
    {"id": "MED-29", "category": "Medium", "name": "Dovetail Guide Gib", "prompt": "Dovetail slide gib block 80x25x12mm with angled guide face"},
    {"id": "MED-30", "category": "Medium", "name": "Linear Guide Carriage Plate", "prompt": "Linear guide carriage plate 70x50x12mm with 4 M4 mounting threads"},

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 3: 50 COMPLEX MODELS (Assemblies & Advanced Geometric Mechanisms)
    # ══════════════════════════════════════════════════════════════════════════
    {"id": "CMPLX-01", "category": "Complex", "name": "Three-Finger Robotic Gripper", "prompt": "Three-finger robotic gripper assembly with base mounting plate, 3 articulated fingers, pivot pins, links, and central linear actuator"},
    {"id": "CMPLX-02", "category": "Complex", "name": "Parallel Jaw Gripper", "prompt": "Robotic end effector gripper assembly with palm plate, 2 opposed fingers, linkage bars, and pneumatic cylinder"},
    {"id": "CMPLX-03", "category": "Complex", "name": "Three-Jaw Lathe Chuck", "prompt": "3-jaw chuck assembly with body plate, 3 stepped jaws, scroll plate, and guide slots"},
    {"id": "CMPLX-04", "category": "Complex", "name": "Planetary Gearbox Set", "prompt": "Planetary gearbox assembly with sun gear, 3 planet gears, carrier plate, ring gear, and input shaft"},
    {"id": "CMPLX-05", "category": "Complex", "name": "Spur Gear Reduction Stage", "prompt": "Spur gear reduction assembly with pinion gear, driven gear, two parallel shafts, and bearing bracket"},
    {"id": "CMPLX-06", "category": "Complex", "name": "Right-Angle Bevel Drive", "prompt": "Bevel gear 90 degree drive assembly with pinion, bevel gear, right angle bracket, and input/output shafts"},
    {"id": "CMPLX-07", "category": "Complex", "name": "Worm Gear Reducer", "prompt": "Worm gear speed reducer assembly with worm screw, worm wheel, shafts, and gearbox housing"},
    {"id": "CMPLX-08", "category": "Complex", "name": "Swivel Caster Wheel", "prompt": "Caster wheel assembly with top mounting plate, swivel fork bracket, 80mm wheel, axle pin, and bushings"},
    {"id": "CMPLX-09", "category": "Complex", "name": "Heavy Swivel Caster", "prompt": "Heavy duty swivel caster assembly with dual wheel fork, pivot pin, and mounting flange"},
    {"id": "CMPLX-10", "category": "Complex", "name": "Linear Slide Stage", "prompt": "Linear slide carriage assembly with guide rail, carriage block, 4 guide pins, and lead screw drive"},
    {"id": "CMPLX-11", "category": "Complex", "name": "Miniature Translation Stage", "prompt": "Miniature linear translation stage with base plate, sliding table, micrometer barrel, and return springs"},
    {"id": "CMPLX-12", "category": "Complex", "name": "Lead Screw Actuator", "prompt": "Lead screw linear actuator assembly with stepper motor mount, lead screw, nut block, and carriage table"},
    {"id": "CMPLX-13", "category": "Complex", "name": "Flanged Pipe Joint", "prompt": "Flanged pipe joint assembly with two mating pipe flanges, center gasket, 4 hex bolts, and 4 hex nuts"},
    {"id": "CMPLX-14", "category": "Complex", "name": "Pipe Sleeve Coupling", "prompt": "High pressure pipe coupling assembly with 2 pipe stubs, sleeve coupling, and sealing O-rings"},
    {"id": "CMPLX-15", "category": "Complex", "name": "Flanged Rigid Coupling", "prompt": "Rigid shaft coupling assembly with two flanged hubs, 4 connecting bolts, and drive key"},
    {"id": "CMPLX-16", "category": "Complex", "name": "Oldham Flexible Coupling", "prompt": "Oldham flexible coupling assembly with two slotted hubs and floating center disc"},
    {"id": "CMPLX-17", "category": "Complex", "name": "Three-Jaw Flexible Coupling", "prompt": "Jaw coupling assembly with two 3-jaw coupling hubs and elastomeric spider insert"},
    {"id": "CMPLX-18", "category": "Complex", "name": "Cardan Universal Joint", "prompt": "Universal joint cardan assembly with input yoke, center cross spider pin, and output yoke"},
    {"id": "CMPLX-19", "category": "Complex", "name": "Split Pillow Block Unit", "prompt": "Pillow block bearing assembly with split cast housing, deep groove ball bearing, shaft, and retaining collar"},
    {"id": "CMPLX-20", "category": "Complex", "name": "Square Flanged Bearing Unit", "prompt": "Flanged bearing unit assembly with 4-bolt square flange housing, insert ball bearing, and shaft"},
    {"id": "CMPLX-21", "category": "Complex", "name": "Quarter-Turn Ball Valve", "prompt": "Ball valve assembly with valve body, rotating ball with fluid port, stem shaft, bonnet, and handle lever"},
    {"id": "CMPLX-22", "category": "Complex", "name": "Spring Check Valve", "prompt": "Check valve assembly with valve body housing, spring-loaded poppet disc, and retaining cap"},
    {"id": "CMPLX-23", "category": "Complex", "name": "Handwheel Globe Valve", "prompt": "Globe valve assembly with cast body, valve seat, plug disc, threaded stem, and handwheel"},
    {"id": "CMPLX-24", "category": "Complex", "name": "Bench Screw Vise", "prompt": "Bench vise clamping mechanism assembly with fixed base jaw, sliding jaw, lead screw, and turn handle"},
    {"id": "CMPLX-25", "category": "Complex", "name": "Over-Center Toggle Clamp", "prompt": "Toggle clamp assembly with base bracket, toggle link, pivot rivets, handle, and clamping spindle"},
    {"id": "CMPLX-26", "category": "Complex", "name": "Workshop C-Clamp", "prompt": "C-clamp assembly with cast C-frame, threaded clamping screw, swivel pad, and Tommy bar handle"},
    {"id": "CMPLX-27", "category": "Complex", "name": "Robotic Elbow Joint", "prompt": "Robotic arm elbow joint assembly with motor bracket, harmonic drive housing, pivot shaft, and output arm"},
    {"id": "CMPLX-28", "category": "Complex", "name": "2-DOF Robot Wrist", "prompt": "2-DOF robotic wrist mechanism assembly with pitch yoke, roll shaft, bevel gears, and tool mounting flange"},
    {"id": "CMPLX-29", "category": "Complex", "name": "Scissor Lift Mechanism", "prompt": "Scissor lift mechanism assembly with top platform, bottom base, 4 crossing scissor arms, and center pivot pins"},
    {"id": "CMPLX-30", "category": "Complex", "name": "Four-Bar Planar Linkage", "prompt": "4-bar linkage mechanism assembly with fixed ground link, crank arm, rocker arm, connecting coupler, and pivot pins"},
    {"id": "CMPLX-31", "category": "Complex", "name": "Slider-Crank Mechanism", "prompt": "Slider-crank mechanism assembly with rotating flywheel crank, connecting rod, crosshead pin, and piston slider"},
    {"id": "CMPLX-32", "category": "Complex", "name": "Four-Slot Geneva Drive", "prompt": "Geneva mechanism assembly with 4-slot Geneva wheel, driving pin disc, and parallel mounting plate"},
    {"id": "CMPLX-33", "category": "Complex", "name": "Cam and Roller Follower", "prompt": "Cam and follower mechanism assembly with eccentric plate cam, roller follower, guide bushing, and follower shaft"},
    {"id": "CMPLX-34", "category": "Complex", "name": "Centrifugal Pump Impeller", "prompt": "Centrifugal pump impeller assembly with front shroud, back shroud, 6 curved backward-swept vanes, and keyed drive hub"},
    {"id": "CMPLX-35", "category": "Complex", "name": "Axial Fan Rotor", "prompt": "Axial flow fan rotor assembly with aerodynamic center hub and 5 twisted airfoil blades"},
    {"id": "CMPLX-36", "category": "Complex", "name": "Helical Screw Compressor", "prompt": "Helical rotor compressor assembly with male 4-lobe rotor, female 6-lobe rotor, and end plates"},
    {"id": "CMPLX-37", "category": "Complex", "name": "Double-Acting Hydraulic Cylinder", "prompt": "Hydraulic cylinder assembly with cylinder barrel, piston head with seal groove, piston rod, and clevis end cap"},
    {"id": "CMPLX-38", "category": "Complex", "name": "Rack and Pinion Rotary Actuator", "prompt": "Pneumatic rotary actuator assembly with rack and pinion housing, dual piston racks, and output pinion shaft"},
    {"id": "CMPLX-39", "category": "Complex", "name": "Coilover Shock Absorber", "prompt": "Shock absorber damper assembly with outer cylinder tube, inner piston rod, coil spring, and eyelet mounts"},
    {"id": "CMPLX-40", "category": "Complex", "name": "Telescopic Mast Mechanism", "prompt": "Telescopic mast assembly with outer square tube, intermediate tube, inner stage tube, and guide collars"},
    {"id": "CMPLX-41", "category": "Complex", "name": "Drill Press Spindle Quill", "prompt": "Drill press spindle quill assembly with outer quill sleeve, rotating spindle shaft, dual bearings, and drive pulley"},
    {"id": "CMPLX-42", "category": "Complex", "name": "Lathe Tailstock Mechanism", "prompt": "Lathe tailstock assembly with cast body base, quill barrel, handwheel, and dead center taper"},
    {"id": "CMPLX-43", "category": "Complex", "name": "Bicycle Crankset & Spindle", "prompt": "Bicycle pedal crank assembly with crank arm, threaded pedal spindle, pedal cage platform, and dual ball bearings"},
    {"id": "CMPLX-44", "category": "Complex", "name": "Double Sheave Pulley Block", "prompt": "Pulley block and tackle assembly with dual side plates, 2 grooved sheave wheels, center axle pin, and swivel hook"},
    {"id": "CMPLX-45", "category": "Complex", "name": "Spring-Loaded Belt Tensioner", "prompt": "Belt tensioner idler assembly with pivoting arm bracket, ball bearing idler pulley, torsion spring, and pivot bolt"},
    {"id": "CMPLX-46", "category": "Complex", "name": "Automotive Drum Brake", "prompt": "Drum brake mechanism assembly with backing plate, two curved brake shoes, hydraulic wheel cylinder, and return spring"},
    {"id": "CMPLX-47", "category": "Complex", "name": "Floating Disc Brake Caliper", "prompt": "Disc brake caliper assembly with caliper bracket, hydraulic piston, two brake friction pads, and mounting guide pins"},
    {"id": "CMPLX-48", "category": "Complex", "name": "Exhaust Collector Manifold", "prompt": "Exhaust manifold turbine housing with multi-branch exhaust collector runners converging to turbine inlet flange"},
    {"id": "CMPLX-49", "category": "Complex", "name": "Aerospace Ribbed Engine Mount", "prompt": "Aerospace engine bracket with topological weight-reduction cutouts, stiffening ribs, 4 engine lugs, and dual mounting flanges"},
    {"id": "CMPLX-50", "category": "Complex", "name": "Volute Scroll Compressor Housing", "prompt": "Complex multi-stage centrifugal compressor housing with volute scroll casing, diffuser passage, and suction inlet bellmouth"},
]


def run_single_model(case: Dict[str, Any]) -> Dict[str, Any]:
    """Execute pipeline for a single model and collect comprehensive telemetry."""
    cid = case["id"]
    category = case["category"]
    name = case["name"]
    prompt = case["prompt"]
    
    t0 = time.time()
    initial_state: AgentState = {
        "design_id": f"bench_{cid.lower()}",
        "session_id": "sess_benchmark_100",
        "user_prompt": prompt,
        "max_retries": 3,
        "parsed_intent": {},
        "cad_code": "",
        "cad_script_history": [],
        "execution_result": {},
        "feature_tree": {},
        "export_paths": {},
        "geometry_valid": False,
        "validation_errors": [],
        "validation_stats": {},
        "dfm_report": {},
        "engineering_report": {},
        "cost_estimate": {},
        "safety_report": {},
        "cam_report": {},
        "doc_report": {},
        "alternatives": [],
        "confidence_scores": {},
        "error_count": 0,
        "last_error": "",
        "messages": [],
    }

    try:
        final_state = cad_graph.invoke(initial_state)
        latency = round(time.time() - t0, 3)

        is_assembly = final_state.get("is_assembly", False)
        cadir_valid = final_state.get("cadir_valid", False) or (is_assembly and bool(final_state.get("component_cadirs")))
        geometry_valid = final_state.get("geometry_valid", False)
        exec_res = final_state.get("execution_result", {})
        volume = exec_res.get("volume", 0.0)
        bbox = exec_res.get("bounding_box", {})

        export_paths = final_state.get("export_paths", {})
        has_step = bool(export_paths.get("step") and Path(export_paths["step"]).exists())
        has_stl = bool(export_paths.get("stl") and Path(export_paths["stl"]).exists())
        has_glb = bool(export_paths.get("glb") and Path(export_paths["glb"]).exists())

        asm_val = final_state.get("assembly_validation", {})
        interf_vol = asm_val.get("total_interference_volume", 0.0) if is_assembly else 0.0
        clearance_ok = asm_val.get("clearance_check_passed", True) if is_assembly else True
        
        asm_obj = final_state.get("assembly_spec")
        comp_count = 1
        if is_assembly and asm_obj is not None:
            if hasattr(asm_obj, "components"):
                comp_count = len(asm_obj.components)
            elif isinstance(asm_obj, dict):
                comp_count = len(asm_obj.get("components", []))

        success = (cadir_valid and geometry_valid and (has_step or has_stl) and volume > 0)

        return {
            "id": cid,
            "category": category,
            "name": name,
            "prompt": prompt,
            "is_assembly": is_assembly,
            "component_count": comp_count,
            "cadir_valid": cadir_valid,
            "geometry_valid": geometry_valid,
            "volume_mm3": round(volume, 2),
            "bounding_box": bbox,
            "interference_volume_mm3": round(interf_vol, 4),
            "clearance_pass": clearance_ok,
            "has_step": has_step,
            "has_stl": has_stl,
            "has_glb": has_glb,
            "latency_sec": latency,
            "success": success,
            "error": final_state.get("last_error", ""),
        }
    except Exception as e:
        latency = round(time.time() - t0, 3)
        return {
            "id": cid,
            "category": category,
            "name": name,
            "prompt": prompt,
            "is_assembly": False,
            "component_count": 0,
            "cadir_valid": False,
            "geometry_valid": False,
            "volume_mm3": 0.0,
            "bounding_box": {},
            "interference_volume_mm3": 0.0,
            "clearance_pass": False,
            "has_step": False,
            "has_stl": False,
            "has_glb": False,
            "latency_sec": latency,
            "success": False,
            "error": str(e),
        }


def main():
    print("=" * 80)
    print("AI-NATIVE CAD-CAM WORKSTATION: 100-MODEL EVALUATION BENCHMARK")
    print(f"Total Models to Evaluate: {len(EVAL_CATALOG)}")
    print("Tiers: 20 Easy | 30 Medium | 50 Complex")
    print("=" * 80)

    results: List[Dict[str, Any]] = []
    start_all = time.time()

    for idx, case in enumerate(EVAL_CATALOG, 1):
        print(f"[{idx:03d}/100] ({case['category']}) Testing: {case['name']} ... ", end="", flush=True)
        res = run_single_model(case)
        status_str = "PASS" if res["success"] else "FAIL"
        print(f"{status_str} (vol: {res['volume_mm3']} mm3, {res['latency_sec']}s, asm={res['is_assembly']})")
        results.append(res)

    total_time = round(time.time() - start_all, 2)

    # Compute Statistics
    easy_results = [r for r in results if r["category"] == "Easy"]
    med_results = [r for r in results if r["category"] == "Medium"]
    cmplx_results = [r for r in results if r["category"] == "Complex"]

    easy_pass = sum(1 for r in easy_results if r["success"])
    med_pass = sum(1 for r in med_results if r["success"])
    cmplx_pass = sum(1 for r in cmplx_results if r["success"])
    total_pass = sum(1 for r in results if r["success"])

    avg_latency = round(sum(r["latency_sec"] for r in results) / len(results), 2)
    step_export_count = sum(1 for r in results if r["has_step"])
    stl_export_count = sum(1 for r in results if r["has_stl"])
    glb_export_count = sum(1 for r in results if r["has_glb"])

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_models": len(results),
        "total_passed": total_pass,
        "total_failed": len(results) - total_pass,
        "overall_success_rate": round((total_pass / len(results)) * 100.0, 1),
        "total_time_seconds": total_time,
        "average_latency_seconds": avg_latency,
        "exports": {
            "step_count": step_export_count,
            "stl_count": stl_export_count,
            "glb_count": glb_export_count,
        },
        "tiers": {
            "easy": {
                "total": len(easy_results),
                "passed": easy_pass,
                "rate": round((easy_pass / len(easy_results)) * 100.0, 1),
            },
            "medium": {
                "total": len(med_results),
                "passed": med_pass,
                "rate": round((med_pass / len(med_results)) * 100.0, 1),
            },
            "complex": {
                "total": len(cmplx_results),
                "passed": cmplx_pass,
                "rate": round((cmplx_pass / len(cmplx_results)) * 100.0, 1),
            },
        },
    }

    # Save Results to JSON
    out_dir = backend_dir / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "benchmark_100_models_results.json"
    
    payload = {
        "summary": summary,
        "results": results,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("\n" + "=" * 80)
    print("BENCHMARK EXECUTION COMPLETE")
    print(f"Overall Success Rate: {summary['overall_success_rate']}% ({total_pass}/{len(results)})")
    print(f"  - Easy Tier:    {summary['tiers']['easy']['rate']}% ({easy_pass}/{len(easy_results)})")
    print(f"  - Medium Tier:  {summary['tiers']['medium']['rate']}% ({med_pass}/{len(med_results)})")
    print(f"  - Complex Tier: {summary['tiers']['complex']['rate']}% ({cmplx_pass}/{len(cmplx_results)})")
    print(f"STEP Exports: {step_export_count}/{len(results)} | STL Exports: {stl_export_count}/{len(results)} | GLB Exports: {glb_export_count}/{len(results)}")
    print(f"Total Time: {total_time}s | Avg Latency: {avg_latency}s/model")
    print(f"Results File: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
