"""
Unit tests for Drawing Understanding Pipeline (Phase 6):
DrawingParser, ViewIdentifier, DimensionExtractor, and FeatureRecognizer.
"""
import pytest
from pathlib import Path
import sys

# Ensure backend root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from drawing.parser import DrawingParser, DrawingPrimitive, TextAnnotation
from drawing.view_identifier import ViewIdentifier
from drawing.dimension_extractor import DimensionExtractor
from drawing.feature_recognizer import FeatureRecognizer
from cad.cadir.schema import CADIRDocument
from cad.cadir.validator import validate_cadir_document


# ─── DrawingParser Tests ──────────────────────────────────────────────────────────────

def test_svg_drawing_parsing():
    svg_content = """
    <svg width="400" height="300" viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
        <rect x="50" y="50" width="100" height="60" fill="none" stroke="black" />
        <circle cx="100" cy="80" r="15" fill="none" stroke="black" />
        <line x1="50" y1="50" x2="150" y2="50" stroke="black" />
        <text x="100" y="40" font-size="12">100 mm</text>
        <text x="100" y="80" font-size="12">Ø30</text>
    </svg>
    """
    parser = DrawingParser()
    parsed = parser.parse(svg_content)

    assert parsed.source_format == "svg"
    assert parsed.width == 400.0
    assert parsed.height == 300.0
    assert len(parsed.primitives) >= 3

    # Check for rect and circle
    types = [p.primitive_type for p in parsed.primitives]
    assert "rectangle" in types
    assert "circle" in types

    # Check for text annotations
    assert len(parsed.text_elements) == 2
    texts = [t.text for t in parsed.text_elements]
    assert "100 mm" in texts
    assert "Ø30" in texts


def test_raster_drawing_parsing(tmp_path):
    import numpy as np
    import cv2

    # Create a synthetic 200x200 image with a white background and black circle + line
    img = np.ones((200, 200, 3), dtype=np.uint8) * 255
    cv2.circle(img, (100, 100), 30, (0, 0, 0), 2)
    cv2.line(img, (20, 20), (180, 20), (0, 0, 0), 2)

    img_path = tmp_path / "test_drawing.png"
    cv2.imwrite(str(img_path), img)

    parser = DrawingParser()
    parsed = parser.parse(img_path)

    assert parsed.source_format == "raster"
    assert parsed.width == 200.0
    assert parsed.height == 200.0
    assert len(parsed.primitives) > 0


# ─── ViewIdentifier Tests ─────────────────────────────────────────────────────────────

def test_view_identifier_label_based():
    svg_content = """
    <svg width="600" height="400">
        <!-- Front View -->
        <rect x="50" y="200" width="80" height="50" />
        <circle cx="90" cy="225" r="10" />
        <text x="90" y="270">FRONT</text>

        <!-- Top View -->
        <rect x="50" y="50" width="80" height="40" />
        <text x="90" y="110">TOP</text>

        <!-- Right View -->
        <rect x="200" y="200" width="40" height="50" />
        <text x="220" y="270">RIGHT</text>
    </svg>
    """
    parser = DrawingParser()
    parsed = parser.parse(svg_content)

    identifier = ViewIdentifier()
    views = identifier.identify_views(parsed)

    assert len(views.views) >= 2
    view_types = [v.view_type for v in views.views]
    assert "front" in view_types
    assert "top" in view_types


def test_view_identifier_fallback_single():
    svg_content = """
    <svg width="200" height="200">
        <circle cx="100" cy="100" r="40" />
    </svg>
    """
    parser = DrawingParser()
    parsed = parser.parse(svg_content)

    identifier = ViewIdentifier()
    views = identifier.identify_views(parsed)

    assert len(views.views) == 1
    assert views.primary_view is not None


# ─── DimensionExtractor Tests ─────────────────────────────────────────────────────────

