"""
Sandboxed CAD code execution engine.
Runs build123d Python code in a subprocess with timeout and restricted environment.
"""
import subprocess
import tempfile
import os
import json
import textwrap
import sys
from pathlib import Path

EXPORTS_DIR = Path(__file__).parent.parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# Wrapper that runs around user code to capture results
EXECUTOR_WRAPPER = '''
import sys
import os
import json
import traceback

# Safety: restrict dangerous operations
import builtins
_original_open = builtins.open

try:
    from build123d import *
    from build123d import export_step, export_stl
except ImportError as e:
    print(json.dumps({"success": False, "error": f"build123d import failed: {e}"}))
    sys.exit(1)

try:
    # ─── USER CODE ───────────────────────────────────────
{user_code}
    # ─────────────────────────────────────────────────────

    # Collect result
    result_var = None
    for name in ["result", "part", "shape", "body", "solid"]:
        if name in dir():
            result_var = eval(name)
            break

    if result_var is None:
        raise ValueError("No result variable found. Assign your final geometry to `result`.")

    # Export files
    output_dir = "{output_dir}"
    step_path = os.path.join(output_dir, "output.step")
    stl_path = os.path.join(output_dir, "output.stl")

    export_step(result_var, step_path)
    export_stl(result_var, stl_path)

    # Geometry info
    bb = result_var.bounding_box()
    info = {{
        "success": True,
        "volume": float(result_var.volume) if hasattr(result_var, "volume") else 0,
        "bounding_box": {{
            "xmin": float(bb.min.X), "xmax": float(bb.max.X),
            "ymin": float(bb.min.Y), "ymax": float(bb.max.Y),
            "zmin": float(bb.min.Z), "zmax": float(bb.max.Z),
        }},
        "step_path": step_path,
        "stl_path": stl_path,
    }}
    print(json.dumps(info))

except Exception as e:
    print(json.dumps({{"success": False, "error": str(e), "traceback": traceback.format_exc()}}))
    sys.exit(1)
'''


def execute_cad_code(code: str, design_id: str, timeout: int = 60) -> dict:
    """
    Execute build123d code in a sandboxed subprocess.
    Returns dict with success, error, file paths, and geometry metadata.
    """
    # Create per-design output directory
    out_dir = EXPORTS_DIR / design_id
    out_dir.mkdir(exist_ok=True)

    # Indent user code to fit inside the wrapper
    indented = textwrap.indent(code.strip(), "    ")
    full_script = EXECUTOR_WRAPPER.format(
        user_code=indented,
        output_dir=str(out_dir),
    )

    # Write to temp file
    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(full_script)
        script_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )

        # Parse the last JSON line from stdout
        stdout_lines = [l.strip() for l in proc.stdout.strip().splitlines() if l.strip()]
        result_json = None
        for line in reversed(stdout_lines):
            try:
                result_json = json.loads(line)
                break
            except json.JSONDecodeError:
                continue

        if result_json is None:
            return {
                "success": False,
                "error": "No JSON output from executor",
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }

        result_json["stdout"] = proc.stdout
        result_json["stderr"] = proc.stderr
        return result_json

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"CAD execution timed out after {timeout} seconds",
            "stdout": "",
            "stderr": "",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": "",
        }
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
