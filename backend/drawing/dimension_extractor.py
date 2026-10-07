"""
Engineering Dimension and Annotation Extractor.
Parses linear dimensions, diameters (Ø), radii (R), hole callouts, and tolerances
from drawing text annotations and correlates them to geometric primitives.
"""
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
import re
import math
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from drawing.parser import TextAnnotation, DrawingPrimitive


class ExtractedDimension(BaseModel):
    """Normalized engineering dimension extracted from drawing annotations."""
    value: float
    dimension_type: str = Field(description="'linear', 'diameter', 'radius', 'hole_callout', 'chamfer', 'angle'")
    raw_text: str
    tolerance: Optional[str] = None
    count: int = 1
    associated_primitive_id: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None


class DimensionExtractor:
    """
    Extracts numerical dimensions, engineering symbols, and tolerances from text annotations.
    Associates dimensions to spatial geometric primitives.
    """

    # Engineering dimension patterns
    DIAMETER_PATTERN = re.compile(r"(?:[Øø]|dia|diameter|\%\%c)\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
    RADIUS_PATTERN = re.compile(r"(?:^|[^\w])R\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
    HOLE_PATTERN = re.compile(r"(\d+)\s*[xX]\s*(?:[Øø]|dia)?\s*(\d+(?:\.\d+)?)", re.IGNORECASE)
    CHAMFER_PATTERN = re.compile(r"(?:C|chamfer)?\s*(\d+(?:\.\d+)?)\s*[xX]\s*45(?:°|deg)?", re.IGNORECASE)
    ANGLE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:°|deg)", re.IGNORECASE)
    LINEAR_PATTERN = re.compile(r"(?:^|[^\w])(\d+(?:\.\d+)?)\s*(?:mm|in)?(?:[^\w]|$)", re.IGNORECASE)
    TOLERANCE_PATTERN = re.compile(r"±\s*(\d+(?:\.\d+)?)|\+(\d+(?:\.\d+)?)\s*/\s*-(\d+(?:\.\d+)?)")

    def __init__(self):
        pass

    def extract_dimensions(
        self,
        text_elements: List[TextAnnotation],
        primitives: Optional[List[DrawingPrimitive]] = None,
    ) -> List[ExtractedDimension]:
        """
        Parses all text annotations and correlates them to the nearest geometric primitives.
        """
        extracted = []

        for txt in text_elements:
            t_str = txt.text.strip()
            dim = self._parse_single_text(t_str, txt.x, txt.y)
            if dim:
                if primitives:
                    dim.associated_primitive_id = self._find_nearest_primitive(dim, primitives)
                extracted.append(dim)

        return extracted

    def _parse_single_text(self, text: str, x: float, y: float) -> Optional[ExtractedDimension]:
        """Parses a single text string into an ExtractedDimension model."""
        clean = text.strip()

        # 1. Chamfer: e.g. "2x45°", "C1.5"
        cham_m = self.CHAMFER_PATTERN.search(clean)
        if cham_m:
            val = float(cham_m.group(1))
            return ExtractedDimension(
                value=val,
                dimension_type="chamfer",
                raw_text=clean,
                x=x,
                y=y,
            )

        # 2. Hole pattern: e.g. "4x Ø10" or "2x 8.5"
        hole_m = self.HOLE_PATTERN.search(clean)
        if hole_m:
            count = int(hole_m.group(1))
            val = float(hole_m.group(2))
            return ExtractedDimension(
                value=val,
                dimension_type="hole_callout",
                raw_text=clean,
                count=count,
                x=x,
                y=y,
            )

        # 3. Diameter: e.g. "Ø25", "DIA 50"
        dia_m = self.DIAMETER_PATTERN.search(clean)
        if dia_m:
            val = float(dia_m.group(1))
            return ExtractedDimension(
                value=val,
                dimension_type="diameter",
                raw_text=clean,
                x=x,
                y=y,
            )

        # 4. Radius: e.g. "R5", "R 12.5"
        rad_m = self.RADIUS_PATTERN.search(clean)
        if rad_m:
            val = float(rad_m.group(1))
            return ExtractedDimension(
                value=val,
                dimension_type="radius",
                raw_text=clean,
                x=x,
                y=y,
            )

        # 5. Angle: e.g. "45°", "90 deg"
        ang_m = self.ANGLE_PATTERN.search(clean)
        if ang_m:
            val = float(ang_m.group(1))
            return ExtractedDimension(
                value=val,
                dimension_type="angle",
                raw_text=clean,
                x=x,
                y=y,
            )

        # 6. General Linear Dimension
        lin_m = self.LINEAR_PATTERN.search(clean)
        if lin_m:
            try:
                val = float(lin_m.group(1))
                # Ignore trivial digits like single index numbers
                if val > 0:
                    tol_str = None
                    tol_m = self.TOLERANCE_PATTERN.search(clean)
                    if tol_m:
                        tol_str = tol_m.group(0).replace(" ", "")

                    return ExtractedDimension(
                        value=val,
                        dimension_type="linear",
                        raw_text=clean,
                        tolerance=tol_str,
                        x=x,
                        y=y,
                    )
            except ValueError:
                pass

        return None

    def _find_nearest_primitive(
        self,
        dim: ExtractedDimension,
        primitives: List[DrawingPrimitive],
    ) -> Optional[str]:
        """Finds the geometric primitive closest to the dimension text position."""
        if dim.x is None or dim.y is None:
            return None

        best_id = None
        min_dist = float("inf")

        for p in primitives:
            # Distance from dimension text coordinate to primitive centroid
            cx = (p.bbox[0] + p.bbox[2]) / 2.0
            cy = (p.bbox[1] + p.bbox[3]) / 2.0
            dist = math.hypot(dim.x - cx, dim.y - cy)

            # Bonus for matching type: diameter/radius prefers circle/arc
            if dim.dimension_type in ("diameter", "radius", "hole_callout") and p.primitive_type in ("circle", "arc"):
                dist *= 0.5

            if dist < min_dist:
                min_dist = dist
                best_id = p.id

        return best_id
