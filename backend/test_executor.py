import os, subprocess, sys
from pathlib import Path
from cad.executor import execute_cad_code

code = """from build123d import *
with BuildPart() as p:
    Box(10, 10, 10)
result = p.part
"""

res = execute_cad_code(code, "test_wrapper_123")
print(res)
