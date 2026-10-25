"""
CAD Asset Schema and Provenance Data Model.
Defines canonical schemas for:
- Asset metadata, formats (STEP vs STL), geometry natures (B-Rep solid vs mesh)
- 4 mechanical usage modes: standard_component_reuse, design_reference,
  custom_geometry_generation, assembly_construction
- Provenance and licensing tracking (respecting usage rights and attribution)
- Physical verification and dimensional metadata
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
import uuid


class CADAssetFormat(str, Enum):
    """File format of the CAD asset."""
    STEP = "step"          # Exact B-Rep boundary representation (editable, solid)
    STP = "stp"            # STEP alias
    STL = "stl"            # Polygonal surface mesh (triangulated, non-editable B-Rep)
    GLTF = "gltf"          # Visualization transmission format
    CADIR_JSON = "cadir"   # Parametric CADIR canonical JSON specification


class GeometryNature(str, Enum):
    """Underlying geometric topology."""
    BREP_SOLID = "brep_solid"          # Exact analytical / NURBS / B-Rep topology with volume
    POLYGONAL_MESH = "polygonal_mesh"  # Faceted surface triangles; cannot apply CAD boolean/features directly
    PARAMETRIC_IR = "parametric_ir"    # Executable procedural CAD feature sequence


class AssetUsageRole(str, Enum):
    """Four distinct mechanical roles for CAD components."""
    STANDARD_COMPONENT_REUSE = "standard_component_reuse"   # Off-the-shelf standard hardware directly imported as STEP
    DESIGN_REFERENCE = "design_reference"                   # Reference geometry/envelope used for dimensional context
    CUSTOM_GEOMETRY_GENERATION = "custom_geometry_generation" # Custom components generated via CadIR / build123d
    ASSEMBLY_CONSTRUCTION = "assembly_construction"         # Multi-component assembly coordinating mates & kinematics


class VerificationStatus(str, Enum):
    """Geometric and dimensional verification status."""
    VERIFIED_BREP = "verified_brep"                      # Valid watertight solid with positive volume
    VERIFIED_WATERTIGHT_MESH = "verified_watertight_mesh" # Valid 2-manifold closed mesh
    UNVERIFIED = "unverified"                            # Ingested metadata without geometry execution check
    FAILED_VALIDATION = "failed_validation"              # Self-intersecting, open shell, or corrupt file


class ProvenanceRecord(BaseModel):
    """Tracks source attribution, licensing terms, and access restrictions."""
    model_config = ConfigDict(extra="ignore")
    source_url: Optional[str] = None
    repository_or_vendor: str = "Local Curated Standard Library"
    license: str = "Apache-2.0"  # SPDX identifier or license title
    author_or_organization: Optional[str] = "Open CAD Engineering Standards"
    terms_restricted: bool = False
    attribution_required: bool = True
    commercial_reuse_allowed: bool = True
    access_protocol: str = "local_filesystem"  # local_filesystem, official_api, public_dataset


class CADAssetMetadata(BaseModel):
    """
    Metadata-backed CAD Asset model.
    Stores complete physical, dimensional, licensing, and topological specifications.
    """
    model_config = ConfigDict(extra="ignore")
    asset_id: str = Field(default_factory=lambda: f"asset_{uuid.uuid4().hex[:8]}")
    name: str
    category: str  # fastener, bearing, gear, flange, pin, housing, manifold, bracket
    subcategory: Optional[str] = None  # e.g., deep_groove_ball_bearing, hex_bolt, spur_gear, dn25_flange
    description: str = ""
    format: CADAssetFormat = CADAssetFormat.STEP
    geometry_nature: GeometryNature = GeometryNature.BREP_SOLID
    file_path: str
    provenance: ProvenanceRecord = Field(default_factory=ProvenanceRecord)
    units: str = "mm"

    # Geometric properties
    bounding_box: Dict[str, float] = Field(
        default_factory=lambda: {"length": 0.0, "width": 0.0, "height": 0.0}
    )
    nominal_dimensions: Dict[str, float] = Field(
        default_factory=dict,
        description="Engineering dimensions: e.g. bore_diameter, outer_diameter, pitch_diameter, thread_size, length"
    )
    mass_kg: Optional[float] = None
    material: Optional[str] = "Structural Steel"

    # Verification telemetry
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    validation_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Computed geometry metrics: volume, face_count, edge_count, is_watertight"
    )

    # Mechanical mating interfaces
    mating_interfaces: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Predefined mating datum points/axes (e.g. bore axis, mounting face, bolt pattern)"
    )
    tags: List[str] = Field(default_factory=list)

    def is_brep_editable(self) -> bool:
        """Returns True only if the asset is true B-Rep solid geometry that can participate in CAD modeling."""
        return self.format in [CADAssetFormat.STEP, CADAssetFormat.STP] and self.geometry_nature == GeometryNature.BREP_SOLID

    def is_mesh_only(self) -> bool:
        """Returns True if the asset is a triangulated mesh (e.g. STL) and must NOT be treated as editable B-Rep."""
        return self.format == CADAssetFormat.STL or self.geometry_nature == GeometryNature.POLYGONAL_MESH
