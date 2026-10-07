"""
Drawing Multi-View Identifier.
Decomposes 2D engineering drawings into canonical orthographic projections:
Front, Top, Right, and Isometric views using spatial clustering and label heuristics.
"""
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from drawing.parser import ParsedDrawing, DrawingPrimitive, TextAnnotation


class DrawingView(BaseModel):
    """Segmented view region from an engineering drawing."""
    view_type: str = Field(description="'front', 'top', 'right', 'isometric', 'single'")
    bbox: Tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
    primitives: List[DrawingPrimitive] = Field(default_factory=list)
    text_elements: List[TextAnnotation] = Field(default_factory=list)
    width: float = 0.0
    height: float = 0.0


class IdentifiedViews(BaseModel):
    """Collection of identified views with primary projection reference."""
    views: List[DrawingView] = Field(default_factory=list)
    primary_view: Optional[DrawingView] = None
    projection_system: str = "third_angle"  # 'third_angle' or 'first_angle'


class ViewIdentifier:
    """
    Identifies and separates multiple orthographic projection views in a 2D drawing.
    """

    VIEW_KEYWORDS = {
        "front": ["front", "elevation", "front view"],
        "top": ["top", "plan", "top view"],
        "right": ["right", "side", "right view", "profile"],
        "isometric": ["isometric", "iso", "3d", "axonometric"],
    }

    def __init__(self):
        pass

    def identify_views(self, drawing: ParsedDrawing) -> IdentifiedViews:
        """
        Decomposes the parsed drawing into distinct projection views.
        """
        if not drawing.primitives:
            single = DrawingView(
                view_type="single",
                bbox=(0.0, 0.0, drawing.width, drawing.height),
                width=drawing.width,
                height=drawing.height,
            )
            return IdentifiedViews(views=[single], primary_view=single)

        # 1. Attempt label-based classification
        labeled_views = self._identify_by_labels(drawing)
        if labeled_views and len(labeled_views) >= 2:
            primary = next((v for v in labeled_views if v.view_type == "front"), labeled_views[0])
            return IdentifiedViews(views=labeled_views, primary_view=primary)

        # 2. Quadrant / Multi-Cluster Spatial Decomposition
        spatial_views = self._identify_by_quadrants(drawing)
        if spatial_views and len(spatial_views) >= 2:
            primary = next((v for v in spatial_views if v.view_type == "front"), spatial_views[0])
            return IdentifiedViews(views=spatial_views, primary_view=primary)

        # 3. Fallback: single view
        min_x = min(p.bbox[0] for p in drawing.primitives)
        min_y = min(p.bbox[1] for p in drawing.primitives)
        max_x = max(p.bbox[2] for p in drawing.primitives)
        max_y = max(p.bbox[3] for p in drawing.primitives)

        single = DrawingView(
            view_type="front",
            bbox=(min_x, min_y, max_x, max_y),
            width=max_x - min_x,
            height=max_y - min_y,
            primitives=list(drawing.primitives),
            text_elements=list(drawing.text_elements),
        )
        return IdentifiedViews(views=[single], primary_view=single)

    def _identify_by_labels(self, drawing: ParsedDrawing) -> Optional[List[DrawingView]]:
        """Checks for textual view labels (e.g. 'FRONT', 'TOP', 'RIGHT')."""
        labels_found: Dict[str, TextAnnotation] = {}
        for txt in drawing.text_elements:
            t_clean = txt.text.lower().strip()
            for v_type, kws in self.VIEW_KEYWORDS.items():
                if any(kw == t_clean or f"{kw} view" in t_clean for kw in kws):
                    labels_found[v_type] = txt

        if len(labels_found) < 2:
            return None

        # Build view boxes around label anchors
        views = []
        for v_type, label in labels_found.items():
            # Filter primitives within proximity of label
            v_prims = [
                p for p in drawing.primitives
                if abs(p.bbox[0] - label.x) < drawing.width * 0.4 and abs(p.bbox[1] - label.y) < drawing.height * 0.4
            ]
            if v_prims:
                min_x = min(p.bbox[0] for p in v_prims)
                min_y = min(p.bbox[1] for p in v_prims)
                max_x = max(p.bbox[2] for p in v_prims)
                max_y = max(p.bbox[3] for p in v_prims)
                views.append(
                    DrawingView(
                        view_type=v_type,
                        bbox=(min_x, min_y, max_x, max_y),
                        width=max_x - min_x,
                        height=max_y - min_y,
                        primitives=v_prims,
                    )
                )

        return views if len(views) >= 2 else None

    def _identify_by_quadrants(self, drawing: ParsedDrawing) -> Optional[List[DrawingView]]:
        """
        Splits drawing along centerlines if primitives naturally cluster into
        distinct quadrants (e.g. standard 3-view or 4-view drawing sheet).
        """
        all_x = [p.bbox[0] for p in drawing.primitives] + [p.bbox[2] for p in drawing.primitives]
        all_y = [p.bbox[1] for p in drawing.primitives] + [p.bbox[3] for p in drawing.primitives]
        if not all_x or not all_y:
            return None

        mid_x = (min(all_x) + max(all_x)) / 2.0
        mid_y = (min(all_y) + max(all_y)) / 2.0

        q_prims = {
            "top_left": [],
            "top_right": [],
            "bottom_left": [],
            "bottom_right": [],
        }

        for p in drawing.primitives:
            px = (p.bbox[0] + p.bbox[2]) / 2.0
            py = (p.bbox[1] + p.bbox[3]) / 2.0

            if px <= mid_x and py <= mid_y:
                q_prims["top_left"].append(p)
            elif px > mid_x and py <= mid_y:
                q_prims["top_right"].append(p)
            elif px <= mid_x and py > mid_y:
                q_prims["bottom_left"].append(p)
            else:
                q_prims["bottom_right"].append(p)

        active_quads = {k: v for k, v in q_prims.items() if len(v) >= 2}
        if len(active_quads) < 2:
            return None

        # Standard Third-Angle Projection mapping:
        # Top View is top-left, Front View is bottom-left, Right View is bottom-right, Isometric is top-right
        quad_type_map = {
            "bottom_left": "front",
            "top_left": "top",
            "bottom_right": "right",
            "top_right": "isometric",
        }

        views = []
        for q_name, prims in active_quads.items():
            min_x = min(p.bbox[0] for p in prims)
            min_y = min(p.bbox[1] for p in prims)
            max_x = max(p.bbox[2] for p in prims)
            max_y = max(p.bbox[3] for p in prims)

            # Assign matching text annotations
            q_texts = [
                t for t in drawing.text_elements
                if min_x - 20 <= t.x <= max_x + 20 and min_y - 20 <= t.y <= max_y + 20
            ]

            views.append(
                DrawingView(
                    view_type=quad_type_map.get(q_name, "front"),
                    bbox=(min_x, min_y, max_x, max_y),
                    width=max_x - min_x,
                    height=max_y - min_y,
                    primitives=prims,
                    text_elements=q_texts,
                )
            )

        return views
