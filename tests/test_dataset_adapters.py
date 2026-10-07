"""
Unit tests for CAD dataset adapters:
CadQueryTranslator, BenchCADAdapter, Fusion360Adapter, Drawing2CADAdapter, and Adapter Registry.
"""
import pytest
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from datasets.cadquery_translator import CadQueryTranslator
from datasets.benchcad_adapter import BenchCADAdapter
from datasets.fusion360_adapter import Fusion360Adapter
from datasets.drawing2cad_adapter import Drawing2CADAdapter
from datasets.registry import (
    register_adapter,
    list_registered_adapters,
    get_adapter,
    get_available_adapters,
)
from cad.cadir.schema import CADIRDocument, CADIRFeature
from cad.cadir.validator import validate_cadir_document


# ─── CadQueryTranslator Tests ─────────────────────────────────────────────────────────

def test_cadquery_translator_washer():
    code = """
import cadquery as cq

result = (
    cq.Workplane("XZ")
    .circle(32.4)
    .extrude(5.0)
    .faces(">Y").workplane()
    .hole(37.0)
    .edges(">Y")
    .chamfer(0.4)
)
"""
    translator = CadQueryTranslator()
    doc = translator.translate(code, doc_id="test_washer", name="Test Washer")

    assert doc.id == "test_washer"
    assert len(doc.features) == 3

    # Feature 1: Extrude
    assert doc.features[0].feature_type == "extrude"
    assert doc.features[0].distance == 5.0
    assert doc.features[0].dependencies == []

    # Feature 2: Hole
    assert doc.features[1].feature_type == "hole"
    assert doc.features[1].diameter == 37.0
    assert doc.features[1].dependencies == [doc.features[0].id]

    # Feature 3: Chamfer
    assert doc.features[2].feature_type == "chamfer"
    assert doc.features[2].length == 0.4
    assert doc.features[2].dependencies == [doc.features[1].id]

    # Validate topological integrity
    val_res = validate_cadir_document(doc)
    assert val_res.is_valid
    assert len(val_res.errors) == 0


def test_cadquery_translator_hex_nut():
    code = """
import cadquery as cq

result = (
    cq.Workplane("XY")
    .polygon(6, 6.35)
    .extrude(2.4)
    .faces(">Z").workplane()
    .circle(1.5)
    .cutThruAll()
)
"""
    translator = CadQueryTranslator()
    doc = translator.translate(code, doc_id="test_hex_nut", name="Test Hex Nut")

    assert len(doc.features) == 2
    assert doc.features[0].feature_type == "extrude"
    assert doc.features[1].feature_type == "hole"
    assert doc.features[1].dependencies == [doc.features[0].id]

    val_res = validate_cadir_document(doc)
    assert val_res.is_valid


def test_cadquery_translator_box_with_fillet():
    code = """
import cadquery as cq

result = (
    cq.Workplane("XY")
    .box(50.0, 30.0, 10.0)
    .edges("|Z")
    .fillet(2.5)
    .faces(">Z").workplane()
    .hole(8.0)
)
"""
    translator = CadQueryTranslator()
    doc = translator.translate(code, doc_id="test_box", name="Test Box")

    assert len(doc.features) == 3
    assert doc.features[0].feature_type == "box"
    assert doc.features[0].length == 50.0
    assert doc.features[1].feature_type == "fillet"
    assert doc.features[1].radius == 2.5
    assert doc.features[2].feature_type == "hole"

    val_res = validate_cadir_document(doc)
    assert val_res.is_valid


def test_cadquery_translator_syntax_error():
    translator = CadQueryTranslator()
    doc = translator.translate("def broken_code(", doc_id="err_doc")
    assert "parse_error" in doc.engineering_intent
    assert len(doc.features) == 0


# ─── BenchCADAdapter Tests ────────────────────────────────────────────────────────────

def test_benchcad_adapter_availability():
    datasets_dir = Path(__file__).resolve().parent.parent / "datasets" / "BenchCAD"
    adapter = BenchCADAdapter(datasets_dir)

    assert adapter.is_available()
    count = adapter.get_record_count()
    assert count == 17900


def test_benchcad_adapter_iteration():
    datasets_dir = Path(__file__).resolve().parent.parent / "datasets" / "BenchCAD"
    adapter = BenchCADAdapter(datasets_dir)

    records = list(adapter.iterate_records(limit=3))
    assert len(records) == 3

    for r in records:
        assert "record_id" in r
        assert "family" in r
        assert "code" in r
        assert "import cadquery as cq" in r["code"]


def test_benchcad_adapter_to_cadir():
    datasets_dir = Path(__file__).resolve().parent.parent / "datasets" / "BenchCAD"
    adapter = BenchCADAdapter(datasets_dir)

    record = adapter.get_record("washer_000001_s20260505")
    assert record is not None
    assert record["family"] == "washer"

    doc = adapter.to_cadir(record)
    assert isinstance(doc, CADIRDocument)
    assert doc.id == "washer_000001_s20260505"
    assert doc.component_family == "washer"
    assert len(doc.features) > 0

    val_res = validate_cadir_document(doc)
    assert val_res.is_valid


