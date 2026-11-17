"""
CAD Intermediate Representation (CADIR) Module
Canonical structured design representation between AI reasoning and parametric CAD kernels.
"""
from .schema import (
    Point3D,
    Vector3D,
    CADIRPlane,
    CADIRLine,
    CADIRArc,
    CADIRCircle,
    CADIRRectangle,
    CADIRPolygon,
    CADIRSlot,
    CADIRSketchPrimitive,
    CADIRSketchProfile,
    CADIRFeature,
    CADIRDocument,
    FeatureType,
    BooleanOperationType,
)
from .validator import (
    CADIRValidationResult,
    validate_cadir_document,
)
from .interpreter import (
    generate_build123d_code,
    interpret_and_execute,
)

__all__ = [
    "Point3D",
    "Vector3D",
    "CADIRPlane",
    "CADIRLine",
    "CADIRArc",
    "CADIRCircle",
    "CADIRRectangle",
    "CADIRPolygon",
    "CADIRSlot",
    "CADIRSketchPrimitive",
    "CADIRSketchProfile",
    "CADIRFeature",
    "CADIRDocument",
    "FeatureType",
    "BooleanOperationType",
    "CADIRValidationResult",
    "validate_cadir_document",
    "generate_build123d_code",
    "interpret_and_execute",
]
