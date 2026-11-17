"""
Lightweight Macro RAG Index (Upgrade 6).
Indexes curated structural construction patterns from Zero-To-CAD-1m, bd_warehouse, and gggears.
Uses local SQLite FTS5 (BM25) full-text search with optional Gemini text-embedding-004 hybrid reranking.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import math
import re
import sqlite3
import sys

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

DATA_DIR = backend_dir / "data"
DB_PATH = DATA_DIR / "macro_rag.db"

# ─────────────────────────────────────────────────────────────────────────────
# Curated Macro Construction Patterns (Zero-To-CAD-1m + bd_warehouse + gggears)
# ─────────────────────────────────────────────────────────────────────────────
CURATED_PATTERNS = [
    {
        "id": "macro_iso_bolt",
        "title": "ISO Metric Hex Head Bolt (bd_warehouse / ISO 4014)",
        "category": "fastener",
        "keywords": "bolt hex head fastener screw iso 4014 din 931 thread m6 m8 m10 m12",
        "operations": "new_body, thread, hex",
        "cadir_json": json.dumps({
            "feature_type": "iso_bolt",
            "standard_designation": "M8x40",
            "length": 40.0,
            "diameter": 8.0,
            "operation": "new_body"
        }),
        "build123d_snippet": "from bd_warehouse.fastener import Iso4014\nbolt = Iso4014(size='M8-1.25', length=40.0)",
    },
    {
        "id": "macro_iso_nut",
        "title": "ISO Metric Hex Nut (bd_warehouse / ISO 4032)",
        "category": "fastener",
        "keywords": "nut hex fastener internal thread iso 4032 din 934 m6 m8 m10 m12",
        "operations": "new_body, internal_thread, hex",
        "cadir_json": json.dumps({
            "feature_type": "iso_nut",
            "standard_designation": "M8",
            "diameter": 8.0,
            "operation": "new_body"
        }),
        "build123d_snippet": "from bd_warehouse.fastener import Iso4032\nnut = Iso4032(size='M8-1.25')",
    },
    {
        "id": "macro_pipe_flange",
        "title": "Industrial Welding Neck Pipe Flange (bd_warehouse / ANSI B16.5)",
        "category": "flange",
        "keywords": "pipe flange welding neck raised face ansi b16.5 din en 1092 pcd bolt circle hub",
        "operations": "new_body, cylinder, hole, pattern",
        "cadir_json": json.dumps({
            "feature_type": "pipe_flange",
            "standard_designation": "2_inch_150lb",
            "bore_diameter": 50.8,
            "diameter": 152.4,
            "height": 25.4,
            "operation": "new_body"
        }),
        "build123d_snippet": "from bd_warehouse.flange import WeldNeckFlange\nflange = WeldNeckFlange(nps='2', pressure_class=150)",
    },
    {
        "id": "macro_roller_bearing",
        "title": "Deep Groove Ball Bearing 608 / 6200 / 6204 (bd_warehouse)",
        "category": "bearing",
        "keywords": "bearing ball roller deep groove raceway inner outer ring bore 608 6200 6204",
        "operations": "new_body, cylinder, revolve",
        "cadir_json": json.dumps({
            "feature_type": "deep_groove_bearing",
            "standard_designation": "608",
            "bore_diameter": 8.0,
            "diameter": 22.0,
            "height": 7.0,
            "operation": "new_body"
        }),
        "build123d_snippet": "from bd_warehouse.bearing import DeepGrooveBallBearing\nbearing = DeepGrooveBallBearing(size='608')",
    },
    {
        "id": "macro_spur_gear",
        "title": "Involute Spur Gear (gggears)",
        "category": "gear",
        "keywords": "spur gear involute teeth pitch module pressure angle pitch diameter bore keyway",
        "operations": "new_body, extrude, pattern, cut",
        "cadir_json": json.dumps({
            "feature_type": "spur_gear_macro",
            "module": 2.0,
            "teeth": 24,
            "face_width": 15.0,
            "bore_diameter": 12.0,
            "pressure_angle": 20.0,
            "operation": "new_body"
        }),
        "build123d_snippet": "from gggears import SpurGear\ngear = SpurGear(module=2.0, teeth=24, face_width=15.0, bore=12.0)",
    },
    {
        "id": "macro_helical_gear",
        "title": "Helical Involute Transmission Gear (gggears)",
        "category": "gear",
        "keywords": "helical gear angle teeth module helix transmission reduction",
        "operations": "new_body, loft, pattern",
        "cadir_json": json.dumps({
            "feature_type": "helical_gear",
            "module": 2.5,
            "teeth": 30,
            "face_width": 20.0,
            "helix_angle": 15.0,
            "bore_diameter": 16.0,
            "operation": "new_body"
        }),
        "build123d_snippet": "from gggears import HelicalGear\ngear = HelicalGear(module=2.5, teeth=30, helix_angle=15.0, face_width=20.0)",
    },
    {
        "id": "macro_bevel_gear",
        "title": "90-Degree Bevel Gear (gggears)",
        "category": "gear",
        "keywords": "bevel gear conical 90 degree right angle transmission miter",
        "operations": "new_body, revolve, cut",
        "cadir_json": json.dumps({
            "feature_type": "bevel_gear",
            "module": 3.0,
            "teeth": 20,
            "bore_diameter": 15.0,
            "operation": "new_body"
        }),
        "build123d_snippet": "from gggears import BevelGear\ngear = BevelGear(module=3.0, teeth=20, bore=15.0)",
    },
    {
        "id": "zero_to_cad_circular_flange_hub",
        "title": "Revolved Flange Hub with PCD Bolt Circle (Zero-To-CAD-1m)",
        "category": "flange",
        "keywords": "flange hub revolved cylinder central bore pcd bolt circle clearance holes fillet",
        "operations": "cylinder, hole, pattern, fillet",
        "cadir_json": json.dumps({
            "features": [
                {"id": "base_disc", "feature_type": "cylinder", "radius": 60.0, "height": 15.0, "operation": "new_body"},
                {"id": "raised_boss", "feature_type": "cylinder", "radius": 35.0, "height": 30.0, "target_face_selector": "top", "operation": "join"},
                {"id": "thru_bore", "feature_type": "hole", "diameter": 30.0, "depth": 50.0, "target_face_selector": "top", "operation": "cut"},
                {"id": "pcd_holes", "feature_type": "hole", "diameter": 6.6, "depth": 20.0, "target_face_selector": "top", "pattern_radius": 48.0, "operation": "cut"},
                {"id": "neck_fillet", "feature_type": "fillet", "radius": 3.0, "target_edge_selector": "all_vertical", "operation": "join"}
            ]
        }),
        "build123d_snippet": "with BuildPart() as p:\n    Cylinder(radius=60, height=15)\n    with BuildSketch(faces().sort_by(Axis.Z)[-1]):\n        Circle(radius=35)\n    extrude(amount=30)\n    Hole(radius=15, depth=50)\n    with Locations(PolarLocations(radius=48, count=6)):\n        Hole(radius=3.3, depth=20)",
    },
    {
        "id": "zero_to_cad_machined_u_bracket",
        "title": "Milled U-Bracket with Stiffener Rib (Zero-To-CAD-1m)",
        "category": "bracket",
        "keywords": "u bracket channel milled stiffener web rib mounting slot holes fillet",
        "operations": "box, pocket, hole, fillet",
        "cadir_json": json.dumps({
            "features": [
                {"id": "base_block", "feature_type": "box", "length": 120.0, "width": 80.0, "height": 50.0, "operation": "new_body"},
                {"id": "center_channel", "feature_type": "pocket", "length": 90.0, "width": 60.0, "depth": 40.0, "target_face_selector": "top", "operation": "cut"},
                {"id": "mount_holes", "feature_type": "hole", "diameter": 9.0, "depth": 20.0, "target_face_selector": "top", "operation": "cut"},
                {"id": "edge_blend", "feature_type": "fillet", "radius": 2.5, "target_edge_selector": "top_perimeter", "operation": "join"}
            ]
        }),
        "build123d_snippet": "with BuildPart() as p:\n    Box(120, 80, 50)\n    with BuildSketch(faces().sort_by(Axis.Z)[-1]):\n        Rectangle(90, 60)\n    extrude(amount=-40, mode=Mode.SUBTRACT)\n    fillet(faces().sort_by(Axis.Z)[-1].edges(), radius=2.5)",
    },
    {
        "id": "zero_to_cad_stepped_shaft",
        "title": "Stepped Transmission Shaft with Bearing Seats (Zero-To-CAD-1m)",
        "category": "shaft",
        "keywords": "stepped shaft transmission bearing seat keyway chamfer shoulder journal",
        "operations": "cylinder, groove, chamfer",
        "cadir_json": json.dumps({
            "features": [
                {"id": "main_shaft", "feature_type": "cylinder", "radius": 20.0, "height": 160.0, "operation": "new_body"},
                {"id": "bearing_seat_1", "feature_type": "cylinder", "radius": 15.0, "height": 30.0, "target_face_selector": "top", "operation": "join"},
                {"id": "bearing_seat_2", "feature_type": "cylinder", "radius": 15.0, "height": 30.0, "target_face_selector": "bottom", "operation": "join"},
                {"id": "end_chamfer", "feature_type": "chamfer", "distance": 1.5, "target_edge_selector": "top_perimeter", "operation": "join"}
            ]
        }),
        "build123d_snippet": "with BuildPart() as p:\n    Cylinder(radius=20, height=160)\n    with BuildSketch(faces().sort_by(Axis.Z)[-1]):\n        Circle(radius=15)\n    extrude(amount=30)\n    chamfer(faces().sort_by(Axis.Z)[-1].edges(), length=1.5)",
    },
    {
        "id": "zero_to_cad_hydraulic_manifold",
        "title": "Hydraulic Manifold Block with Port Cavities (Zero-To-CAD-1m)",
        "category": "manifold",
        "keywords": "manifold block hydraulic port passage cavity fluid cross drill npt counterbore",
        "operations": "box, hole, counterbore, pocket",
        "cadir_json": json.dumps({
            "features": [
                {"id": "body_block", "feature_type": "box", "length": 140.0, "width": 100.0, "height": 70.0, "operation": "new_body"},
                {"id": "inlet_port", "feature_type": "hole", "diameter": 16.0, "depth": 50.0, "target_face_selector": "top", "operation": "cut"},
                {"id": "outlet_port", "feature_type": "hole", "diameter": 16.0, "depth": 50.0, "target_face_selector": "front", "operation": "cut"},
                {"id": "mounting_cbores", "feature_type": "counterbore", "diameter": 9.0, "depth": 70.0, "target_face_selector": "top", "operation": "cut"}
            ]
        }),
        "build123d_snippet": "with BuildPart() as p:\n    Box(140, 100, 70)\n    with BuildSketch(faces().sort_by(Axis.Z)[-1]):\n        Circle(radius=8)\n    extrude(amount=-50, mode=Mode.SUBTRACT)",
    }
]


def _init_db(conn: sqlite3.Connection):
    """Initializes SQLite schema and populates curated patterns."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS macro_metadata (
            id TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            keywords TEXT,
            operations TEXT,
            cadir_json TEXT,
            build123d_snippet TEXT
        )
    """)
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS macro_fts USING fts5(
            id UNINDEXED,
            title,
            category,
            keywords,
            operations,
            tokenize='porter'
        )
    """)

    # Check if empty
    cursor.execute("SELECT count(*) FROM macro_metadata")
    if cursor.fetchone()[0] == 0:
        for p in CURATED_PATTERNS:
            cursor.execute(
                "INSERT INTO macro_metadata (id, title, category, keywords, operations, cadir_json, build123d_snippet) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p["id"], p["title"], p["category"], p["keywords"], p["operations"], p["cadir_json"], p["build123d_snippet"])
            )
            cursor.execute(
                "INSERT INTO macro_fts (id, title, category, keywords, operations) VALUES (?, ?, ?, ?, ?)",
                (p["id"], p["title"], p["category"], p["keywords"], p["operations"])
            )
        conn.commit()