def test_benchcad_adapter_missing_dir(tmp_path):
    adapter = BenchCADAdapter(tmp_path / "non_existent")
    assert not adapter.is_available()
    assert adapter.get_record_count() == 0
    assert list(adapter.iterate_records()) == []


# ─── Fusion360Adapter Tests ───────────────────────────────────────────────────────────

def test_fusion360_adapter_availability():
    datasets_dir = Path(__file__).resolve().parent.parent / "datasets" / "Fusion360Gallery"
    adapter = Fusion360Adapter(datasets_dir)

    assert adapter.is_available()
    assert adapter.get_record_count() >= 5


def test_fusion360_adapter_to_cadir_single_sketch_extrude():
    datasets_dir = Path(__file__).resolve().parent.parent / "datasets" / "Fusion360Gallery"
    adapter = Fusion360Adapter(datasets_dir)

    record = adapter.get_record("SingleSketchExtrude")
    assert record is not None

    doc = adapter.to_cadir(record)
    assert isinstance(doc, CADIRDocument)
    assert len(doc.features) == 1
    assert doc.features[0].feature_type == "extrude"
    assert len(doc.sketches) == 1
    # Check that constraints were extracted
    assert "constraints" in doc.engineering_intent
    assert len(doc.engineering_intent["constraints"]) >= 4

    val_res = validate_cadir_document(doc)
    assert val_res.is_valid


def test_fusion360_adapter_to_cadir_hexagon():
    datasets_dir = Path(__file__).resolve().parent.parent / "datasets" / "Fusion360Gallery"
    adapter = Fusion360Adapter(datasets_dir)

    record = adapter.get_record("Hexagon")
    assert record is not None

    doc = adapter.to_cadir(record)
    assert isinstance(doc, CADIRDocument)
    # Hexagon has 3 timeline extrusions
    assert len(doc.features) == 3
    for f in doc.features:
        assert f.feature_type == "extrude"

    val_res = validate_cadir_document(doc)
    assert val_res.is_valid


def test_fusion360_adapter_missing_dir(tmp_path):
    adapter = Fusion360Adapter(tmp_path / "non_existent")
    assert not adapter.is_available()
    assert adapter.get_record_count() == 0


# ─── Drawing2CADAdapter Tests ─────────────────────────────────────────────────────────

def test_drawing2cad_adapter_graceful_availability(tmp_path):
    adapter = Drawing2CADAdapter(tmp_path)
    assert not adapter.is_available()
    assert adapter.get_record_count() == 0


def test_drawing2cad_adapter_vector_decoding():
    adapter = Drawing2CADAdapter(Path("datasets/Drawing2CAD-main"))

    # Synthesize a sequence: Circle -> EOS -> Extrude
    # cmd 2: Circle (cx=0, cy=0, r=0.015)
    # cmd 3: EOS
    # cmd 5: Ext (args: 5 sketch, 3 plane, 4 trans, then e1=0.03, e2=0.0, b=0, u=0)
    sequence = [
        [2, 0.0, 0.0, 0.0, 0.0, 0.015],
        [3],
        [5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.03, 0.0, 0, 0],
    ]

    doc = adapter.decode_cad_vector_to_cadir(
        sequence, doc_id="d2c_circle_extrude", name="Decoded Circle"
    )

    assert isinstance(doc, CADIRDocument)
    assert len(doc.features) == 1
    assert doc.features[0].feature_type == "extrude"
    assert doc.features[0].distance == 30.0  # 0.03 * 1000 mm

    val_res = validate_cadir_document(doc)
    assert val_res.is_valid


# ─── Dataset Registry Tests ───────────────────────────────────────────────────────────

def test_adapter_registry_listing():
    registered = list_registered_adapters()
    assert "deepcad" in registered
    assert "benchcad" in registered
    assert "fusion360" in registered
    assert "drawing2cad" in registered


def test_adapter_registry_lookup():
    datasets_dir = Path(__file__).resolve().parent.parent / "datasets"

    adapter_bc = get_adapter("benchcad", dataset_dir=datasets_dir / "BenchCAD")
    assert isinstance(adapter_bc, BenchCADAdapter)

    adapter_f360 = get_adapter("fusion360", dataset_dir=datasets_dir / "Fusion360Gallery")
    assert isinstance(adapter_f360, Fusion360Adapter)

    with pytest.raises(KeyError):
        get_adapter("non_existent_dataset")


def test_adapter_registry_available():
    datasets_dir = Path(__file__).resolve().parent.parent / "datasets"
    available = get_available_adapters(datasets_dir=datasets_dir)

    # DeepCAD, BenchCAD, and Fusion360 (testdata) are present locally
    assert "deepcad" in available
    assert "benchcad" in available
    assert "fusion360" in available
