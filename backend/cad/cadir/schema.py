"""
CAD Intermediate Representation (CADIR) — Canonical Schema
Defines the strict Pydantic v2 models representing parametric mechanical components,
sketch profiles, 3D operations, explicit feature dependencies, and engineering intent.
"""
from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, model_validator
import json


class Point3D(BaseModel):
    """3D Cartesian Point with parametric coordinates."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class Vector3D(BaseModel):
    """3D Directional Vector."""
    x: float = 0.0
    y: float = 0.0
    z: float = 1.0


class CADIRPlane(BaseModel):
    """Construction plane for 2D sketches."""
    origin: Point3D = Field(default_factory=Point3D)
    normal: Vector3D = Field(default_factory=lambda: Vector3D(x=0.0, y=0.0, z=1.0))
    x_axis: Vector3D = Field(default_factory=lambda: Vector3D(x=1.0, y=0.0, z=0.0))


# ─── 2D Sketch Primitives ──────────────────────────────────────────────────────────

class CADIRLine(BaseModel):
    primitive_type: Literal["line"] = "line"
    start: Point3D
    end: Point3D


class CADIRArc(BaseModel):
    primitive_type: Literal["arc"] = "arc"
    start: Point3D
    end: Point3D
    center: Optional[Point3D] = None
    radius: Optional[float] = None


class CADIRCircle(BaseModel):
    primitive_type: Literal["circle"] = "circle"
    center: Point3D = Field(default_factory=Point3D)
    radius: float = Field(gt=0.0, description="Radius must be strictly positive")


class CADIRRectangle(BaseModel):
    primitive_type: Literal["rectangle"] = "rectangle"
    width: float = Field(gt=0.0, description="Width along local X")
    height: float = Field(gt=0.0, description="Height along local Y")
    center: Point3D = Field(default_factory=Point3D)


class CADIRPolygon(BaseModel):
    primitive_type: Literal["polygon"] = "polygon"
    points: List[Point3D] = Field(min_length=3, description="Minimum 3 vertices for a polygon")


class CADIRSlot(BaseModel):
    primitive_type: Literal["slot"] = "slot"
    length: float = Field(gt=0.0)
    width: float = Field(gt=0.0)
    center: Point3D = Field(default_factory=Point3D)


CADIRSketchPrimitive = Union[
    CADIRLine, CADIRArc, CADIRCircle, CADIRRectangle, CADIRPolygon, CADIRSlot
]


class CADIRSketchProfile(BaseModel):
    """Closed or bounded planar profile comprised of 2D primitives."""
    id: str
    name: str = ""
    plane: CADIRPlane = Field(default_factory=CADIRPlane)
    primitives: List[CADIRSketchPrimitive] = Field(default_factory=list)
    is_closed: bool = True
    inner_loops: List[List[CADIRSketchPrimitive]] = Field(
        default_factory=list, description="Internal closed boundaries (holes/islands)"
    )
    constraints: List[Dict[str, Any]] = Field(default_factory=list)


# ─── 3D Features & Operations ──────────────────────────────────────────────────────

FeatureType = Literal[
    "box",
    "cylinder",
    "sphere",
    "extrude",
    "revolve",
    "hole",
    "pocket",
    "fillet",
    "chamfer",
    "linear_pattern",
    "polar_pattern",
    "mirror",
    "boolean_union",
    "boolean_cut",
    "boolean_intersect",
]

BooleanOperationType = Literal["new_body", "join", "cut", "intersect"]


class CADIRFeature(BaseModel):
    """
    Parametric feature node in the CAD construction tree.
    Explicitly tracks dependencies on preceding features.
    """
    id: str = Field(description="Unique identifier (e.g. 'f1_base_box')")
    name: str = ""
    feature_type: FeatureType
    dependencies: List[str] = Field(
        default_factory=list,
        description="IDs of predecessor features this feature relies upon",
    )
    operation: BooleanOperationType = "new_body"
    target_geometry: Optional[str] = Field(
        default=None,
        description="Reference to targeted parent feature, edge group, or face",
    )
    suppressed: bool = False

    # 3D Primitive parameters
    length: Optional[float] = Field(default=None, gt=0.0)
    width: Optional[float] = Field(default=None, gt=0.0)
    height: Optional[float] = Field(default=None, gt=0.0)
    radius: Optional[float] = Field(default=None, gt=0.0)
    center: Optional[Point3D] = None
    axis: Optional[Vector3D] = None

    # Sketch-based 3D parameters
    sketch_id: Optional[str] = None
    distance: Optional[float] = Field(default=None, gt=0.0)
    depth: Optional[float] = Field(default=None, gt=0.0)
    angle: Optional[float] = None
    taper_angle: float = 0.0
    symmetric: bool = False

    # Hole parameters
    diameter: Optional[float] = Field(default=None, gt=0.0)
    hole_type: Literal["simple", "counterbore", "countersink"] = "simple"
    cbore_diameter: Optional[float] = None
    cbore_depth: Optional[float] = None
    csink_diameter: Optional[float] = None
    csink_angle: Optional[float] = None
    position: Optional[Point3D] = None
    direction: Optional[Vector3D] = None

    # Edge modification parameters (Fillet / Chamfer)
    edge_selector: str = Field(
        default="all",
        description="Rule/query for target edges (e.g. 'all', 'top', 'bottom', 'vertical', 'edges_at_z_max')",
    )

    # Pattern / Transform parameters
    count: Optional[int] = Field(default=None, ge=1)
    spacing: Optional[float] = None
    mirror_plane: Optional[CADIRPlane] = None

    # Boolean parameters
    tool_feature_id: Optional[str] = None

    # Generic parameter dictionary for extended flexibility
    params: Dict[str, Any] = Field(default_factory=dict)


# ─── CADIR Document Root ───────────────────────────────────────────────────────────

class CADIRDocument(BaseModel):
    """
    Canonical CAD Intermediate Representation (CADIR) Document.
    Serves as the deterministic bridge between AI intent and build123d construction.
    """
    schema_version: str = "1.0.0"
    id: str
    name: str
    description: str = ""
    component_family: Optional[str] = Field(
        default=None,
        description="Component classification (e.g. 'bearing_housing', 'shaft', 'mounting_plate', 'bracket')",
    )
    difficulty: Optional[str] = Field(
        default=None, description="Complexity tier: L1, L2, L3, L4, L5"
    )
    units: Literal["mm", "cm", "m", "in"] = "mm"
    material: str = "Structural Steel"

    parameters: Dict[str, float] = Field(
        default_factory=dict,
        description="Global parametric design variables referenced by features",
    )
    engineering_intent: Dict[str, Any] = Field(
        default_factory=dict,
        description="Design intent: requirements, loads, factor of safety, functional constraints",
    )
    sketches: List[CADIRSketchProfile] = Field(
        default_factory=list, description="2D sketch profiles"
    )
    features: List[CADIRFeature] = Field(
        default_factory=list, description="Ordered parametric feature sequence"
    )
    validation_requirements: Dict[str, Any] = Field(
        default_factory=dict,
        description="Engineering verification criteria (e.g. max_mass, min_fos, envelope)",
    )

    def get_feature(self, feature_id: str) -> Optional[CADIRFeature]:
        for f in self.features:
            if f.id == feature_id:
                return f
        return None

    def get_sketch(self, sketch_id: str) -> Optional[CADIRSketchProfile]:
        for s in self.sketches:
            if s.id == sketch_id:
                return s
        return None

    def get_feature_ids(self) -> List[str]:
        return [f.id for f in self.features]

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        return {f.id: list(f.dependencies) for f in self.features}

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "CADIRDocument":
        return cls.model_validate_json(json_str)