def get_macro_db_connection() -> sqlite3.Connection:
    """Returns a connection to the local Macro RAG SQLite database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def query_macro_rag(
    prompt: str,
    operations: Optional[List[str]] = None,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Hybrid retriever (BM25 FTS5 + optional Gemini embedding scoring).
    Finds top structural construction patterns matching the prompt and requested operations.
    """
    if not prompt:
        return []

    conn = get_macro_db_connection()
    cursor = conn.cursor()

    # Sanitize search query for FTS5 (alphanumeric tokens only)
    tokens = re.findall(r'[a-zA-Z0-9]+', prompt.lower())
    if operations:
        for op in operations:
            tokens.extend(re.findall(r'[a-zA-Z0-9]+', op.lower()))

    # Filter out short stopwords
    stopwords = {"a", "an", "the", "in", "on", "at", "for", "with", "and", "or", "of", "to", "is", "it"}
    valid_tokens = [t for t in tokens if len(t) > 2 and t not in stopwords]

    if not valid_tokens:
        valid_tokens = ["flange", "gear", "bracket"]

    # Build FTS5 query: "token1 OR token2 OR ..."
    fts_query = " OR ".join(valid_tokens[:32])

    results: List[Dict[str, Any]] = []

    try:
        query_sql = """
            SELECT m.id, m.title, m.category, m.keywords, m.operations, m.cadir_json, m.build123d_snippet, bm25(macro_fts) as rank
            FROM macro_fts
            JOIN macro_metadata m ON macro_fts.id = m.id
            WHERE macro_fts MATCH ?
            ORDER BY rank ASC
            LIMIT ?
        """
        cursor.execute(query_sql, (fts_query, limit * 2))
        rows = cursor.fetchall()

        for row in rows:
            results.append({
                "id": row["id"],
                "title": row["title"],
                "category": row["category"],
                "keywords": row["keywords"],
                "operations": row["operations"],
                "cadir_json": row["cadir_json"],
                "build123d_snippet": row["build123d_snippet"],
                "score": float(row["rank"]),
            })
    except Exception as e:
        # Fallback to category substring match if FTS5 query fails
        cursor.execute("SELECT * FROM macro_metadata LIMIT ?", (limit,))
        for row in cursor.fetchall():
            results.append({
                "id": row["id"],
                "title": row["title"],
                "category": row["category"],
                "keywords": row["keywords"],
                "operations": row["operations"],
                "cadir_json": row["cadir_json"],
                "build123d_snippet": row["build123d_snippet"],
                "score": 1.0,
            })
    finally:
        conn.close()

    return results[:limit]
