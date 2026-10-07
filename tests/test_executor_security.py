import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parents[1] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.executor import _validate_generated_code


def test_build123d_star_import_is_allowed():
    _validate_generated_code("from build123d import *\nresult = None")


def test_build123d_named_import_is_allowed():
    _validate_generated_code("from build123d import Box, export_step\nresult = None")


@pytest.mark.parametrize("code", [
    "import os",
    "from pathlib import Path",
    "result = open('secrets.txt')",
    "result = __import__('os')",
])
def test_unsafe_generated_code_is_rejected(code):
    with pytest.raises(ValueError):
        _validate_generated_code(code)
