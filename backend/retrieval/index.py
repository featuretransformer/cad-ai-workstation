"""
Parametric CAD Knowledge Base — SQLite Index.
Indexes canonical CADIR models across BenchCAD, DeepCAD, and Fusion360
for fast, structured few-shot exemplar retrieval and LLM context grounding.
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from cad.cadir.schema import CADIRDocument
from cad.cadir.interpreter import generate_build123d_code
from config import settings


class KnowledgeIndex:
    """
    SQLite-backed local indexing and retrieval engine for CADIR exemplars.
    Provides fast lookup by component family, feature sequences, and engineering constraints.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self.db_path = Path(db_path) if db_path else Path(settings.knowledge_db_path)
        self._ensure_db_dir()
        self.init_db()

    def _ensure_db_dir(self) -> None:
        """Ensure parent directory exists for SQLite database file."""
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection with dict row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Creates table schemas and query indices if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cad_examples (
                    id TEXT PRIMARY KEY,
                    source_dataset TEXT,
                    family TEXT,
                    variant TEXT,
                    difficulty TEXT,
                    feature_types TEXT,
                    feature_count INTEGER,
                    sketch_count INTEGER,
                    param_summary TEXT,
                    cadir_json TEXT,
                    description TEXT,
                    code_snippet TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cad_family ON cad_examples(family)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cad_source ON cad_examples(source_dataset)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cad_difficulty ON cad_examples(difficulty)")
            conn.commit()

    def index_document(
        self,
        doc: CADIRDocument,
        source_dataset: str,
        code_snippet: Optional[str] = None,
    ) -> bool:
        """
        Indexes a single CADIRDocument into the knowledge base.
        Generates build123d code snippet if not explicitly provided.
        """
        family = (doc.component_family or "").lower().strip()
        variant = (doc.engineering_intent.get("variant") or "").lower().strip()
        difficulty = (doc.difficulty or "medium").lower().strip()

        feature_types = [f.feature_type for f in doc.features]
        feature_count = len(doc.features)
        sketch_count = len(doc.sketches)

        # Extract parameter summary
        param_summary = dict(doc.parameters)
        for f in doc.features:
            if f.length is not None:
                param_summary[f"{f.id}_length"] = f.length
            if f.width is not None:
                param_summary[f"{f.id}_width"] = f.width
            if f.height is not None:
                param_summary[f"{f.id}_height"] = f.height
            if f.radius is not None:
                param_summary[f"{f.id}_radius"] = f.radius
            if f.distance is not None:
                param_summary[f"{f.id}_distance"] = f.distance
            if f.diameter is not None:
                param_summary[f"{f.id}_diameter"] = f.diameter

        # Generate build123d code snippet if needed
        generated_code = code_snippet
        if not generated_code:
            try:
                generated_code = generate_build123d_code(doc)
            except Exception:
                generated_code = ""

        cadir_json = doc.to_json()
        description = doc.description or f"{doc.name} ({source_dataset})"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO cad_examples (
                    id, source_dataset, family, variant, difficulty,
                    feature_types, feature_count, sketch_count,
                    param_summary, cadir_json, description, code_snippet
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.id,
                source_dataset,
                family,
                variant,
                difficulty,
                json.dumps(feature_types),
                feature_count,
                sketch_count,
                json.dumps(param_summary),
                cadir_json,
                description,
                generated_code,
            ))
            conn.commit()

        return True

    def bulk_index_documents(
        self,
        items: List[Tuple[CADIRDocument, str, Optional[str]]],
    ) -> int:
        """
        Batch index multiple (doc, source_dataset, optional_code) tuples inside a single transaction.
        """
        indexed_count = 0
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for doc, source_dataset, code_snippet in items:
                family = (doc.component_family or "").lower().strip()
                variant = (doc.engineering_intent.get("variant") or "").lower().strip()
                difficulty = (doc.difficulty or "medium").lower().strip()

                feature_types = [f.feature_type for f in doc.features]
                feature_count = len(doc.features)
                sketch_count = len(doc.sketches)

                param_summary = dict(doc.parameters)
                for f in doc.features:
                    if f.length is not None:
                        param_summary[f"{f.id}_length"] = f.length
                    if f.diameter is not None:
                        param_summary[f"{f.id}_diameter"] = f.diameter

                generated_code = code_snippet
                if not generated_code:
                    try:
                        generated_code = generate_build123d_code(doc)
                    except Exception:
                        generated_code = ""

                cursor.execute("""
                    INSERT OR REPLACE INTO cad_examples (
                        id, source_dataset, family, variant, difficulty,
                        feature_types, feature_count, sketch_count,
                        param_summary, cadir_json, description, code_snippet
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc.id,
                    source_dataset,
                    family,
                    variant,
                    difficulty,
                    json.dumps(feature_types),
                    feature_count,
                    sketch_count,
                    json.dumps(param_summary),
                    doc.to_json(),
                    doc.description or f"{doc.name} ({source_dataset})",
                    generated_code,
                ))
                indexed_count += 1
            conn.commit()
        return indexed_count

    def get_document_count(self) -> int:
        """Returns total number of indexed CAD documents."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cad_examples")
            return cursor.fetchone()[0]

    def get_family_counts(self) -> Dict[str, int]:
        """Returns distribution of component families in the index."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT family, COUNT(*) as cnt
                FROM cad_examples
                GROUP BY family
                ORDER BY cnt DESC
            """)
            return {row["family"]: row["cnt"] for row in cursor.fetchall()}

    def get_example_by_id(self, example_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves raw row dictionary by document ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cad_examples WHERE id = ?", (example_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["feature_types"] = json.loads(res["feature_types"])
            res["param_summary"] = json.loads(res["param_summary"])
            return res

    def clear_all(self) -> None:
        """Empties all records from the cad_examples table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cad_examples")
            conn.commit()