def test_dimension_extractor():
    texts = [
        TextAnnotation(id="t1", text="100 ± 0.05", x=50.0, y=20.0),
        TextAnnotation(id="t2", text="Ø25.0", x=100.0, y=100.0),
        TextAnnotation(id="t3", text="R5.0", x=150.0, y=80.0),
        TextAnnotation(id="t4", text="4x Ø8.5", x=120.0, y=120.0),
        TextAnnotation(id="t5", text="2x45°", x=180.0, y=180.0),
    ]

    prims = [
        DrawingPrimitive(id="p_circle", primitive_type="circle", center=(100.0, 100.0), radius=12.5, bbox=(87.5, 87.5, 112.5, 112.5)),
        DrawingPrimitive(id="p_rect", primitive_type="rectangle", start=(0.0, 0.0), width=100.0, height=50.0, bbox=(0.0, 0.0, 100.0, 50.0)),
    ]

    extractor = DimensionExtractor()
    dims = extractor.extract_dimensions(texts, primitives=prims)

    assert len(dims) == 5

    dim_map = {d.dimension_type: d for d in dims}
    assert "linear" in dim_map
    assert dim_map["linear"].value == 100.0
    assert dim_map["linear"].tolerance == "±0.05"

    assert "diameter" in dim_map
    assert dim_map["diameter"].value == 25.0
    assert dim_map["diameter"].associated_primitive_id == "p_circle"

    assert "radius" in dim_map
    assert dim_map["radius"].value == 5.0

    assert "hole_callout" in dim_map
    assert dim_map["hole_callout"].value == 8.5
    assert dim_map["hole_callout"].count == 4

    assert "chamfer" in dim_map
    assert dim_map["chamfer"].value == 2.0


# ─── FeatureRecognizer Tests ──────────────────────────────────────────────────────────

def test_feature_recognizer_engineering_drawing():
    svg_content = """
    <svg width="400" height="300">
        <!-- Front View Plate with Center Hole -->
        <rect x="50" y="50" width="120" height="80" />
        <circle cx="110" cy="90" r="15" />
        <text x="110" y="30">120 mm</text>
        <text x="110" y="90">Ø30</text>
        <text x="160" y="50">2x45°</text>
    </svg>
    """
    parser = DrawingParser()
    parsed = parser.parse(svg_content)

    v_identifier = ViewIdentifier()
    views = v_identifier.identify_views(parsed)

    dim_extractor = DimensionExtractor()
    dims = dim_extractor.extract_dimensions(parsed.text_elements, primitives=parsed.primitives)

    recognizer = FeatureRecognizer()
    doc = recognizer.recognize_features(
        drawing=parsed,
        views=views,
        dimensions=dims,
        input_type="drawing",
        doc_id="plate_with_hole",
        name="Mounting Plate",
    )

    assert isinstance(doc, CADIRDocument)
    assert len(doc.features) >= 2

    # Feature 1: Base Extrude
    assert doc.features[0].feature_type == "extrude"
    assert doc.features[0].distance > 0

    # Feature 2: Hole
    assert doc.features[1].feature_type == "hole"
    assert doc.features[1].diameter == 30.0
    assert doc.features[1].dependencies == [doc.features[0].id]

    # Validate topological integrity
    val_res = validate_cadir_document(doc)
    assert val_res.is_valid
    assert len(val_res.errors) == 0


def test_feature_recognizer_sketch_photo_guardrails():
    svg_content = """<svg width="200" height="200"><circle cx="100" cy="100" r="30" /></svg>"""
    parser = DrawingParser()
    parsed = parser.parse(svg_content)

    v_identifier = ViewIdentifier()
    views = v_identifier.identify_views(parsed)
    dim_extractor = DimensionExtractor()
    dims = dim_extractor.extract_dimensions(parsed.text_elements)

    recognizer = FeatureRecognizer()

    # 1. Test Rough Sketch mode
    doc_sketch = recognizer.recognize_features(
        drawing=parsed,
        views=views,
        dimensions=dims,
        input_type="sketch",
        doc_id="sketch_doc",
    )
    assert "clarification_needed" in doc_sketch.engineering_intent
    assert len(doc_sketch.engineering_intent["clarification_needed"]) > 0

    # 2. Test Reference Photo mode
    doc_photo = recognizer.recognize_features(
        drawing=parsed,
        views=views,
        dimensions=dims,
        input_type="photo",
        doc_id="photo_doc",
    )
    assert doc_photo.engineering_intent.get("requires_user_dimensions") is True
    assert any("MANDATORY CONFIRMATION" in c for c in doc_photo.engineering_intent["clarification_needed"])
