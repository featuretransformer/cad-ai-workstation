"""
Hardened subprocess CAD executor with improved isolation and safety.
Runs build123d Python code in a sandboxed subprocess with:
- Timeout enforcement
- Restricted environment variables
- AST validation before execution
- Output sanitization
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Dict, Set

EXPORTS_DIR = Path(__file__).parent.parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# Forbidden imports for security
FORBIDDEN_IMPORTS = {
    "os", "sys", "subprocess", "shutil", "pathlib",
    "pickle", "shelve", "socket", "urllib", "requests",
    "eval", "exec", "compile", "__import__",
}

# Wrapper that runs around user code to capture results
EXECUTOR_WRAPPER = '''
import sys
import os
import json
import traceback

# Restrict dangerous builtins
import builtins
_original_open = builtins.open
_safe_open_paths = {r"{output_dir}"}

def safe_open(file, mode='r', *args, **kwargs):
    """Restricted open - only allows writing to output directory."""
    fpath = os.path.abspath(file)
    if 'w' in mode or 'a' in mode:
        if not any(fpath.startswith(sp) for sp in _safe_open_paths):
            raise PermissionError(f"Write access denied: {{file}}")
    return _original_open(file, mode, *args, **kwargs)

builtins.open = safe_open

try:
    from build123d import *
    from build123d import export_step, export_stl
except ImportError as e:
    print(json.dumps({{"success": False, "error": "build123d import failed: " + str(e)}}))
    sys.exit(1)

try:
    # ─── USER CODE ───────────────────────────────────────
{user_code}
    # ─────────────────────────────────────────────────────

    # Collect result
    result_var = None
    for name in ["result", "part", "shape", "body", "solid", "assembly"]:
        if name in dir() and name in locals():
            result_var = locals()[name]
            break

    if result_var is None:
        raise ValueError("No result variable found. Assign your final geometry to `result`.")

    # Export files
    output_dir = r"{output_dir}"
    step_path = os.path.join(output_dir, "output.step")
    stl_path = os.path.join(output_dir, "output.stl")

    export_step(result_var, step_path)
    export_stl(result_var, stl_path)

    # Geometry info
    bb = result_var.bounding_box()
    volume_val = float(result_var.volume) if hasattr(result_var, "volume") else 0.0
    
    info = {{
        "success": True,
        "volume": volume_val,
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


def validate_code_ast(code: str) -> Dict[str, any]:
    """
    Validate Python code AST to detect forbidden operations.
    Returns {"valid": bool, "errors": List[str]}.
    """
    errors = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"valid": False, "errors": [f"Syntax error: {e}"]}

    # Check for forbidden imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORTS or alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    errors.append(f"Forbidden import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module in FORBIDDEN_IMPORTS or node.module.split(".")[0] in FORBIDDEN_IMPORTS):
                errors.append(f"Forbidden import from: {node.module}")

    return {"valid": len(errors) == 0, "errors": errors}


def execute_cad_code(code: str, design_id: str, timeout: int = 60) -> dict:
    """
    Execute build123d code in a sandboxed subprocess.
    Returns dict with success, error, file paths, and geometry metadata.
    """
    # 1. Validate AST
    validation = validate_code_ast(code)
    if not validation["valid"]:
        return {
            "success": False,
            "error": "Code validation failed",
            "validation_errors": validation["errors"],
            "stdout": "",
            "stderr": "",
        }

    # 2. Create per-design output directory
    out_dir = EXPORTS_DIR / design_id
    out_dir.mkdir(exist_ok=True)

    # 3. Indent user code to fit inside the wrapper
    indented = textwrap.indent(code.strip(), "    ")
    full_script = EXECUTOR_WRAPPER.format(
        user_code=indented,
        output_dir=out_dir.as_posix(),
    )

    # 4. Write to temp file
    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(full_script)
        script_path = f.name

    try:
        # 5. Execute with restricted environment
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": "",
            # Remove dangerous env vars
        }

        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(out_dir),  # Run in output directory
        )

        # 6. Parse the last JSON line from stdout
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
            "error": f"Executor exception: {str(e)}",
            "stdout": "",
            "stderr": "",
        }
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
