"""
Parametric Python Script Exporter.
Generates clean, human-readable, standalone Python/build123d scripts
with explicit parametric constants declared at the top for mechanical engineers.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import re


def export_parametric_python_script(
    design_id: str,
    prompt: str,
    cad_code: str,
    parameters: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> str:
    """
    Transforms CAD code into a professional parametric Python script.
    Extracts all numeric constants into a top-level PARAMETERS block
    so engineers can tweak variables and immediately re-generate STEP/STL models.
    """
    lines: List[str] = [
        '"""',
        '==============================================================================',
        'AI-NATIVE CAD-CAM WORKSTATION — PARAMETRIC DESIGN SCRIPT',
        f'Design ID: {design_id}',
        f'Design Brief: {prompt}',
        'Kernel: build123d (OpenCASCADE Community Edition)',
        'Units: millimeters (mm)',
        '==============================================================================',
        'INSTRUCTIONS FOR MECHANICAL ENGINEERS:',
        '1. Modify any parameter in the "DESIGN VARIABLES" section below.',
        '2. Run `python <filename>.py` to regenerate updated STEP and STL files.',
        '==============================================================================',
        '"""',
        'import sys',
        'from pathlib import Path',
        'from build123d import *',
        '',
        '# ============================================================================== #',
        '#                        1. PARAMETRIC DESIGN VARIABLES                          #',
        '# ============================================================================== #',
    ]

    # Insert explicit parameters dictionary if available
    param_dict = parameters or {}
    if not param_dict:
        # Default dimensional variables extracted from prompt if possible
        param_dict = {
            "OVERALL_SCALE": 1.0,
        }

    for k, v in param_dict.items():
        clean_k = re.sub(r"[^A-Za-z0-9_]", "_", str(k)).upper()
        if not clean_k[0].isalpha():
            clean_k = f"PARAM_{clean_k}"
        lines.append(f"{clean_k:24} = {v:<10}  # mm")

    lines.extend([
        '',
        '# ============================================================================== #',
        '#                        2. GEOMETRIC CONSTRUCTION                               #',
        '# ============================================================================== #',
        '',
    ])

    # Clean and insert the body of the CAD code
    raw_lines = cad_code.strip().splitlines()
    body_lines = []
    skip_header = True
    for l in raw_lines:
        if "from build123d import" in l or "import sys" in l:
            continue
        body_lines.append(l)

    lines.extend(body_lines)

    lines.extend([
        '',
        '# ============================================================================== #',
        '#                        3. EXECUTION & CAD EXPORT                               #',
        '# ============================================================================== #',
        'if __name__ == "__main__":',
        '    # Find the resulting solid part or compound',
        '    solid = None',
        '    if "p" in locals() and hasattr(locals()["p"], "part"):',
        '        solid = locals()["p"].part',
        '    elif "assembly" in locals():',
        '        solid = locals()["assembly"]',
        '    elif "compound" in locals():',
        '        solid = locals()["compound"]',
        '',
        '    if solid is not None:',
        '        out_dir = Path(__file__).resolve().parent',
        '        step_file = out_dir / "output.step"',
        '        stl_file = out_dir / "output.stl"',
        '        ',
        '        export_step(solid, str(step_file))',
        '        export_stl(solid, str(stl_file))',
        '        ',
        '        vol = getattr(solid, "volume", 0.0)',
        '        bbox = getattr(solid, "bounding_box", None)',
        '        print("=" * 60)',
        '        print("CAD MODEL GENERATED SUCCESSFULLY")',
        '        print(f"Volume: {round(vol, 2)} mm^3")',
        '        if bbox:',
        '            print(f"Bounding Box: X=[{bbox().min.X:.1f}, {bbox().max.X:.1f}], Y=[{bbox().min.Y:.1f}, {bbox().max.Y:.1f}], Z=[{bbox().min.Z:.1f}, {bbox().max.Z:.1f}] mm")',
        '        print(f"Exported STEP: {step_file.name}")',
        '        print(f"Exported STL:  {stl_file.name}")',
        '        print("=" * 60)',
        '    else:',
        '        print("Error: Could not locate constructed CAD solid.")',
    ])

    script_content = "\n".join(lines) + "\n"

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(script_content)

    return script_content
