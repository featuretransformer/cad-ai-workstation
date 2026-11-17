import pytest
import uuid
from backend.cad.cadir.schema import CADIRDocument, CADIRFeature, Point3D
from backend.cad.cadir.interpreter import generate_build123d_code
from backend.cad.executor import execute_cad_code


def _build_and_execute(doc: CADIRDocument):
    code = generate_build123d_code(doc)
    res = execute_cad_code(code, design_id=f"test_{uuid.uuid4().hex[:8]}")
    assert res["success"] is True, f"Execution failed for {doc.name}: {res.get('error')}\nCode:\n{code}"
    return res


def test_u_channel_primitive():
    doc = CADIRDocument(
        name="Test U-Channel",
        component_family="u_channel",
        features=[
            CADIRFeature(
                name="Channel",
                feature_type="u_channel",
                params={"width": 30.0, "height": 20.0, "length": 80.0, "wall_thickness": 3.0},
                operation="new_body",
            )
        ],
    )
    res = _build_and_execute(doc)
    assert abs(res["volume"] - 15360.0) < 1.0


def test_i_beam_primitive():
    doc = CADIRDocument(
        name="Test I-Beam",
        component_family="i_beam",
        features=[
            CADIRFeature(
                name="Beam",
                feature_type="i_beam",
                params={"flange_width": 50.0, "height": 60.0, "length": 100.0, "flange_thickness": 6.0, "web_thickness": 6.0},
                operation="new_body",
            )
        ],
    )
    res = _build_and_execute(doc)
    assert abs(res["volume"] - 88800.0) < 1.0


def test_v_block_primitive():
    doc = CADIRDocument(
        name="Test V-Block",
        component_family="v_block",
        features=[
            CADIRFeature(
                name="VBlock",
                feature_type="v_block",
                params={"width": 60.0, "height": 40.0, "length": 50.0, "groove_depth": 15.0, "groove_angle": 90.0},
                operation="new_body",
            )
        ],
    )
    res = _build_and_execute(doc)
    assert abs(res["volume"] - 108750.0) < 5.0


def test_connecting_rod_primitive():
    doc = CADIRDocument(
        name="Test Connecting Rod",
        component_family="connecting_rod",
        features=[
            CADIRFeature(
                name="Rod",
                feature_type="connecting_rod",
                params={"outer_r": 20.0, "inner_r": 12.0, "center_dist": 100.0, "face_width": 10.0, "bore_d": 25.0, "small_bore": 14.0},
                operation="new_body",
            )
        ],
    )
    res = _build_and_execute(doc)
    assert abs(res["volume"] - 34199.5) < 5.0


def test_gear_rack_primitive():
    doc = CADIRDocument(
        name="Test Gear Rack",
        component_family="gear_rack",
        features=[
            CADIRFeature(
                name="Rack",
                feature_type="gear_rack",
                params={"module": 2.0, "teeth": 8, "pressure_angle": 20.0, "face_width": 12.0, "wall_thickness": 6.0, "height": 4.5},
                operation="new_body",
            )
        ],
    )
    res = _build_and_execute(doc)
    assert abs(res["volume"] - 5054.9) / 5054.9 < 0.05


def test_domed_cap_primitive():
    doc = CADIRDocument(
        name="Test Domed Cap",
        component_family="domed_cap",
        features=[
            CADIRFeature(
                name="Cap",
                feature_type="domed_cap",
                params={"outer_r": 30.0, "wall_thickness": 3.0, "flange_od": 84.0, "flange_thickness": 3.0},
                operation="new_body",
            )
        ],
    )
    res = _build_and_execute(doc)
    assert abs(res["volume"] - 25079.3) < 5.0


def test_v_pulley_primitive():
    doc = CADIRDocument(
        name="Test V-Pulley",
        component_family="v_pulley",
        features=[
            CADIRFeature(
                name="Pulley",
                feature_type="v_pulley",
                params={"od": 100.0, "face_width": 30.0, "groove_angle": 40.0, "groove_depth": 9.0, "rim_id": 80.0, "hub_diameter": 30.0, "bore_d": 16.0, "web_thickness": 6.0},
                operation="new_body",
            )
        ],
    )
    res = _build_and_execute(doc)
    assert abs(res["volume"] - 117208.8) < 5.0


def test_pocket_block_base_alignment():
    doc = CADIRDocument(
        name="Test Pocket Block",
        component_family="pocket_block",
        frame_z_base=True,
        frame_center_x=True,
        frame_center_y=True,
        features=[
            CADIRFeature(
                name="Base Block",
                feature_type="box",
                length=60.0,
                width=40.0,
                height=15.0,
                operation="new_body",
            ),
            CADIRFeature(
                name="Pocket",
                feature_type="box",
                length=30.0,
                width=20.0,
                height=8.0,
                position=Point3D(x=0.0, y=0.0, z=11.0),
                operation="cut",
            ),
        ],
    )
    res = _build_and_execute(doc)
    assert abs(res["volume"] - 31200.0) < 1.0


def test_pillow_block_primitive():
    doc = CADIRDocument(
        name="Test Pillow Block",
        component_family="pillow_block",
        features=[
            CADIRFeature(
                name="PillowBlock",
                feature_type="pillow_block",
                params={"length": 100.0, "width": 40.0, "flange_thickness": 12.0, "upright_width": 40.0, "height": 40.0, "bore_d": 20.0, "bore_z": 32.0, "hole_x": 40.0, "hole_d": 10.0},
                operation="new_body",
            )
        ],
    )
    res = _build_and_execute(doc)
    assert abs(res["volume"] - 97548.7) < 5.0
