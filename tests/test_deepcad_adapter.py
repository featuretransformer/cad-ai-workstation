"""
Unit tests for DeepCAD dataset adapter.
Phase 2 First Dataset Adapter Verification.
"""
import pytest
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from datasets.deepcad_adapter import DeepCADAdapter
from cad.cadir.validator import validate_cadir_document


@pytest.fixture
def deepcad_adapter():
    project_root = Path(__file__).resolve().parent.parent
    deepcad_dir = project_root / "datasets" / "DeepCAD"
    return DeepCADAdapter(deepcad_dir, scale_to_mm=True)


def test_deepcad_adapter_availability(deepcad_adapter):
    """Verify adapter detects the local DeepCAD dataset files."""
    assert deepcad_adapter.is_available()
    assert deepcad_adapter.dataset_name == "DeepCAD"
    record_count = deepcad_adapter.get_record_count()
    assert record_count > 0, f"Expected records in DeepCAD, found {record_count}"


def test_deepcad_get_specific_record(deepcad_adapter):
    """Verify fetching a specific record by ID."""
    record = deepcad_adapter.get_record("00020000")
    assert record is not None
    assert record["record_id"] == "00020000"
    assert "raw_data" in record
    assert "entities" in record["raw_data"]
    assert "sequence" in record["raw_data"]


def test_deepcad_to_cadir_conversion(deepcad_adapter):
    """
    Verify translating DeepCAD 00020000 into a valid CADIR document.
    """
    record = deepcad_adapter.get_record("00020000")
    assert record is not None

    cadir_doc = deepcad_adapter.to_cadir(record)
    assert cadir_doc.id == "deepcad_00020000"
    assert cadir_doc.units == "mm"
    assert len(cadir_doc.sketches) >= 1
    assert len(cadir_doc.features) >= 1

    # Verify features and sketches are properly linked
    for feat in cadir_doc.features:
        assert feat.feature_type == "extrude"
        assert feat.distance > 0
        assert feat.sketch_id is not None
        assert cadir_doc.get_sketch(feat.sketch_id) is not None

    # Run CADIR validation
    result = validate_cadir_document(cadir_doc)
    assert result.is_valid, f"CADIR validation failed: {result.errors}"
    assert len(result.topological_order) == len(cadir_doc.features)


def test_deepcad_batch_representative_samples(deepcad_adapter):
    """
    Test 5 representative DeepCAD records to verify generalization across different components.
    """
    records = list(deepcad_adapter.iterate_records(limit=5))
    assert len(records) == 5

    for rec in records:
        cadir_doc = deepcad_adapter.to_cadir(rec)
        assert cadir_doc.id.startswith("deepcad_")
        assert len(cadir_doc.features) > 0

        # Validate each generated CADIR document
        result = validate_cadir_document(cadir_doc)
        assert result.is_valid, f"Record {rec['record_id']} failed CADIR validation: {result.errors}"


def test_deepcad_adapter_missing_directory():
    """Verify graceful handling when dataset directory is invalid."""
    fake_dir = Path("non_existent_deepcad_path_12345")
    adapter = DeepCADAdapter(fake_dir)
    assert not adapter.is_available()
    assert adapter.get_record_count() == 0
    assert adapter.get_record("00020000") is None
    assert list(adapter.iterate_records(limit=5)) == []
