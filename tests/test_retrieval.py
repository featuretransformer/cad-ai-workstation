"""
Unit tests for the CADIR Knowledge Base and Retrieval Engine:
KnowledgeIndex, CADIRQuery, search_knowledge_base, rank_candidates, and build_knowledge_index.
"""
import pytest
from pathlib import Path
import sys

# Ensure backend root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from cad.cadir.schema import (
    CADIRDocument,
    CADIRFeature,
    CADIRSketchProfile,
    CADIRCircle,
    CADIRPlane,
    Point3D,
    Vector3D,
)
from retrieval.index import KnowledgeIndex
from retrieval.ranker import rank_candidates
from retrieval.query import (
    CADIRQuery,
    search_knowledge_base,
    parse_intent_to_query,
)
from scripts.build_index import build_knowledge_index


def _create_sample_doc(
    doc_id: str,
    family: str,
    features_list: list,
    difficulty: str = "medium",
) -> CADIRDocument:
    doc = CADIRDocument(
        id=doc_id,
        name=f"Sample {family}",
        component_family=family,
        difficulty=difficulty,
        engineering_intent={"variant": "standard"},
    )
    prev_id = None
    for idx, f_type in enumerate(features_list):
        fid = f"f_{idx}_{f_type}"
        feat = CADIRFeature(
            id=fid,
            feature_type=f_type,
            distance=10.0 if f_type == "extrude" else (1.0 if f_type == "chamfer" else None),
            diameter=15.0 if f_type == "hole" else None,
            depth=10.0 if f_type == "hole" else None,
            radius=2.0 if f_type == "fillet" else None,
            length=1.0 if f_type == "chamfer" else None,
            dependencies=[prev_id] if prev_id else [],
        )
        if f_type == "extrude":
            sk = CADIRSketchProfile(
                id=f"sk_{idx}",
                plane=CADIRPlane(),
                primitives=[CADIRCircle(radius=20.0)],
            )
            doc.sketches.append(sk)
            feat.sketch_id = sk.id

        doc.features.append(feat)
        prev_id = fid

    return doc


# ─── KnowledgeIndex Tests ─────────────────────────────────────────────────────────────

def test_knowledge_index_creation(tmp_path):
    db_file = tmp_path / "test_knowledge.db"
    index = KnowledgeIndex(db_file)

    assert index.get_document_count() == 0
    assert index.get_family_counts() == {}


def test_knowledge_index_single_document(tmp_path):
    db_file = tmp_path / "test_knowledge.db"
    index = KnowledgeIndex(db_file)

    doc = _create_sample_doc("w_1", "washer", ["extrude", "hole", "chamfer"])
    success = index.index_document(doc, source_dataset="BenchCAD")

    assert success
    assert index.get_document_count() == 1

    row = index.get_example_by_id("w_1")
    assert row is not None
    assert row["family"] == "washer"
    assert row["source_dataset"] == "BenchCAD"
    assert "extrude" in row["feature_types"]
    assert "hole" in row["feature_types"]
    assert "chamfer" in row["feature_types"]
    assert row["code_snippet"] != ""  # Automatically generated build123d code


def test_knowledge_index_bulk_documents(tmp_path):
    db_file = tmp_path / "test_knowledge.db"
    index = KnowledgeIndex(db_file)

    doc1 = _create_sample_doc("doc_1", "flange", ["extrude", "hole"])
    doc2 = _create_sample_doc("doc_2", "flange", ["extrude", "hole", "fillet"])
    doc3 = _create_sample_doc("doc_3", "bracket", ["box", "hole"])

    indexed = index.bulk_index_documents([
        (doc1, "DeepCAD", None),
        (doc2, "DeepCAD", None),
        (doc3, "Fusion360", None),
    ])

    assert indexed == 3
    assert index.get_document_count() == 3

    families = index.get_family_counts()
    assert families["flange"] == 2
    assert families["bracket"] == 1


# ─── Ranker Tests ─────────────────────────────────────────────────────────────────────

def test_rank_candidates():
    candidates = [
        {
            "id": "c1",
            "family": "washer",
            "feature_types": ["extrude", "hole", "chamfer"],
            "difficulty": "medium",
            "description": "Standard ISO washer",
            "code_snippet": "val = ...",
        },
        {
            "id": "c2",
            "family": "hex_nut",
            "feature_types": ["extrude", "hole"],
            "difficulty": "medium",
            "description": "Hex nut",
            "code_snippet": "",
        },
        {
            "id": "c3",
            "family": "bracket",
            "feature_types": ["box", "fillet"],
            "difficulty": "hard",
            "description": "Mounting bracket",
            "code_snippet": "",
        },
    ]

    ranked = rank_candidates(
        candidates=candidates,
        family="washer",
        features=["hole", "chamfer"],
        keywords=["washer"],
        difficulty="medium",
    )

    assert len(ranked) == 3
    assert ranked[0]["id"] == "c1"
    assert ranked[0]["_score"] > ranked[1]["_score"]
    assert "exact_family_match(washer)" in ranked[0]["_match_reasons"]


# ─── Retrieval Query Tests ────────────────────────────────────────────────────────────

def test_parse_intent_to_query():
    query1 = parse_intent_to_query("I need a washer with a mounting hole and chamfer")
    assert query1.family == "washer"
    assert query1.features is not None
    assert "hole" in query1.features
    assert "chamfer" in query1.features

    query2 = parse_intent_to_query("Generate a hex_nut with polygon and extrude")
    assert query2.family == "hex_nut"
    assert "polygon" in query2.features
    assert "extrude" in query2.features


def test_search_knowledge_base_integration(tmp_path):
    db_file = tmp_path / "test_knowledge.db"
    index = KnowledgeIndex(db_file)

    w1 = _create_sample_doc("w_1", "washer", ["extrude", "hole", "chamfer"])
    w2 = _create_sample_doc("w_2", "washer", ["extrude", "hole"])
    n1 = _create_sample_doc("n_1", "hex_nut", ["extrude", "hole"])
    b1 = _create_sample_doc("b_1", "bracket", ["box", "hole", "fillet"])

    index.bulk_index_documents([
        (w1, "BenchCAD", None),
        (w2, "BenchCAD", None),
        (n1, "BenchCAD", None),
        (b1, "Fusion360", None),
    ])

    # 1. Search with structured CADIRQuery
    query = CADIRQuery(family="washer", features=["chamfer"], limit=2)
    results = search_knowledge_base(index, query)

    assert len(results) == 2
    assert results[0]["id"] == "w_1"
    assert results[0]["cadir_document"] is not None
    assert isinstance(results[0]["cadir_document"], CADIRDocument)

    # 2. Search with natural language string
    nl_results = search_knowledge_base(index, "I need a bracket with fillet", limit=1)
    assert len(nl_results) == 1
    assert nl_results[0]["id"] == "b_1"
    assert nl_results[0]["family"] == "bracket"


# ─── Batch Indexing Script Tests ──────────────────────────────────────────────────────

def test_build_knowledge_index_script_execution(tmp_path):
    target_db = tmp_path / "script_knowledge.db"

    build_knowledge_index(
        db_path=target_db,
        limit_per_dataset=2,
        clear_existing=True,
    )

    assert target_db.exists()
    index = KnowledgeIndex(target_db)
    count = index.get_document_count()
    # At least DeepCAD, BenchCAD, and Fusion360 should each contribute up to 2 items
    assert count >= 4
