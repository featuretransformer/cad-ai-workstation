"""
Engineering Drawing and Sketch Parser.
Extracts vector primitives (lines, arcs, circles, rectangles) and text annotations
from SVG engineering drawings and raster images (PNG, JPG) using svgpathtools and OpenCV.
"""
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from pydantic import BaseModel, Field
import xml.etree.ElementTree as ET
import re
import math
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class DrawingPrimitive(BaseModel):
    """Normalized 2D geometric primitive extracted from a drawing."""
    id: str
    primitive_type: str = Field(description="'line', 'arc', 'circle', 'rectangle', 'polyline'")
    start: Optional[Tuple[float, float]] = None
    end: Optional[Tuple[float, float]] = None
    center: Optional[Tuple[float, float]] = None
    radius: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    points: Optional[List[Tuple[float, float]]] = None
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # (min_x, min_y, max_x, max_y)


class TextAnnotation(BaseModel):
    """Text label or dimension annotation extracted from a drawing."""
    id: str
    text: str
    x: float
    y: float
    font_size: float = 12.0


class ParsedDrawing(BaseModel):
    """Structured representation of a parsed 2D drawing or sketch."""
    source_format: str  # 'svg', 'raster', 'dxf'
    width: float = 0.0
    height: float = 0.0
    viewbox: Optional[Tuple[float, float, float, float]] = None
    primitives: List[DrawingPrimitive] = Field(default_factory=list)
    text_elements: List[TextAnnotation] = Field(default_factory=list)


