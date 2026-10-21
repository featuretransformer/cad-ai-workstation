"""
CAD Assembly Schema.
Defines canonical data structures for multi-component mechanical assemblies:
- Placement3D: 3D spatial transforms (translations + Euler rotations)
- MatingInterface: kinematic and contact constraints between components
- ComponentSpec: individual part specification with parametric CADIR bindings
- AssemblySpec: complete system-level assembly architecture, parameters, and BOM
"""
from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator
import uuid
import json

from cad.cadir.schema import Point3D, Vector3D, CADIRDocument


class Placement3D(BaseModel):
    """
    Spatial positioning and orientation of a component or instance in 3D assembly space.
    Translation in units (mm), Euler rotation angles (rx, ry, rz) in degrees.
    """
    model_config = ConfigDict(extra="ignore")
    translation: Point3D = Field(default_factory=Point3D)
    rotation: Vector3D = Field(
        default_factory=lambda: Vector3D(x=0.0, y=0.0, z=0.0),
        description="Euler rotation angles (deg) around X, Y, Z axes"
    )
    anchor: Optional[Point3D] = Field(
        default=None,
        description="Local origin/datum point within the component"
    )

    @classmethod
    def from_xyz_rxyz(
        cls,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        rx: float = 0.0,
        ry: float = 0.0,
        rz: float = 0.0,
    ) -> "Placement3D":
        return cls(
            translation=Point3D(x=x, y=y, z=z),
            rotation=Vector3D(x=rx, y=ry, z=rz),
        )


MatingType = Literal[
    "rigid",
    "revolute",
    "prismatic",
    "cylindrical",
    "planar_contact",
    "coaxial",
    "fastener",
    "slot",
    "gear_mesh",
    "custom",
]


class MatingInterface(BaseModel):
    """
    Physical, kinematic, or contact relationship between two components.
    Defines joint types, nominal clearances, offsets, and motion limits.
    """
    model_config = ConfigDict(extra="ignore")
    interface_id: str = Field(default_factory=lambda: f"mate_{uuid.uuid4().hex[:6]}")
    name: str = ""
    mate_type: MatingType = "rigid"
    parent_component_id: str = Field(..., description="ID of primary/reference component")
    child_component_id: str = Field(..., description="ID of constrained/mounted component")
    parent_datum: str = Field(default="", description="Reference feature or datum on parent")
    child_datum: str = Field(default="", description="Target feature or datum on child")
    clearance: float = Field(default=0.2, description="Nominal functional clearance (mm)")
    offset: float = Field(default=0.0, description="Offset along joint axis (mm)")
    axis: Optional[Vector3D] = Field(default=None, description="Axis of motion or alignment")
    limits: Dict[str, float] = Field(default_factory=dict, description="e.g. min_angle, max_angle, stroke")
    description: str = ""


class ComponentSpec(BaseModel):
    """
    Specification for a single mechanical component within an assembly.
    Can represent single or repeated parts (e.g. 3 fingers, 4 bolts).
    """
    model_config = ConfigDict(extra="ignore")
    component_id: str = Field(default_factory=lambda: f"comp_{uuid.uuid4().hex[:6]}")
    name: str
    role: str = Field(
        ...,
        description="Mechanical function: mounting_plate, finger, pivot_pin, linkage, actuator, shaft, housing, etc."
    )
    quantity: int = Field(default=1, ge=1)
    cadir_document: Optional[CADIRDocument] = Field(
        default=None,
        description="Full parametric CADIR document defining component geometry"
    )
    base_placement: Placement3D = Field(default_factory=Placement3D)
    instance_placements: List[Placement3D] = Field(
        default_factory=list,
        description="Explicit placements for each instance when quantity > 1"
    )
    material: str = "Structural Steel"
    motion_type: Literal["fixed", "revolute", "linear", "floating"] = "fixed"
    parameters: Dict[str, float] = Field(default_factory=dict)
    description: str = ""

    @model_validator(mode="after")
    def populate_instance_placements(self) -> "ComponentSpec":
        """Ensure instance_placements has at least self.quantity entries."""
        if not self.instance_placements:
            self.instance_placements = [self.base_placement for _ in range(self.quantity)]
        elif len(self.instance_placements) < self.quantity:
            last = self.instance_placements[-1]
            self.instance_placements.extend([last] * (self.quantity - len(self.instance_placements)))
        return self


class AssemblySpec(BaseModel):
    """
    Canonical Multi-Component Mechanical Assembly Specification.
    Defines the shared engineering truth across components, interfaces, and placements.
    """
    model_config = ConfigDict(extra="ignore")
    schema_version: str = "1.0.0"
    id: str = Field(default_factory=lambda: f"asm_{uuid.uuid4().hex[:8]}")
    name: str = "Mechanical Assembly"
    description: str = ""
    assembly_family: Optional[str] = Field(
        default=None,
        description="Classification: gripper, gearbox, caster_wheel, robotic_link, clamp, etc."
    )
    units: Literal["mm", "cm", "m", "in"] = "mm"
    global_parameters: Dict[str, float] = Field(
        default_factory=dict,
        description="Global parameters driving component dimensions and spacing"
    )
    components: List[ComponentSpec] = Field(default_factory=list)
    mating_interfaces: List[MatingInterface] = Field(default_factory=list)
    validation_requirements: Dict[str, Any] = Field(
        default_factory=dict,
        description="Interference limits, minimum clearances, mass envelopes"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Engineering assumptions made during decomposition"
    )
    unresolved_parameters: List[str] = Field(
        default_factory=list,
        description="Parameters defaulted or needing user confirmation"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_component(self, component_id: str) -> Optional[ComponentSpec]:
        for comp in self.components:
            if comp.component_id == component_id:
                return comp
        return None

    def get_bom(self) -> List[Dict[str, Any]]:
        """Generate Bill of Materials summary."""
        bom = []
        for comp in self.components:
            bom.append({
                "component_id": comp.component_id,
                "name": comp.name,
                "role": comp.role,
                "quantity": comp.quantity,
                "material": comp.material,
                "motion_type": comp.motion_type,
            })
        return bom

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "AssemblySpec":
        return cls.model_validate_json(json_str)
