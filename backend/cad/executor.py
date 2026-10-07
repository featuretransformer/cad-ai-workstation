"""Controlled subprocess execution for generated build123d code."""
import ast
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

EXPORTS_DIR = Path(__file__).parent.parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)
_ALLOWED_IMPORTS = {"build123d"}
_BLOCKED_NAMES = {"__import__", "open", "exec", "eval", "compile", "input", "breakpoint"}
_BLOCKED_ATTRS = {"system", "popen", "run", "call", "check_call", "check_output", "connect", "urlopen"}


def _validate_generated_code(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(f"Generated CAD code is invalid Python: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] not in _ALLOWED_IMPORTS for alias in node.names):
                raise ValueError("Only build123d imports are allowed")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if module not in _ALLOWED_IMPORTS:
                raise ValueError(f"Import not allowed: {node.module}")
        elif isinstance(node, ast.Name) and node.id in _BLOCKED_NAMES:
            raise ValueError(f"Operation not allowed: {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr in _BLOCKED_ATTRS:
            raise ValueError(f"Operation not allowed: {node.attr}")


EXECUTOR_WRAPPER = '''
import json, os, sys, traceback
try:
    from build123d import *
    from build123d import export_step, export_stl
    # Generated code has already passed the parent-process AST policy.
{user_code}
    result_var = next((globals()[name] for name in ("result", "part", "shape", "body", "solid") if name in globals()), None)
    if result_var is None:
        raise ValueError("No result variable found. Assign final geometry to `result`.")
    output_dir = r"{output_dir}"
    step_path = os.path.join(output_dir, "output.step")
    stl_path = os.path.join(output_dir, "output.stl")
    export_step(result_var, step_path)
    export_stl(result_var, stl_path)
    bb = result_var.bounding_box()
    print(json.dumps({{"success": True, "volume": float(getattr(result_var, "volume", 0)), "bounding_box": {{"xmin": float(bb.min.X), "xmax": float(bb.max.X), "ymin": float(bb.min.Y), "ymax": float(bb.max.Y), "zmin": float(bb.min.Z), "zmax": float(bb.max.Z)}}, "step_path": step_path, "stl_path": stl_path}}))
except Exception as exc:
    print(json.dumps({{"success": False, "error": str(exc), "traceback": traceback.format_exc()}}))
    sys.exit(1)
'''


def execute_cad_code(code: str, design_id: str, timeout: int = 60) -> dict:
    _validate_generated_code(code)
    out_dir = EXPORTS_DIR / design_id
    out_dir.mkdir(exist_ok=True)
    full_script = EXECUTOR_WRAPPER.format(user_code=textwrap.indent(code.strip(), "    "), output_dir=out_dir.as_posix())
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as file:
        file.write(full_script)
        script_path = file.name
    try:
        proc = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=timeout, env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"})
        result = next((json.loads(line) for line in reversed(proc.stdout.splitlines()) if line.strip() and _is_json(line)), None)
        if result is None:
            return {"success": False, "error": "No JSON output from executor", "stdout": proc.stdout, "stderr": proc.stderr}
        result.update(stdout=proc.stdout, stderr=proc.stderr)
        return result
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"CAD execution timed out after {timeout} seconds", "stdout": "", "stderr": ""}
    except Exception as exc:
        return {"success": False, "error": str(exc), "stdout": "", "stderr": ""}
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


def _is_json(line: str) -> bool:
    try:
        json.loads(line)
        return True
    except json.JSONDecodeError:
        return False