class DrawingParser:
    """
    Parser for technical engineering drawings in vector (SVG) and raster (PNG, JPG) formats.
    """

    def __init__(self):
        pass

    def parse(
        self,
        source: Union[str, Path, bytes],
        file_format: Optional[str] = None,
    ) -> ParsedDrawing:
        """
        Main entrypoint: parses drawing from file path, XML string, or image bytes.
        """
        # Determine format
        fmt = (file_format or "").lower()
        if not fmt and isinstance(source, (str, Path)):
            p = Path(source)
            if p.suffix:
                fmt = p.suffix.lstrip(".").lower()

        if isinstance(source, str) and ("<svg" in source or fmt == "svg"):
            return self.parse_svg(source)
        elif fmt in ("png", "jpg", "jpeg", "bmp") or isinstance(source, bytes):
            return self.parse_raster(source)
        elif isinstance(source, Path) and source.exists():
            if source.suffix.lower() == ".svg":
                with open(source, "r", encoding="utf-8", errors="ignore") as f:
                    return self.parse_svg(f.read())
            else:
                return self.parse_raster(source)

        return ParsedDrawing(source_format="unknown")

    def parse_svg(self, svg_content: Union[str, Path]) -> ParsedDrawing:
        """
        Extracts lines, arcs, circles, rectangles, and text elements from SVG markup.
        """
        if isinstance(svg_content, Path) or (isinstance(svg_content, str) and not svg_content.strip().startswith("<")):
            with open(svg_content, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        else:
            content = str(svg_content)

        # Remove namespaces for easy tag matching
        clean_xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', content)
        try:
            root = ET.fromstring(clean_xml)
        except ET.ParseError:
            # Fallback to loose regex or empty
            return ParsedDrawing(source_format="svg")

        # Parse viewBox and dimensions
        width = self._parse_num(root.attrib.get("width", "800"), 800.0)
        height = self._parse_num(root.attrib.get("height", "600"), 600.0)
        vb = None
        if "viewBox" in root.attrib:
            vb_parts = [float(x) for x in re.split(r'[\s,]+', root.attrib["viewBox"].strip()) if x]
            if len(vb_parts) == 4:
                vb = tuple(vb_parts)
                width = vb[2]
                height = vb[3]

        primitives: List[DrawingPrimitive] = []
        text_elements: List[TextAnnotation] = []
        counter = 1

        # 1. Circle elements
        for elem in root.iter("circle"):
            cx = self._parse_num(elem.attrib.get("cx", "0"))
            cy = self._parse_num(elem.attrib.get("cy", "0"))
            r = self._parse_num(elem.attrib.get("r", "10"))
            if r > 0:
                pid = f"prim_{counter}_circle"
                primitives.append(
                    DrawingPrimitive(
                        id=pid,
                        primitive_type="circle",
                        center=(cx, cy),
                        radius=r,
                        bbox=(cx - r, cy - r, cx + r, cy + r),
                    )
                )
                counter += 1

        # 2. Rect elements
        for elem in root.iter("rect"):
            rx = self._parse_num(elem.attrib.get("x", "0"))
            ry = self._parse_num(elem.attrib.get("y", "0"))
            rw = self._parse_num(elem.attrib.get("width", "0"))
            rh = self._parse_num(elem.attrib.get("height", "0"))
            if rw > 0 and rh > 0:
                pid = f"prim_{counter}_rect"
                primitives.append(
                    DrawingPrimitive(
                        id=pid,
                        primitive_type="rectangle",
                        start=(rx, ry),
                        width=rw,
                        height=rh,
                        bbox=(rx, ry, rx + rw, ry + rh),
                    )
                )
                counter += 1

        # 3. Line elements
        for elem in root.iter("line"):
            x1 = self._parse_num(elem.attrib.get("x1", "0"))
            y1 = self._parse_num(elem.attrib.get("y1", "0"))
            x2 = self._parse_num(elem.attrib.get("x2", "0"))
            y2 = self._parse_num(elem.attrib.get("y2", "0"))
            pid = f"prim_{counter}_line"
            primitives.append(
                DrawingPrimitive(
                    id=pid,
                    primitive_type="line",
                    start=(x1, y1),
                    end=(x2, y2),
                    bbox=(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)),
                )
            )
            counter += 1

        # 4. Path elements (using svgpathtools if available)
        try:
            import svgpathtools
            for elem in root.iter("path"):
                d = elem.attrib.get("d", "")
                if not d.strip():
                    continue
                try:
                    path_obj = svgpathtools.parse_path(d)
                    for seg in path_obj:
                        pid = f"prim_{counter}_path_seg"
                        counter += 1
                        if isinstance(seg, svgpathtools.Line):
                            sx, sy = seg.start.real, seg.start.imag
                            ex, ey = seg.end.real, seg.end.imag
                            primitives.append(
                                DrawingPrimitive(
                                    id=pid,
                                    primitive_type="line",
                                    start=(sx, sy),
                                    end=(ex, ey),
                                    bbox=(min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey)),
                                )
                            )
                        elif isinstance(seg, svgpathtools.Arc):
                            sx, sy = seg.start.real, seg.start.imag
                            ex, ey = seg.end.real, seg.end.imag
                            rad = seg.radius.real if hasattr(seg.radius, 'real') else float(seg.radius)
                            primitives.append(
                                DrawingPrimitive(
                                    id=pid,
                                    primitive_type="arc",
                                    start=(sx, sy),
                                    end=(ex, ey),
                                    radius=rad,
                                    bbox=(min(sx, ex) - rad, min(sy, ey) - rad, max(sx, ex) + rad, max(sy, ey) + rad),
                                )
                            )
                        else:
                            # Curves (CubicBezier, QuadraticBezier)
                            sx, sy = seg.start.real, seg.start.imag
                            ex, ey = seg.end.real, seg.end.imag
                            primitives.append(
                                DrawingPrimitive(
                                    id=pid,
                                    primitive_type="line",
                                    start=(sx, sy),
                                    end=(ex, ey),
                                    bbox=(min(sx, ex), min(sy, ey), max(sx, ex), max(sy, ey)),
                                )
                            )
                except Exception:
                    continue
        except ImportError:
            pass

        # 5. Text elements (annotations, dimensions)
        t_counter = 1
        for elem in root.iter("text"):
            text_str = "".join(elem.itertext()).strip()
            if text_str:
                tx = self._parse_num(elem.attrib.get("x", "0"))
                ty = self._parse_num(elem.attrib.get("y", "0"))
                fs = self._parse_num(elem.attrib.get("font-size", "12"))
                text_elements.append(
                    TextAnnotation(
                        id=f"txt_{t_counter}",
                        text=text_str,
                        x=tx,
                        y=ty,
                        font_size=fs if fs > 0 else 12.0,
                    )
                )
                t_counter += 1

        return ParsedDrawing(
            source_format="svg",
            width=width,
            height=height,
            viewbox=vb,
            primitives=primitives,
            text_elements=text_elements,
        )

    def parse_raster(self, image_source: Union[str, Path, bytes]) -> ParsedDrawing:
        """
        Parses raster drawings (PNG, JPG) using OpenCV to detect lines, circles, and layout contours.
        """
        import cv2
        import numpy as np

        if isinstance(image_source, (str, Path)):
            img = cv2.imread(str(image_source))
        elif isinstance(image_source, bytes):
            nparr = np.frombuffer(image_source, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            return ParsedDrawing(source_format="raster")

        if img is None:
            return ParsedDrawing(source_format="raster")

        height, width = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect circles using Hough Circles
        primitives: List[DrawingPrimitive] = []
        counter = 1

        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=20,
            param1=50,
            param2=30,
            minRadius=5,
            maxRadius=int(min(height, width) / 2),
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for c in circles[0, :]:
                cx, cy, r = float(c[0]), float(c[1]), float(c[2])
                pid = f"prim_{counter}_circle"
                primitives.append(
                    DrawingPrimitive(
                        id=pid,
                        primitive_type="circle",
                        center=(cx, cy),
                        radius=r,
                        bbox=(cx - r, cy - r, cx + r, cy + r),
                    )
                )
                counter += 1

        # Detect lines using Canny edges + HoughLinesP
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=20, maxLineGap=10)

        if lines is not None:
            for line in lines[:100]:  # Cap at 100 dominant lines
                coords = line[0] if hasattr(line, "__len__") and len(line) > 0 and hasattr(line[0], "__len__") else line
                x1, y1, x2, y2 = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
                pid = f"prim_{counter}_line"
                primitives.append(
                    DrawingPrimitive(
                        id=pid,
                        primitive_type="line",
                        start=(x1, y1),
                        end=(x2, y2),
                        bbox=(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)),
                    )
                )
                counter += 1

        return ParsedDrawing(
            source_format="raster",
            width=float(width),
            height=float(height),
            primitives=primitives,
            text_elements=[],
        )

    def _parse_num(self, val_str: str, default: float = 0.0) -> float:
        """Safely parses dimension strings like '120px', '45.5mm', '100' into floats."""
        if not val_str:
            return default
        match = re.search(r"[-+]?\d*\.?\d+", val_str)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return default
        return default
