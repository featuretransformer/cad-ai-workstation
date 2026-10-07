"""
Drawing Understanding Pipeline.
Translates 2D engineering drawings, rough sketches, and reference photos
into canonical CADIR parametric models via deterministic vector parsing,
multi-view decomposition, dimension extraction, and feature recognition.
"""
from .parser import DrawingParser, ParsedDrawing, DrawingPrimitive, TextAnnotation
from .view_identifier import ViewIdentifier, DrawingView, IdentifiedViews
from .dimension_extractor import DimensionExtractor, ExtractedDimension
from .feature_recognizer import FeatureRecognizer

__all__ = [
    "DrawingParser",
    "ParsedDrawing",
    "DrawingPrimitive",
    "TextAnnotation",
    "ViewIdentifier",
    "DrawingView",
    "IdentifiedViews",
    "DimensionExtractor",
    "ExtractedDimension",
    "FeatureRecognizer",
]
