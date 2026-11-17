"""
CAD Intermediate Representation (CADIR) — Canonical Schema
Defines the strict Pydantic v2 models representing parametric mechanical components,
sketch profiles, 3D operations, explicit feature dependencies, and engineering intent.
"""
from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict
import json
import uuid


class Point3D(BaseModel):
    """3D Cartesian Point with parametric coordinates."""
    model_config = ConfigDict(extra="ignore")
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @model_validator(mode="before")
    @classmethod
    def parse_coords(cls, data):
        if isinstance(data, (list, tuple)):
            return {
                "x": float(data[0]) if len(data) > 0 else 0.0,
                "y": float(data[1]) if len(data) > 1 else 0.0,
                "z": float(data[2]) if len(data) > 2 else 0.0,
            }
        return data


class Vector3D(BaseModel):
    """3D Directional Vector."""
    model_config = ConfigDict(extra="ignore")
    x: float = 0.0
    y: float = 0.0
    z: float = 1.0

    @model_validator(mode="before")
    @classmethod
    def parse_vector(cls, data):
        if isinstance(data, (list, tuple)):
            return {
                "x": float(data[0]) if len(data) > 0 else 0.0,
                "y": float(data[1]) if len(data) > 1 else 0.0,
                "z": float(data[2]) if len(data) > 2 else 1.0,
            }
        return data


class CADIRPlane(BaseModel):
    """Construction plane for 2D sketches."""
    model_config = ConfigDict(extra="ignore")
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
    "sweep",
    "loft",
    "shell",
    "rib",
    "thread",
    "linear_pattern",
    "polar_pattern",
    "mirror",
    "boolean_union",
    "boolean_cut",
    "boolean_intersect",
    "regular_polygon",
    "groove",
    "counterbore_hole",
    "countersink_hole",
]

BooleanOperationType = Literal["new_body", "join", "cut", "intersect"]


class CADIRFeature(BaseModel):
    """
    Parametric feature node in the CAD construction tree.
    Explicitly tracks dependencies on preceding features.
    """
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: f"f_{uuid.uuid4().hex[:6]}")
    name: str = ""
    description: str = ""
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
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    center: Optional[Point3D] = None
    axis: Optional[Vector3D] = None

    # Sketch-based 3D parameters
    sketch_id: Optional[str] = None
    distance: Optional[float] = None
    depth: Optional[float] = None
    angle: Optional[float] = None
    taper_angle: float = 0.0
    symmetric: bool = False

    # Sweep parameters
    path_sketch_id: Optional[str] = None
    path_feature_id: Optional[str] = None

    # Loft parameters
    section_sketch_ids: List[str] = Field(default_factory=list)
    ruled: bool = False

    # Shell parameters
    thickness: Optional[float] = None
    opening_faces: List[str] = Field(
        default_factory=list,
        description="Faces to remove for hollow shell (e.g. ['top'], ['bottom'])"
    )

    # Rib parameters
    rib_thickness: Optional[float] = None

    # Thread parameters
    pitch: Optional[float] = None
    thread_diameter: Optional[float] = None
    thread_length: Optional[float] = None
    thread_type: Literal["metric", "unified", "acme", "schematic"] = "metric"

    # Hole parameters
    diameter: Optional[float] = None
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

    # Regular Polygon / Prism parameters
    side_count: Optional[int] = Field(default=6, ge=3)

    # Groove parameters
    outer_radius: Optional[float] = None
    inner_radius: Optional[float] = None
    groove_width: Optional[float] = None

    # Pattern / Transform parameters
    count: Optional[int] = Field(default=None, ge=1)
    spacing: Optional[float] = None
    mirror_plane: Optional[CADIRPlane] = None

    # Boolean parameters
    tool_feature_id: Optional[str] = None

    # Generic parameter dictionary for extended flexibility
    params: Dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "length", "width", "height", "radius", "distance", "depth", "diameter",
        "cbore_diameter", "cbore_depth", "csink_diameter", "csink_angle",
        "thickness", "pitch", "thread_diameter", "thread_length", "rib_thickness",
        mode="before"
    )
    @classmethod
    def coerce_positive_numeric(cls, v):
        """Ensure positive numeric values; raise ValueError for non-positive numbers."""
        if v is None:
            return None
        try:
            val = float(v)
            if val <= 0:
                raise ValueError(f"Value must be strictly positive, got {val}")
            return val
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid positive numeric value: {v}") from e

    @model_validator(mode="before")
    @classmethod
    def sync_position_and_center(cls, data):
        if isinstance(data, dict):
            # Sync center and position
            if "position" in data and ("center" not in data or data["center"] is None):
                data["center"] = data["position"]
            elif "center" in data and ("position" not in data or data["position"] is None):
                data["position"] = data["center"]
        return data


# ─── CADIR Document Root ───────────────────────────────────────────────────────────

class CADIRDocument(BaseModel):
    """
    Canonical CAD Intermediate Representation (CADIR) Document.
    Serves as the deterministic bridge between AI intent and build123d construction.
    """
    model_config = ConfigDict(extra="ignore")
    schema_version: str = "1.0.0"
    id: str = Field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:8]}")
    name: str = "Mechanical Component"
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

    parameters: Dict[str, Any] = Field(
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
