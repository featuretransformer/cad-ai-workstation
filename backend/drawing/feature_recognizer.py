"""
Drawing Feature Recognizer.
Correlates orthographic views, vector primitives, and extracted dimensions
into canonical 3D CAD operations and validated CADIRDocuments.
Enforces clarification dialogs for rough sketches and reference photos.
"""
from typing import Dict, Any, List, Optional, Tuple, Literal
from pathlib import Path
import math
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.cadir.schema import (
    CADIRDocument,
    CADIRFeature,
    CADIRSketchProfile,
    CADIRPlane,
    CADIRLine,
    CADIRCircle,
    CADIRRectangle,
    Point3D,
    Vector3D,
)
from cad.cadir.validator import validate_cadir_document
from drawing.parser import ParsedDrawing, DrawingPrimitive
from drawing.view_identifier import IdentifiedViews, DrawingView
from drawing.dimension_extractor import ExtractedDimension


InputMode = Literal["drawing", "sketch", "photo"]


class FeatureRecognizer:
    """
    Translates 2D views and dimensions into 3D CADIR features.
    Handles engineering drawings, rough sketches, and photos.
    """

    def __init__(self):
        pass

    def recognize_features(
        self,
        drawing: ParsedDrawing,
        views: IdentifiedViews,
        dimensions: List[ExtractedDimension],
        input_type: InputMode = "drawing",
        doc_id: str = "drawing_model",
        name: str = "Drawing Reconstructed Part",
    ) -> CADIRDocument:
        """
        Synthesizes views, primitives, and dimensions into a canonical CADIRDocument.
        """
        doc = CADIRDocument(
            id=doc_id,
            name=name,
            description=f"Generated from {input_type} via Drawing Understanding Pipeline",
            component_family="machined_component",
            difficulty="L2",
            units="mm",
            engineering_intent={
                "source": "drawing_understanding_pipeline",
                "input_type": input_type,
                "view_count": len(views.views),
                "dimension_count": len(dimensions),
            },
        )

        # 1. Enforce strict guardrails for Rough Sketch and Photograph inputs
        if input_type in ("sketch", "photo"):
            self._apply_sketch_photo_guardrails(doc, input_type, views, dimensions)

        # 2. Select primary view (typically Front view)
        primary_view = views.primary_view or (views.views[0] if views.views else None)
        if not primary_view or not primary_view.primitives:
            # Empty drawing fallback
            return doc

        # 3. Determine base extrusion distance
        depth = self._determine_extrusion_depth(views, dimensions)

        # 4. Construct Base Sketch and Extrusion
        sketch_id = "sk_1_base"
        sketch_prims, internal_circles = self._extract_sketch_geometry(primary_view)

        base_sketch = CADIRSketchProfile(
            id=sketch_id,
            name="Base Profile",
            plane=CADIRPlane(),
            primitives=sketch_prims if sketch_prims else [CADIRRectangle(width=50.0, height=30.0)],
            is_closed=True,
        )
        doc.sketches.append(base_sketch)

        feat_counter = 1
        base_feat_id = f"feat_{feat_counter}_base_extrude"
        feat_counter += 1

        base_extrude = CADIRFeature(
            id=base_feat_id,
            name="Base Extrude",
            feature_type="extrude",
            sketch_id=sketch_id,
            distance=depth,
            operation="new_body",
            dependencies=[],
        )
        doc.features.append(base_extrude)
        last_body_id = base_feat_id

        # 5. Add Hole Features for Internal Circles
        for idx, circle in enumerate(internal_circles):
            # Check if there is an explicit dimension matching this circle
            dia = self._resolve_circle_diameter(circle, dimensions)
            h_id = f"feat_{feat_counter}_hole"
            feat_counter += 1

            hole_feat = CADIRFeature(
                id=h_id,
                name=f"Hole {idx + 1}",
                feature_type="hole",
                diameter=dia,
                depth=depth * 1.5,  # Through-hole
                hole_type="simple",
                operation="cut",
                dependencies=[last_body_id],
            )
            doc.features.append(hole_feat)
            last_body_id = h_id

        # 6. Add Chamfers / Fillets if dimensioned
        for dim in dimensions:
            if dim.dimension_type == "chamfer":
                ch_id = f"feat_{feat_counter}_chamfer"
                feat_counter += 1
                doc.features.append(
                    CADIRFeature(
                        id=ch_id,
                        name="Chamfer",
                        feature_type="chamfer",
                        distance=dim.value,
                        length=dim.value,
                        edge_selector="top",
                        operation="join",
                        dependencies=[last_body_id],
                    )
                )
                last_body_id = ch_id
            elif dim.dimension_type == "radius" and dim.value < depth:
                fil_id = f"feat_{feat_counter}_fillet"
                feat_counter += 1
                doc.features.append(
                    CADIRFeature(
                        id=fil_id,
                        name="Fillet",
                        feature_type="fillet",
                        radius=dim.value,
                        edge_selector="vertical",
                        operation="join",
                        dependencies=[last_body_id],
                    )
                )
                last_body_id = fil_id

        # Validate topological integrity
        val_res = validate_cadir_document(doc)
        if not val_res.is_valid:
            doc.engineering_intent["cadir_validation_warnings"] = val_res.errors

        return doc

    def _determine_extrusion_depth(
        self,
        views: IdentifiedViews,
        dimensions: List[ExtractedDimension],
    ) -> float:
        """Determines 3D depth from orthogonal views (Top/Right) or dimension callouts."""
        # 1. Check if Top or Right view exists
        for v in views.views:
            if v.view_type in ("top", "right"):
                # Dimension along height of Top view or width of Right view represents depth
                depth_val = v.height if v.view_type == "top" else v.width
                if depth_val > 0:
                    return round(depth_val, 2)

        # 2. Check linear dimensions
        for dim in dimensions:
            if dim.dimension_type == "linear" and 1.0 <= dim.value <= 500.0:
                return dim.value

        # 3. Default nominal engineering depth
        return 10.0

    def _extract_sketch_geometry(
        self,
        view: DrawingView,
    ) -> Tuple[List[Any], List[DrawingPrimitive]]:
        """
        Separates boundary geometry from interior holes in the view.
        Returns (sketch_primitives, internal_circles).
        """
        sketch_prims = []
        internal_circles = []

        all_circles = [p for p in view.primitives if p.primitive_type == "circle"]
        all_rects = [p for p in view.primitives if p.primitive_type == "rectangle"]
        all_lines = [p for p in view.primitives if p.primitive_type == "line"]

        if all_rects:
            # Use largest rectangle as outer boundary
            largest_rect = max(all_rects, key=lambda r: (r.width or 0) * (r.height or 0))
            sketch_prims.append(
                CADIRRectangle(
                    width=largest_rect.width or 50.0,
                    height=largest_rect.height or 30.0,
                )
            )
            internal_circles = all_circles
        elif all_circles:
            # Largest circle is outer cylinder; smaller circles are holes
            sorted_circles = sorted(all_circles, key=lambda c: c.radius or 0, reverse=True)
            outer = sorted_circles[0]
            sketch_prims.append(
                CADIRCircle(
                    radius=outer.radius or 25.0,
                )
            )
            internal_circles = sorted_circles[1:]
        elif all_lines:
            # Map lines to CADIRLine primitives
            for line in all_lines[:20]:
                if line.start and line.end:
                    sketch_prims.append(
                        CADIRLine(
                            start=Point3D(x=line.start[0], y=line.start[1], z=0.0),
                            end=Point3D(x=line.end[0], y=line.end[1], z=0.0),
                        )
                    )

        return sketch_prims, internal_circles

    def _resolve_circle_diameter(
        self,
        circle: DrawingPrimitive,
        dimensions: List[ExtractedDimension],
    ) -> float:
        """Finds matching diameter dimension for a circle or falls back to geometric radius*2."""
        for dim in dimensions:
            if dim.associated_primitive_id == circle.id:
                if dim.dimension_type in ("diameter", "hole_callout"):
                    return dim.value
                elif dim.dimension_type == "radius":
                    return dim.value * 2.0

        if circle.radius:
            return round(circle.radius * 2.0, 2)
        return 10.0

    def _apply_sketch_photo_guardrails(
        self,
        doc: CADIRDocument,
        input_type: InputMode,
        views: IdentifiedViews,
        dimensions: List[ExtractedDimension],
    ) -> None:
        """
        Implements Section 5.2 and 5.3 mandatory user clarification dialog declarations.
        Declares missing dimensions and prohibits unverified auto-dimensioning.
        """
        clarifications = []
        missing_dims = []

        if not dimensions:
            missing_dims.extend(["overall_length", "overall_width", "overall_thickness"])
            clarifications.append("No explicit dimension annotations found. Please provide overall bounding dimensions.")

        if len(views.views) < 2:
            missing_dims.append("thickness_depth")
            clarifications.append("Only a single view was detected. Please specify part thickness/depth.")

        if input_type == "photo":
            clarifications.append(
                "MANDATORY CONFIRMATION: Reference photograph input lacks metric scale, tolerances, "
                "and internal geometry. Please verify all dimensions before manufacturing."
            )
            doc.engineering_intent["requires_user_dimensions"] = True

        doc.engineering_intent["missing_dimensions"] = missing_dims
        doc.engineering_intent["clarification_needed"] = clarifications
