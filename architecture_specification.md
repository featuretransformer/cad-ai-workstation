# AI-Integrated Parametric CAD Workstation — Dataset Enhancement Architecture Specification

> **Status:** Analysis & Specification (NO implementation)
> **Date:** 2026-10-06
> **Handoff Target:** Gemini Pro High for coding/implementation

---

## TABLE OF CONTENTS

1. [Current System Assessment](#section-1)
2. [Four Dataset Analysis](#section-2)
3. [Dataset Roles](#section-3)
4. [Two Knowledge Pathways](#section-4)
5. [Drawing/Sketch/Photo Pipeline](#section-5)
6. [CADIR Integration](#section-6)
7. [Retrieval](#section-7)
8. [Training](#section-8)
9. [Complex CAD Generation](#section-9)
10. [LangGraph Integration](#section-10)
11. [Self-Healing](#section-11)
12. [Data Pipeline](#section-12)
13. [Directory Structure](#section-13)
14. [Windows Workflow](#section-14)
15. [Licensing](#section-15)
16. [Performance](#section-16)
17. [Benchmark](#section-17)
18. [Implementation Plan](#section-18)
19. [Risks](#section-19)
20. [Final Architecture](#section-20)

---

<a id="section-1"></a>
## SECTION 1 — CURRENT SYSTEM ASSESSMENT

### 1.1 What Exists Today

The project at [`cad-ai-workstation-main/`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main) is a Phase 1 Alpha multi-agent CAD workstation with the following verified architecture:

| Layer | Files | Status |
|-------|-------|--------|
| **FastAPI backend** | [`main.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/main.py) | ✅ Exists, imports `api.routes` and `agents.graph` |
| **Pydantic config** | [`config.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/config.py) | ✅ Settings: Ollama, Gemini, Groq, PostgreSQL, Redis, MinIO |
| **CAD executor** | [`cad/executor.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/cad/executor.py) | ✅ Sandboxed subprocess running build123d code |
| **CAD exporter** | [`cad/exporter.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/cad/exporter.py) | ✅ STEP→STL→GLB pipeline via trimesh |
| **Feature tree** | [`cad/feature_tree.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/cad/feature_tree.py) | ✅ Regex-based feature extraction from build123d code |
| **Validator** | [`cad/validator.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/cad/validator.py) | ✅ STEP file-exists check + trimesh watertight/manifold |
| **Celery tasks** | [`tasks/cad_tasks.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/tasks/cad_tasks.py) | ✅ LangGraph pipeline execution with Redis pub/sub |
| **LLM factory** | [`utils/llm.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/utils/llm.py) | ✅ Gemini Pro (supervisor) + Groq/DeepSeek (design) |
| **Database** | [`db/models.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/db/models.py), [`db/crud.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/db/crud.py), [`db/schemas.py`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/backend/db/schemas.py) | ✅ Session, Design, AgentLog, ExportArtifact |
| **Docker infra** | [`docker-compose.dev.yml`](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/docker-compose.dev.yml) | ✅ PostgreSQL, Redis, MinIO |
| **Frontend** | `frontend/src/` (15 files) | ✅ Next.js 14, React Three Fiber, Zustand, WebSocket |

### 1.2 Critical Observation: Missing Directories

The `main.py` imports `from api.routes import sessions, design, export, websocket` and `from agents.graph import cad_graph`, but **neither `backend/agents/` nor `backend/api/` directories currently exist on disk**. The README documents them as expected. This means:

- The LangGraph agent pipeline (`agents/graph.py`, `agents/state.py`, individual agent nodes) **needs to be created or is intended to be created**
- The API routes (`api/routes/`) **need to be created or are intended to be created**
- The project runs at Phase 1 Alpha with the documented architecture as the design target

### 1.3 What MUST Remain Unchanged

| Component | Reason |
|-----------|--------|
| `cad/executor.py` — sandboxed subprocess model | Core security + isolation architecture |
| `cad/exporter.py` — STEP→STL→GLB pipeline | Working export chain |
| `cad/validator.py` — trimesh validation | Geometry validation infrastructure |
| `cad/feature_tree.py` — regex pattern list | Working feature extraction (extend, don't replace) |
| `db/models.py` — Session/Design/AgentLog/ExportArtifact | Database schema (extend with new fields, don't restructure) |
| `tasks/cad_tasks.py` — Celery + Redis pub/sub | Working task/streaming infrastructure |
| `config.py` — Settings pattern | Extend with new settings, don't replace |
| `utils/llm.py` — LLM factory | Extend with Ollama local models, don't replace |
| `docker-compose.dev.yml` — infrastructure | No modifications needed |
| Frontend — all 15 source files | Extend only when dataset features reach the UI |
| Raw dataset directories | **IMMUTABLE** — never modify raw files |

### 1.4 Current CADIR Status

**There is no explicit CADIR schema or representation in the codebase.** The system currently:
1. LLM generates raw build123d Python code directly
2. Executor runs that code in a subprocess
3. Feature tree is extracted *post-hoc* via regex

**The CADIR concept exists in the architecture vision but is not yet implemented.** This is a key finding — the dataset enhancement work must include creating the CADIR schema as a foundational step before dataset adapters can map into it.

### 1.5 Current LLM Configuration

| Setting | Current Value | Notes |
|---------|---------------|-------|
| `ollama_base_url` | `http://localhost:11434` | ✅ Configured |
| `ollama_model` | `llama3.1:8b` | Default only; Qwen3:8b, DeepSeek-R1:8b also available |
| Supervisor LLM | Gemini 1.5 Pro or Groq Llama 3.3 70B | Cloud-based |
| Design LLM | Groq DeepSeek-R1-distill-llama-70b or Gemini 1.5 Flash | Cloud-based |

**The LLM factory does not yet support local Ollama models.** This needs to be extended.

---

<a id="section-2"></a>
## SECTION 2 — FOUR DATASET ANALYSIS

### 2.1 DeepCAD

| Property | Value |
|----------|-------|
| **Location** | `datasets/DeepCAD/` |
| **License** | MIT (Copyright 2022 Rundi Wu) |
| **Source** | Onshape public documents via ABC dataset |
| **Format** | JSON files (`cad_json/`), vectorized H5 (`cad_vec.tar.gz`) |
| **Size on disk** | 77,720 JSON files across 37 subdirectories |
| **Split** | train: 161,240 / val: 8,946 / test: 8,052 (from `train_val_test_split.json`) |
| **Repo code** | `datasets/DeepCAD/repo/` — PyTorch autoencoder + latent GAN |

**Actual data format (verified from `00027103.json`):**

```json
{
  "entities": {
    "<uuid>": {
      "type": "ExtrudeFeature",
      "name": "Extrude 2",
      "operation": "NewBodyFeatureOperation",
      "extent_type": "SymmetricFeatureExtentType",
      "profiles": [{"profile": "...", "sketch": "..."}],
      "extent_one": {"distance": {"value": 0.127}, "taper_angle": {"value": 0.0}},
      ...
    },
    "<uuid>": {
      "type": "Sketch",
      "reference_plane": {},
      "points": {},
      "curves": {},
      "profiles": {},
      "transform": {},
      ...
    }
  },
  "properties": {...},
  "sequence": [
    {"type": "Sketch", "index": 0, ...},
    {"type": "ExtrudeFeature", "index": 1, ...},
    ...
  ]
}
```

**Geometry information:**
- Sketch-and-extrude construction sequences
- 2D sketch primitives: lines, arcs, circles with explicit coordinates
- Extrude operations: NewBody, Join, Cut, Intersect
- Extent types: OneSide, Symmetric, TwoSides
- Sketch plane transforms (origin, orientation)
- Profile references linking sketches to extrude operations
- Parametric distances and taper angles

**Feature information:**
- Sequential feature ordering via `sequence` array
- Dependencies: extrude profiles reference sketch entities
- Operation types: boolean operations (new body, join, cut, intersect)

**Code information:** None — data-only, no executable CAD code

**Preprocessing requirements:**
- Parse JSON into normalized feature sequences
- Extract sketch geometry primitives
- Map extrude operations to build123d equivalents
- Handle coordinate normalization (units in Onshape scale, not mm)
- Filter out malformed/incomplete sequences

**Usefulness:** **HIGH** — richest source of parametric sketch-and-extrude construction sequences with exact parameters. Directly maps to the sketch→extrude construction paradigm.

**Limitations:**
- Only sketch-and-extrude operations (no fillet, chamfer, shell, revolve, sweep, loft, pattern)
- Relatively simple geometries (the dataset was designed for generative model training)
- No component category labels (shaft, flange, bracket, etc.)
- Onshape-specific entity format requiring translation

### 2.2 BenchCAD

| Property | Value |
|----------|-------|
| **Location** | `datasets/BenchCAD/BenchCAD___bench_cad/code_gen/` |
| **License** | Not explicitly stated in dataset_info.json (empty license field) — **REQUIRES VERIFICATION** |
| **Format** | HuggingFace Arrow/Parquet dataset (2 shards) |
| **Size** | 17,900 examples, ~746 MB download, ~765 MB uncompressed |

**Actual data schema (verified from `dataset_info.json`):**

| Field | Type | Description |
|-------|------|-------------|
| `stem` | string | Component identifier/stem name |
| `family` | string | **Component family category** |
| `variant` | string | Variant within family |
| `difficulty` | string | Difficulty rating |
| `base_plane` | string | Base construction plane |
| `standard` | string | Engineering standard reference |
| `code` | string | **Executable CadQuery Python code** |
| `view_0_png` through `view_3_png` | Image | Multi-view rendered images |
| `composite_png` | Image | Composite multi-view image |

**Geometry information:** Via CadQuery code execution (implicit), multi-view images (visual)

**Feature information:** Component family/variant classification, difficulty level, base plane

**Code information:** **Executable CadQuery Python code** — this is the critical value. CadQuery and build123d share the same OpenCASCADE kernel and many API patterns, but the syntax differs significantly.

**Metadata:** Component family, variant, difficulty, standard, base plane — **extremely valuable** for retrieval indexing

**Construction sequence information:** Embedded in the CadQuery code (sequential operations)

**Preprocessing requirements:**
- Load Arrow/Parquet via HuggingFace `datasets` or PyArrow
- Parse CadQuery code → extract operation sequences
- Translate CadQuery patterns to build123d equivalents
- Extract metadata fields for indexing
- Validate code executability (CadQuery→build123d translation may introduce errors)

**Usefulness:** **HIGHEST** — only dataset with (a) executable CAD code, (b) component family labels, (c) difficulty levels, and (d) multi-view images. Direct source for few-shot examples.

**Limitations:**
- CadQuery, not build123d — requires translation
- License unclear — must verify before any commercial use
- 17,900 examples is moderate scale
- Code quality/correctness is assumed, not verified

### 2.3 Fusion 360 Gallery Dataset

| Property | Value |
|----------|-------|
| **Location** | `datasets/Fusion360Gallery/Fusion360GalleryDataset-master/` |
| **License** | **Autodesk custom license — NON-COMMERCIAL RESEARCH ONLY** |
| **Source** | Autodesk Fusion 360 user submissions |
| **Format** | Currently only documentation/tools in repo; actual data must be downloaded separately |
| **Sub-datasets** | Reconstruction (8,625 sequences), Segmentation (35,680 parts), Assembly (8,251 assemblies) |

**Actual contents currently on disk:** Only the README, documentation, and tools scripts — **the actual geometry/JSON data has NOT been downloaded yet**.

**The most relevant subset is the Reconstruction Dataset (r1.0.1, 2.0 GB download):**

From the [reconstruction documentation](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/datasets/Fusion360Gallery/Fusion360GalleryDataset-master/docs/reconstruction.md):

- Construction sequences in JSON with `timeline`, `entities`, `sequence` structures
- **Identical format to DeepCAD** (both come from Fusion 360 / Onshape parametric CAD)
- Sketch entities: points, curves (Line, Arc, Circle, Ellipse, Spline), constraints, dimensions, profiles
- Extrude features with operation types, extent types, distances, taper angles
- B-Rep data in .smt and .step formats
- Mesh data in .obj format
- Per-step geometry snapshots (STEP + OBJ + PNG at each timeline step)

**The Segmentation Dataset is secondarily useful:**
- 35,680 parts segmented by modeling operation (Extrude, Fillet, Chamfer, etc.)
- Provides face-to-operation mapping — useful for understanding which faces were created by which features

**Preprocessing requirements:**
- Download actual data (~2 GB for reconstruction, ~3 GB for segmentation)
- Parse same JSON format as DeepCAD (shared Fusion 360 API structure)
- Extract B-Rep face references
- Process STEP files for geometric validation

**Usefulness:** **HIGH** — most realistic/complex CAD geometries, with rich parametric data and ground-truth B-Rep. Contains constraints and dimensions that DeepCAD does not.

**Limitations:**
- **NON-COMMERCIAL RESEARCH ONLY** license
- Large download required
- Data not yet on disk — only documentation
- Only sketch-and-extrude (same limitation as DeepCAD for the reconstruction subset)

### 2.4 Drawing2CAD (CAD-VGDrawing)

| Property | Value |
|----------|-------|
| **Location** | `datasets/Drawing2CAD-main/` |
| **License** | MIT (Copyright 2025 lllssc) |
| **Source** | Research code — uses DeepCAD data as underlying CAD models |
| **Publication** | ACM Multimedia 2025 |
| **Format** | SVG engineering drawings + vectorized representations (.npy) + CAD sequences (.h5) |
| **Data status** | **Code/model only — actual data must be downloaded from Google Drive** |

**Actual data format (from [macro.py](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/datasets/Drawing2CAD-main/config/macro.py) and [bi_sequence_dataset.py](file:///c:/Users/shiva/OneDrive/Desktop/cad-ai-workstation-main/datasets/Drawing2CAD-main/dataset/bi_sequence_dataset.py)):**

**SVG Drawing Representation:**
- `svg_raw/`: Engineering drawings in SVG format for each CAD model
- 4 views: `Front`, `Top`, `Right`, `FrontTopRight`
- SVG preprocessed: path simplification, deduplication, reordering, viewbox normalization
- `svg_vec/`: Vectorized SVG sequences as `.npy` files
- SVG commands: `SOS`, `EOS`, `L` (line), `C` (bezier curve)
- SVG args: 8 parameters (start x/y, control points, end x/y)
- Max SVG sequence length: 100 elements

**CAD Sequence Representation:**
- `cad_vec/`: Vectorized CAD sequences in `.h5` format
- CAD commands: `Line`, `Arc`, `Circle`, `EOS`, `SOL`, `Ext` (extrude)
- CAD sketch args: x, y, alpha, f, r (5 params)
- CAD plane args: theta, phi, gamma (3 params)
- CAD transform args: p_x, p_y, p_z, s (4 params)
- CAD extrude args: e1, e2, b, u (4 params)
- Extrude operations: NewBody, Join, Cut, Intersect
- Extent types: OneSide, Symmetric, TwoSides
- Max CAD sequence length: 60 elements, max 10 extrusions, max 6 loops, max 15 curves/loop

**Input options:**
- `1x`: FrontTopRight view only (100 SVG elements)
- `3x`: Front + Top + Right (300 SVG elements)
- `4x`: All four views (400 SVG elements)

**Drawing information:**
- Engineering drawing primitives in vectorized form
- View identification and separation
- Line and bezier curve representation
- Spatial relationships between drawing elements

**Preprocessing requirements:**
- Download actual data from Google Drive (~SVG + vectorized representations)
- The vectorized data is already preprocessed for neural model input
- For our pipeline: extract SVG primitives, parse view structure, identify dimensions
- The raw SVGs need OCR/dimension extraction for engineering interpretation

**Usefulness:** **HIGH for Drawing→CAD pathway** — the only dataset providing explicit 2D drawing → 3D CAD mappings. The shared underlying CAD models with DeepCAD creates a natural bridge.

**Limitations:**
- Data must be downloaded separately
- Based on DeepCAD geometries (same sketch-and-extrude limitation)
- Vectorized representation is designed for neural seq2seq training, not direct engineering interpretation
- No explicit dimension annotations in the vectorized form (dimensions are encoded implicitly in coordinates)
- The model is a PyTorch Transformer — **we are not importing their neural model**

### 2.5 Zenodo 7785223 (Optional Resource)

| Property | Value |
|----------|-------|
| **Relationship** | **Derived from Fusion 360 Gallery dataset** |
| **Contents** | SVG drawings + STEP files + reconstructed 3D wireframes |
| **Status** | Additional ABC dataset test cases included |

**Recommendation:** Treat as **auxiliary reference data** under the Fusion360 pipeline. It provides drawing↔STEP correspondences that complement Drawing2CAD's drawing↔CAD-sequence correspondences. Do NOT count as a fifth dataset.

---

<a id="section-3"></a>
## SECTION 3 — DATASET ROLES

| Dataset | Unique Role | Knowledge Type | Convergence Point |
|---------|-------------|----------------|-------------------|
| **DeepCAD** | Parametric CAD construction sequence knowledge (largest scale) | Feature sequences, sketch geometry, extrude parameters | → CADIR sketch-and-extrude features |
| **BenchCAD** | Executable CAD code exemplars with component family labels | Code templates, family/difficulty metadata, CadQuery→build123d translation patterns | → CADIR via code pattern extraction + few-shot examples |
| **Fusion360** | Realistic CAD complexity with B-Rep and constraints | Rich constraint data, face segmentation, ground-truth geometry, construction sequences | → CADIR with constraint enrichment + geometric validation reference |
| **Drawing2CAD** | 2D drawing → 3D CAD mapping | SVG/vector drawing interpretation, view decomposition, drawing-to-sequence translation | → CADIR via drawing understanding pipeline |

**Non-overlapping value matrix:**

```
                      Sequence  Code  Metadata  Constraints  Drawings  B-Rep  Scale
DeepCAD               ██████    ░░░░  ░░░░░░░░  ░░░░░░░░░░░  ░░░░░░░░  ░░░░  ██████
BenchCAD              ████░░    ████  ██████░░  ░░░░░░░░░░░  ░░░░░░░░  ░░░░  ████░░
Fusion360              ████░░    ░░░░  ░░░░░░░░  ██████████░  ░░░░░░░░  ████  ████░░
Drawing2CAD            ████░░    ░░░░  ░░░░░░░░  ░░░░░░░░░░░  ████████  ░░░░  ████░░
```

---

<a id="section-4"></a>
## SECTION 4 — TWO KNOWLEDGE PATHWAYS

### PATH A — CAD Construction Knowledge

```
DeepCAD (177K sequences) ──┐
                           ├──► Feature Extraction ──► Normalized Feature Sequences
BenchCAD (17.9K examples) ─┤                          │
                           │                          ├──► CADIR Schema Mapping
Fusion360 (8.6K+ designs) ─┘                          │
                                                      ▼
                                              Processed Knowledge Store
                                                      │
                                              ┌───────┴───────┐
                                              │               │
                                         Local Index     Few-Shot
                                         (SQLite)       Examples
                                              │               │
                                              └───────┬───────┘
                                                      ▼
                                            LLM Context Injection
                                                      │
                                                      ▼
                                              CADIR Generation
                                                      │
                                                      ▼
                                         Controlled build123d Interpreter
```

**How it converges to CADIR:**

1. **DeepCAD** sequences are parsed from JSON → extracted as ordered lists of (Sketch, Extrude) pairs with parameters → each maps to a CADIR feature node with `sketch_profiles`, `extrude_config`, and `dependencies`
2. **BenchCAD** CadQuery code is parsed → operation sequences extracted → translated to build123d-compatible feature descriptions → each maps to CADIR feature nodes with `code_pattern` reference
3. **Fusion360** reconstruction JSON follows the same format as DeepCAD → parsed identically but enriches with constraint data and B-Rep face references → CADIR nodes gain `constraints` and `geometry_reference` fields

### PATH B — Drawing Understanding

```
Engineering Drawing / Sketch / Photo
              │
              ▼
    Input Classification
    (drawing vs sketch vs photo)
              │
    ┌─────────┼─────────┐
    │         │         │
    ▼         ▼         ▼
Drawing    Sketch     Photo
Pipeline   Pipeline   Pipeline
    │         │         │
    ▼         ▼         ▼
 SVG/PDF   Image     Image
 Parsing   Analysis  Analysis
    │         │         │
    ▼         ▼         ▼
 View ID   Feature    Shape
 OCR/Dim   Guess      Guess
    │         │         │
    └────┬────┘         │
         │         User Dialog
         │         (dimensions)
         │              │
         └──────┬───────┘
                ▼
      Engineering Interpretation
                │
                ▼
        CAD Feature Plan
                │
                ▼
             CADIR            ◄── Same CADIR schema as Path A
                │
                ▼
      build123d Interpreter
```

**The Drawing2CAD dataset provides:**
- Verified mapping from SVG drawing representations → CAD construction sequences
- View decomposition logic (Front, Top, Right, combined)
- Drawing primitive vocabulary (lines, curves in SVG → sketch operations in CAD)

**Convergence:** Both pathways produce CADIR documents. The CADIR schema is the single canonical representation.

---

<a id="section-5"></a>
## SECTION 5 — DRAWING / SKETCH / PHOTO PIPELINE

### 5.1 Engineering Drawing → CAD

**Most constrained pipeline — richest input information:**

```
Engineering Drawing (SVG/PDF/PNG/DXF)
        │
        ├── If vector format (SVG/DXF): ──► Vector parser (deterministic)
        │                                    │
        │                                    ├── Extract lines, arcs, circles
        │                                    ├── Identify views (front/top/right)
        │                                    ├── Extract dimension annotations
        │                                    ├── Extract centerlines
        │                                    └── Extract section indicators
        │
        ├── If raster format (PNG/JPG): ──► OCR + Line Detection
        │                                    │
        │                                    ├── Tesseract/EasyOCR for dimensions
        │                                    ├── Hough/LSD for line segments
        │                                    ├── Circle detection (Hough circles)
        │                                    └── View region identification
        │
        └── Both paths merge:
                │
                ▼
        Drawing Understanding (LLM-assisted)
                │
                ├── Correlate views (front↔top↔right projections)
                ├── Resolve 3D geometry from 2D projections
                ├── Map dimensions to parametric values
                ├── Identify features (holes, slots, steps, tapers)
                └── Generate feature dependency order
                        │
                        ▼
                CAD Feature Plan
                        │
                        ▼
                     CADIR
```

**Technology choices:**
- **Vector parsing:** `svgpathtools` (Python, pure geometry extraction — no ML needed)
- **OCR:** `easyocr` or `pytesseract` (dimension text extraction)
- **Line detection:** OpenCV `HoughLinesP` (for raster inputs)
- **View correlation:** Deterministic geometric algorithm (projection matching)
- **Feature recognition:** LLM-assisted interpretation of extracted primitives
- **Drawing2CAD dataset:** Provides training signal / retrieval examples for the drawing→feature mapping

### 5.2 Rough Engineering Sketch → CAD

**Less constrained — missing information expected:**

```
Rough Sketch (image)
        │
        ▼
  Sketch Preprocessing
  (contrast, binarize, denoise)
        │
        ▼
  Feature Detection (CV)
  ├── Lines, curves (approximate)
  ├── Circles (approximate)
  ├── Annotations (if legible)
  └── Cross-hatch / section marks
        │
        ▼
  LLM Interpretation (multimodal or description-based)
  ├── "This looks like a bracket with mounting holes"
  ├── Identify likely component type
  ├── Estimate proportions (not exact dims)
  └── List MISSING information
        │
        ▼
  User Clarification Dialog
  ├── "What is the overall length?"
  ├── "How many mounting holes?"
  ├── "What material?"
  └── "What are the hole diameters?"
        │
        ▼
  CAD Feature Plan (with user-provided dims)
        │
        ▼
     CADIR
```

**Key difference from engineering drawings:** The system must explicitly declare what dimensions are missing and prompt the user. The LLM provides shape/feature interpretation, NOT numerical dimensions.

### 5.3 Reference Photograph → User-Assisted CAD

**Least constrained — CANNOT produce exact engineering CAD without user input:**

```
Photograph
        │
        ▼
  Visual Analysis (LLM multimodal or CV)
  ├── Identify object type
  ├── Identify visible features (holes, steps, curves)
  ├── Estimate proportions from visual cues
  └── Identify what CANNOT be determined:
      ├── Hidden geometry (internal cavities, rear features)
      ├── Exact dimensions (no scale reference)
      ├── Material
      ├── Tolerances
      └── Internal features
        │
        ▼
  MANDATORY User Dialog
  ├── Confirm component type
  ├── Provide ALL critical dimensions
  ├── Specify hidden features
  ├── Specify material/tolerance requirements
  └── Approve feature interpretation
        │
        ▼
  Engineering Intent (user-verified)
        │
        ▼
  CAD Feature Plan
        │
        ▼
     CADIR
```

> [!WARNING]
> **The system MUST NOT claim "photo → exact engineering CAD."** A photograph inherently lacks:
> - Exact metric dimensions
> - Hidden/internal geometry
> - Tolerances and surface finish
> - Engineering material specifications
>
> The pipeline must make this explicit in the UI and require user dimensional input before CADIR generation.

---

<a id="section-6"></a>
## SECTION 6 — CADIR INTEGRATION

### 6.1 CADIR Schema Definition (Must Be Created)

Since CADIR does not currently exist in the codebase, it must be defined as a Pydantic schema. The schema must accommodate all information that can be extracted from the four datasets while remaining executable by the build123d interpreter.

**Proposed CADIR Pydantic schema:**

```python
# Conceptual — exact implementation for Gemini Pro High

class CADIRSketchPrimitive:
    type: Literal["line", "arc", "circle", "ellipse", "spline", "rectangle"]
    params: dict  # type-specific: start/end points, radius, center, etc.

class CADIRSketchProfile:
    id: str
    plane: CADIRPlane  # origin + normal + x_axis
    primitives: list[CADIRSketchPrimitive]
    constraints: list[CADIRConstraint]  # optional, from Fusion360

class CADIRFeature:
    id: str
    type: Literal[
        "extrude", "revolve", "sweep", "loft",
        "fillet", "chamfer", "shell", "hole",
        "polar_pattern", "linear_pattern", "mirror",
        "boolean_union", "boolean_cut", "boolean_intersect"
    ]
    params: dict  # type-specific parametric values
    sketch_profile: Optional[str]  # reference to sketch profile ID
    dependencies: list[str]  # IDs of features this depends on
    target_geometry: Optional[str]  # edge/face reference for fillet/chamfer

class CADIRDocument:
    id: str
    name: str
    description: str
    component_family: Optional[str]  # from BenchCAD metadata
    difficulty: Optional[str]  # from BenchCAD metadata
    engineering_intent: dict  # from LLM design interpretation
    sketches: list[CADIRSketchProfile]
    features: list[CADIRFeature]  # ordered by dependency
    parameters: dict[str, float]  # named parametric values
    constraints: list[CADIRConstraint]  # design constraints
    validation_requirements: dict  # engineering validation criteria
```

### 6.2 Dataset → CADIR Mapping

**DeepCAD → CADIR:**
```
DeepCAD JSON entity (type="Sketch")
  → CADIRSketchProfile
    .plane = from entity.transform + entity.reference_plane
    .primitives = from entity.curves (SketchLine→line, SketchArc→arc, SketchCircle→circle)
    .constraints = [] (DeepCAD lacks constraints)

DeepCAD JSON entity (type="ExtrudeFeature")
  → CADIRFeature
    .type = "extrude"
    .params = {
        operation: entity.operation (NewBody→boolean_union, Cut→boolean_cut, ...),
        distance: entity.extent_one.distance.value,
        direction: computed from extent_type,
        taper: entity.extent_one.taper_angle.value
    }
    .sketch_profile = entity.profiles[0].profile
    .dependencies = [previous_feature_id]
```

**BenchCAD → CADIR:**
```
BenchCAD code (CadQuery Python)
  → AST parse
  → Extract operation sequence
  → Map CadQuery operations to CADIR features:
      cq.Workplane("XY").box(l,w,h) → sketch(rectangle) + extrude
      .faces(">Z").hole(d) → CADIRFeature(type="hole", params={diameter: d})
      .edges("|Z").fillet(r) → CADIRFeature(type="fillet", params={radius: r})
      .chamfer(d) → CADIRFeature(type="chamfer", params={distance: d})
  → Metadata: family, variant, difficulty → CADIRDocument metadata
```

**Fusion360 → CADIR:**
```
Fusion360 reconstruction JSON
  → Same parser as DeepCAD (identical entity format)
  → ADDITIONAL: constraints from sketch.constraints → CADIRConstraint
  → ADDITIONAL: dimension data from sketch.dimensions → CADIRDocument.parameters
  → ADDITIONAL: B-Rep face references for feature tracking
```

**Drawing2CAD → CADIR:**
```
Drawing2CAD SVG
  → svgpathtools parse → drawing primitives
  → View identification
  → LLM interpretation → Engineering Intent
  → Feature planning → CAD Feature Plan
  → CAD Feature Plan → CADIR (same schema)

Drawing2CAD vectorized data
  → Reference: SVG drawing → CAD sequence pairs for retrieval
  → Not directly mapped to CADIR (training data format)
```

### 6.3 Required CADIR Extensions vs. Baseline

The CADIR schema must support features beyond sketch-and-extrude to handle complex mechanical components:

| Feature Type | DeepCAD | BenchCAD | Fusion360 | Drawing2CAD | Must Add |
|-------------|---------|----------|-----------|-------------|----------|
| Extrude | ✅ | ✅ | ✅ | ✅ | Core |
| Revolve | ❌ | ✅ (in code) | ❌ (recon.) | ❌ | Yes |
| Fillet | ❌ | ✅ (in code) | ✅ (segm.) | ❌ | Yes |
| Chamfer | ❌ | ✅ (in code) | ✅ (segm.) | ❌ | Yes |
| Hole | ❌ | ✅ (in code) | ❌ | ❌ | Yes |
| Shell | ❌ | ✅ (in code) | ❌ | ❌ | Yes |
| Pattern | ❌ | ✅ (in code) | ❌ | ❌ | Yes |
| Sweep/Loft | ❌ | ✅ (in code) | ❌ | ❌ | Yes |
| Mirror | ❌ | ✅ (in code) | ❌ | ❌ | Yes |

**Conclusion:** BenchCAD is the primary source for feature types beyond sketch-and-extrude. The CadQuery code contains fillet, chamfer, hole, shell, and pattern operations that must be parsed and mapped.

---

<a id="section-7"></a>
## SECTION 7 — RETRIEVAL

### 7.1 Retrieval Justification

**Yes, retrieval is justified.** Reason: The datasets contain ~200K+ construction examples. Loading all into LLM context is impossible. Relevant examples must be selected per-query.

### 7.2 What to Index

| Index Field | Source | Retrieval Use Case |
|-------------|--------|-------------------|
| `component_family` | BenchCAD `.family` | "I need a pulley" → retrieve pulley examples |
| `feature_types` | Extracted from all datasets | "bracket with holes and fillets" → find examples with those features |
| `feature_sequence` | All datasets | Find similar construction strategies |
| `difficulty` | BenchCAD `.difficulty` | Match to complexity level |
| `parameter_ranges` | All datasets | "shaft diameter 25mm" → find examples with similar dimensions |
| `sketch_complexity` | Computed: loop_count × curve_count | Match sketch complexity |
| `operation_count` | Computed | Match overall complexity |
| `text_description` | Generated via LLM for each example | Semantic search on intent |

### 7.3 Retrieval Architecture

**Start with the simplest possible solution:**

```
                    ┌─────────────────────┐
                    │  SQLite Database     │
                    │                     │
                    │  table: cad_examples│
                    │  ├── id             │
                    │  ├── source_dataset │
                    │  ├── family         │
                    │  ├── difficulty     │
                    │  ├── feature_types  │ ← JSON array
                    │  ├── feature_count  │
                    │  ├── param_summary  │ ← JSON
                    │  ├── cadir_json     │ ← full CADIR
                    │  ├── description    │
                    │  └── code_snippet   │ ← build123d if available
                    └─────────────────────┘
                              │
                     Query: SQL WHERE + text search
                              │
                    ┌─────────────────────┐
                    │  Optional: Embedding │
                    │  (Phase 2 only)      │
                    │  sentence-transformers│
                    │  all-MiniLM-L6-v2    │
                    │  → cosine similarity │
                    └─────────────────────┘
```

**Phase 1:** SQLite with structured field queries (family, difficulty, feature_types LIKE, parameter ranges). This requires zero additional infrastructure.

**Phase 2 (only if SQL retrieval proves insufficient):** Add embedding-based semantic search using `sentence-transformers/all-MiniLM-L6-v2` (90MB model, CPU inference, fast). Store embeddings in SQLite as BLOB, compute cosine similarity on small candidate sets.

**DO NOT introduce:**
- Vector databases (Chroma, Pinecone, Milvus, Qdrant)
- Redis for retrieval
- Elasticsearch
- Any external retrieval service

### 7.4 Retrieval Query Flow

```
User Prompt: "Create a stepped shaft with keyway, 50mm diameter"
        │
        ▼
LLM extracts structured query:
  family: "shaft"
  features: ["extrude", "chamfer", "boolean_cut"]
  keywords: "stepped", "keyway"
  params: {diameter: 50}
        │
        ▼
SQL query:
  SELECT * FROM cad_examples
  WHERE family LIKE '%shaft%'
    AND feature_types LIKE '%extrude%'
  ORDER BY difficulty ASC
  LIMIT 5
        │
        ▼
Retrieved CADIR examples injected into LLM context
```

---

<a id="section-8"></a>
## SECTION 8 — TRAINING

### 8.1 Training Decision Matrix

| Phase | Approach | Justified Now? | Reason |
|-------|----------|----------------|--------|
| Phase 1 | No training — retrieval + few-shot | **YES** | Zero training cost, immediately testable, establishes baseline |
| Phase 2 | Supervised fine-tuning on CADIR generation | **NOT YET** | Need Phase 1 benchmark data first |
| Phase 3 | Specialized CAD model | **NO** | RTX 3050 6GB insufficient for meaningful training |
| Phase 4 | Reinforcement learning from CAD execution feedback | **NO** | Research-grade, far future |

### 8.2 Why NOT to Fine-Tune Now

1. **No CADIR ground truth exists yet.** The CADIR schema must be created first, then datasets processed into CADIR format. Only then can training data be constructed.

2. **RTX 3050 6GB is insufficient** for fine-tuning 8B parameter models. Even QLoRA of Qwen3:8b requires ~10GB VRAM minimum for stable training.

3. **Retrieval + few-shot has not been benchmarked.** Fine-tuning is justified only after proving that retrieval alone is insufficient.

4. **CadQuery→build123d translation quality is unverified.** Training on incorrectly translated examples would be counterproductive.

### 8.3 Recommended Path

```
NOW (P0-P4):
  Create CADIR schema
  Build dataset adapters
  Extract and validate CADIR examples
  Build SQLite index

NEXT (P5-P7):
  Retrieval-augmented generation
  Few-shot CADIR examples in LLM context
  Benchmark against baseline

LATER (P8+, only if benchmarks justify):
  Consider cloud-based fine-tuning
  Consider distillation from cloud LLM to local model
  Consider parameter-efficient training on smaller sub-tasks
```

---

<a id="section-9"></a>
## SECTION 9 — COMPLEX CAD GENERATION (10 Components)

### 9.1 Stepped Shaft

| Property | Detail |
|----------|--------|
| **Feature sequence** | Base cylinder → step down (smaller cylinder, boolean union) → step down again → keyway (rectangle profile, boolean cut) → chamfer on ends → fillet at step transitions |
| **Relevant datasets** | DeepCAD (revolve/extrude sequences), BenchCAD (shaft family, CadQuery code) |
| **Retrieved knowledge** | BenchCAD shaft family examples → feature ordering, diameter stepping patterns, keyway geometry |
| **CADIR representation** | `features: [extrude(cylinder, d=50, h=120), extrude(cylinder, d=35, h=80, offset=120, op=union), cut(rectangle_profile, keyway_dims), chamfer(end_edges, 2mm), fillet(step_edges, 3mm)]` |
| **Validation** | Solid/manifold, correct step diameters, keyway depth/width per standard, overall length |

### 9.2 Flanged Shaft

| Property | Detail |
|----------|--------|
| **Feature sequence** | Base cylinder (shaft) → flange disc (larger cylinder, union) → bolt circle holes (polar pattern of holes) → central bore (optional) → chamfers → fillets |
| **Relevant datasets** | BenchCAD (flange family), DeepCAD (extrude sequences) |
| **Retrieved knowledge** | Flange standards (bolt circle diameter, number of holes), construction order |
| **CADIR** | `features: [extrude(cylinder_shaft), extrude(cylinder_flange, op=union), polar_pattern(hole, count=6, bolt_circle_r=45), chamfer, fillet]` |
| **Validation** | Bolt pattern symmetry, hole-to-edge clearance, shaft/flange concentricity |

### 9.3 Pulley

| Property | Detail |
|----------|--------|
| **Feature sequence** | Revolve profile (V-groove cross-section) → central bore → keyway → set screw hole → hub fillet |
| **Relevant datasets** | BenchCAD (pulley family), DeepCAD (revolve operations if available) |
| **Retrieved knowledge** | V-groove profiles per belt standard, hub diameter ratios |
| **CADIR** | `features: [revolve(v_groove_profile), hole(bore), cut(keyway), hole(set_screw, radial), fillet]` |
| **Validation** | Groove angle per standard, bore concentricity, keyway dimensions per shaft standard |

### 9.4 Mounting Bracket

| Property | Detail |
|----------|--------|
| **Feature sequence** | Base plate (box extrude) → vertical wall (box extrude, union) → gusset/rib (triangle profile extrude, union) → mounting holes (through holes) → fillets at wall-plate junction |
| **Relevant datasets** | BenchCAD (bracket family), Fusion360 (complex geometry examples) |
| **Retrieved knowledge** | L-bracket patterns, gusset placement, hole patterns |
| **CADIR** | `features: [extrude(base_plate), extrude(wall, op=union), extrude(gusset, op=union), hole(mount_hole, count=4), fillet(junction_edges)]` |
| **Validation** | Wall perpendicularity, gusset connectivity, hole clearance |

### 9.5 Bearing Housing

| Property | Detail |
|----------|--------|
| **Feature sequence** | Base block → central bore (bearing seat) → bearing retainer groove → mounting holes → oil channel (optional) → fillets → chamfers |
| **Relevant datasets** | BenchCAD (housing family), Fusion360 (complex construction) |
| **Retrieved knowledge** | Bearing bore tolerances, retainer groove dimensions, mounting patterns |
| **CADIR** | `features: [extrude(base_block), hole(bearing_bore, precision), cut(retainer_groove), polar_pattern(mount_holes), chamfer, fillet]` |
| **Validation** | Bore diameter tolerance, concentricity, adequate wall thickness, mounting pattern symmetry |

### 9.6 Gearbox Housing

| Property | Detail |
|----------|--------|
| **Feature sequence** | Shell body (box → shell) → bearing bores (multiple) → shaft passages → mounting flange → bolt holes → drain/fill plugs → ribs → fillets |
| **Relevant datasets** | Fusion360 (complex multi-feature), BenchCAD (housing family) |
| **Retrieved knowledge** | Wall thickness standards, bearing bore alignment, rib placement |
| **CADIR** | `features: [extrude(outer_box), shell(wall_thickness=5), hole(bearing_bore_1), hole(bearing_bore_2), extrude(mounting_flange), pattern(bolt_holes), extrude(rib, op=union), fillet]` |
| **Validation** | Shaft center distances, bearing alignment, wall structural adequacy, draft angles for casting |

### 9.7 Flange

| Property | Detail |
|----------|--------|
| **Feature sequence** | Disc (cylinder extrude) → central bore → raised face (concentric cylinder, union) → bolt circle holes → gasket groove (optional) → chamfers |
| **Relevant datasets** | BenchCAD (flange family), DeepCAD (extrude sequences) |
| **Retrieved knowledge** | ASME B16.5 / DIN flange standards, pressure classes |
| **CADIR** | `features: [extrude(disc), hole(bore), extrude(raised_face, op=union), polar_pattern(bolt_holes, count=8), cut(gasket_groove), chamfer]` |
| **Validation** | Bolt circle per standard, bore per pipe size, raised face dimensions |

### 9.8 Impeller

| Property | Detail |
|----------|--------|
| **Feature sequence** | Hub (cylinder) → shroud disc → blades (loft or sweep along curved path, polar pattern) → bore → keyway → balancing holes (optional) |
| **Relevant datasets** | Fusion360 (complex swept geometry), BenchCAD (if impeller family exists) |
| **Retrieved knowledge** | Blade profile curves, outlet angle, number of blades, hub-to-tip ratio |
| **CADIR** | `features: [extrude(hub_cylinder), extrude(shroud_disc), polar_pattern(loft(blade_profile, guide_curve), count=6), hole(bore), cut(keyway)]` |
| **Validation** | Blade symmetry, hub-shroud connectivity, bore concentricity, dynamic balance consideration |

### 9.9 Mechanical Fixture

| Property | Detail |
|----------|--------|
| **Feature sequence** | Base plate → vertical supports (multiple extrusions) → clamping slots (cuts) → T-slot (profile cut) → dowel pin holes → clamping screw holes → chamfers |
| **Relevant datasets** | BenchCAD (fixture family), Fusion360 (multi-feature) |
| **Retrieved knowledge** | T-slot standards, dowel pin patterns, clamping strategies |
| **CADIR** | `features: [extrude(base_plate), extrude(support_walls, op=union), cut(clamping_slots), cut(t_slot_profile), hole(dowel_pins), hole(clamp_screws), chamfer]` |
| **Validation** | Slot dimensions, support wall thickness, hole positioning accuracy |

### 9.10 Multi-Feature Support Bracket

| Property | Detail |
|----------|--------|
| **Feature sequence** | L-shaped base (two perpendicular extrusions) → triangular gusset rib → lightening pocket (cut) → stiffener rib → mounting holes (multiple patterns) → counterbore holes → fillets → chamfers |
| **Relevant datasets** | BenchCAD (bracket family), Fusion360 (segmentation for feature types) |
| **Retrieved knowledge** | Rib-to-wall ratios, pocket corner radii, counterbore standards |
| **CADIR** | `features: [extrude(horizontal_plate), extrude(vertical_plate, op=union), extrude(gusset, op=union), cut(lightening_pocket), extrude(stiffener, op=union), linear_pattern(mount_holes), counterbore_hole(attach_holes), fillet, chamfer]` |
| **Validation** | Feature interference, adequate material at all cross-sections, hole-to-edge clearance, fillet radii feasibility |

---

<a id="section-10"></a>
## SECTION 10 — LANGGRAPH INTEGRATION

### 10.1 Current Pipeline (From README)

```
User Prompt → Supervisor → Design Agent → CAD Executor → Geometry Validator
         ↑                                                          │
         └──────────── retry loop (max 5x) ◄────────────────────────┘
         ↓ (on success)
DFM → Engineering → Cost → Safety → Alternatives → CAM → Documentation → Export
```

### 10.2 Enhanced Pipeline with Dataset Intelligence

```
User Prompt
     │
     ▼
┌─────────────┐
│  Supervisor  │  ← UNCHANGED (intent parsing)
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│  Input Classifier     │  ← NEW NODE
│  (text vs drawing     │
│   vs sketch vs photo) │
└──────┬───────────────┘
       │
       ├── If text prompt ──────────────────────────────────────────┐
       │                                                            │
       ├── If engineering drawing ──► Drawing Understanding ────────┤
       │                              (OCR, view parse, dims)       │
       │                                                            │
       ├── If rough sketch ──► Sketch Interpretation ───────────────┤
       │                       (CV + LLM + user dialog)             │
       │                                                            │
       └── If photo ──► Photo Analysis ─────────────────────────────┤
                        (LLM visual + MANDATORY user dims)          │
                                                                    │
                                                                    ▼
                                                    ┌───────────────────────┐
                                                    │  Engineering Intent   │
                                                    │  (unified from any    │
                                                    │   input pathway)      │
                                                    └───────┬───────────────┘
                                                            │
                                                            ▼
                                               ┌────────────────────────┐
                                               │  Dataset Retrieval     │  ← NEW NODE
                                               │  (query SQLite index,  │
                                               │   find similar CADIR   │
                                               │   examples)            │
                                               └───────┬────────────────┘
                                                       │
                                                       ▼
                                               ┌────────────────────────┐
                                               │  Design Agent          │  ← MODIFIED
                                               │  (now receives:        │
                                               │   - engineering intent │
                                               │   - retrieved examples │
                                               │   - CADIR schema)      │
                                               │  OUTPUT: CADIR document│
                                               └───────┬────────────────┘
                                                       │
                                                       ▼
                                               ┌────────────────────────┐
                                               │  CADIR Validator       │  ← NEW NODE
                                               │  (schema validation,   │
                                               │   dependency check,    │
                                               │   parameter ranges)    │
                                               └───────┬────────────────┘
                                                       │
                                                       ▼
                                               ┌────────────────────────┐
                                               │  CADIR→build123d       │  ← NEW NODE
                                               │  Interpreter           │
                                               │  (deterministic code   │
                                               │   generation from      │
                                               │   validated CADIR)     │
                                               └───────┬────────────────┘
                                                       │
                                                       ▼
                                               ┌────────────────────────┐
                                               │  CAD Executor          │  ← UNCHANGED
                                               │  (sandboxed subprocess)│
                                               └───────┬────────────────┘
                                                       │
                                                       ▼
                                               ┌────────────────────────┐
                                               │  Geometry Validator    │  ← ENHANCED
                                               │  (existing trimesh +   │
                                               │   OCCT topology check) │
                                               └───────┬────────────────┘
                                                       │
                                            ┌──────────┴──────────┐
                                            │ Valid?               │
                                            │                      │
                                          YES                     NO
                                            │                      │
                                            ▼                      ▼
                                    Downstream Agents    ┌──────────────────┐
                                    (DFM, Engineering,   │  CADIR Repair    │ ← NEW
                                     Cost, Safety, etc.) │  Agent           │
                                    ← UNCHANGED          │  (dataset-       │
                                                         │   informed       │
                                                         │   error repair)  │
                                                         └──────┬───────────┘
                                                                │
                                                                ▼
                                                         Back to CADIR
                                                         Validator
                                                         (retry loop)
```

### 10.3 When Dataset Retrieval Occurs

**Answer: B + D — Inside Design Agent context AND during repair.**

| Retrieval Point | Purpose | Query |
|-----------------|---------|-------|
| Before Design Agent | Provide relevant construction examples | "Find me 3-5 examples similar to the engineering intent" |
| During CADIR Repair | Find working alternatives for failed features | "The fillet on edge X failed — find examples where fillet succeeded on similar geometry" |

Retrieval should NOT happen:
- Before the Supervisor (too early, intent not yet parsed)
- After CADIR generation but before execution (too late, CADIR already fixed)
- During downstream agents (DFM, Cost, etc.) — they don't modify geometry

---

<a id="section-11"></a>
## SECTION 11 — SELF-HEALING

### 11.1 Current Self-Healing

The existing retry loop (max 5 retries) works as:
```
CAD execution failure → error message → Design Agent regenerates entire code → retry
```

This is brute-force — the LLM has no context about *why* the failure occurred or what alternatives exist.

### 11.2 Dataset-Enhanced Self-Healing

```
CADIR Execution
     │
     ▼
  FAILURE
     │
     ▼
Error Classification
├── Schema error (CADIR malformed) → CADIR Validator fixes
├── Feature error (edge not found, face invalid) → Feature-level repair
├── Boolean error (subtraction produces empty) → Operation repair
├── Topology error (non-manifold, self-intersect) → Geometry repair
└── Parameter error (fillet radius too large) → Parameter adjustment
     │
     ▼
Retrieval Query: "feature type = {failed_feature_type},
                  similar_geometry = {context}"
     │
     ▼
Retrieved examples show WORKING patterns for similar features
     │
     ▼
LLM Repair Agent:
  "The fillet on the step transition failed because radius (5mm)
   exceeds the step height (3mm). Retrieved example #42 shows
   a successful fillet with radius = 0.4 × step_height.
   Reducing fillet radius to 1.2mm."
     │
     ▼
Modified CADIR → Re-execute → Validate
```

### 11.3 Specific Repair Strategies

| Failure Type | Dataset-Informed Repair |
|-------------|------------------------|
| Fillet radius too large | Retrieve similar examples → compute successful radius/feature-size ratios |
| Boolean cut produces empty solid | Retrieve examples with same cut pattern → verify cut depth/position |
| Hole too close to edge | Retrieve examples with similar hole patterns → check minimum edge distances |
| Sketch profile not closed | Retrieve similar sketches → compare primitive connectivity |
| Feature reference lost after previous feature | Retrieve examples → find alternative reference strategies |

---

<a id="section-12"></a>
## SECTION 12 — DATA PIPELINE

### 12.1 Complete Pipeline

```
┌─────────────────────────────────────────────────────────┐
│ STAGE 1: Raw Storage (IMMUTABLE)                        │
│                                                          │
│ datasets/                                               │
│ ├── DeepCAD/cad_json/         ← 77,720 JSON files      │
│ ├── BenchCAD/...code_gen/     ← 17,900 Arrow records    │
│ ├── Fusion360Gallery/...      ← documentation only      │
│ └── Drawing2CAD-main/         ← code only, data TBD     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 2: Parse (Dataset-Specific Adapters)              │
│                                                          │
│ DeepCAD Adapter:                                         │
│   JSON → parse entities → extract Sketch + Extrude      │
│                                                          │
│ BenchCAD Adapter:                                        │
│   Arrow → load via PyArrow → extract code + metadata    │
│   CadQuery code → AST parse → operation sequence        │
│                                                          │
│ Fusion360 Adapter:                                       │
│   JSON → parse entities (same format as DeepCAD)         │
│   + extract constraints, dimensions, B-Rep refs          │
│                                                          │
│ Drawing2CAD Adapter:                                     │
│   SVG → svgpathtools → drawing primitives               │
│   NPY → vectorized drawing sequences                     │
│   H5 → vectorized CAD sequences                          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 3: Validate                                        │
│                                                          │
│ - Schema validation (required fields present)            │
│ - Parameter range checks (no NaN, no extreme values)     │
│ - Sequence completeness (sketches referenced by extrudes)│
│ - Geometry plausibility (positive dimensions, etc.)      │
│ - For BenchCAD: syntax-check CadQuery code               │
│                                                          │
│ OUTPUT: validation report + filtered valid set           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 4: Extract & Normalize                             │
│                                                          │
│ Feature Extractor:                                       │
│   - operation type, parameters                           │
│   - sketch primitive counts                              │
│   - feature dependency graph                             │
│   - bounding box estimates                               │
│                                                          │
│ Normalizer:                                              │
│   - unit conversion (Onshape→mm or user preference)      │
│   - coordinate normalization                             │
│   - operation name normalization                          │
│     (NewBodyFeatureOperation → "new_body")               │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 5: CADIR Mapping                                   │
│                                                          │
│ CadirMapper:                                             │
│   normalized_features → CADIRDocument                    │
│   - create sketch profiles                               │
│   - create feature nodes                                 │
│   - establish dependencies                               │
│   - attach metadata (source, family, difficulty)         │
│                                                          │
│ BenchCAD Special Path:                                   │
│   CadQuery code → CadQuery-to-build123d translator      │
│   → build123d code snippets stored as reference          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 6: Index & Store                                   │
│                                                          │
│ SQLite database: datasets/processed/knowledge.db         │
│                                                          │
│ Tables:                                                  │
│   cad_examples:                                          │
│     id, source, family, difficulty,                      │
│     feature_types (JSON), feature_count,                 │
│     param_summary (JSON), description,                   │
│     cadir_json, code_snippet,                            │
│     sketch_complexity, operation_count                   │
│                                                          │
│   drawing_examples: (from Drawing2CAD)                   │
│     id, svg_path, view_type,                            │
│     primitive_count, linked_cad_id                       │
│                                                          │
│ Flat files: datasets/processed/{dataset}/                │
│   Individual CADIR JSON documents                        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│ STAGE 7: Retrieve                                        │
│                                                          │
│ Query interface:                                         │
│   retrieve_similar(                                      │
│     family="shaft",                                      │
│     feature_types=["extrude", "chamfer"],                │
│     difficulty="medium",                                 │
│     top_k=5                                              │
│   ) → list[CADIRDocument]                                │
│                                                          │
│ Used by:                                                 │
│   - Design Agent (during CADIR generation)               │
│   - Repair Agent (during self-healing)                   │
│   - Drawing Pipeline (for drawing→CAD examples)          │
└─────────────────────────────────────────────────────────┘
```

---

<a id="section-13"></a>
## SECTION 13 — DIRECTORY STRUCTURE

### 13.1 Proposed Additions (Preserving Existing)

```diff
 cad-ai-workstation-main/
 ├── backend/
 │   ├── main.py                    # MODIFY: add dataset health endpoint
 │   ├── config.py                  # MODIFY: add dataset config settings
+│   ├── agents/                    # CREATE (referenced by main.py but missing)
+│   │   ├── __init__.py
+│   │   ├── state.py              # AgentState TypedDict with CADIR fields
+│   │   ├── graph.py              # LangGraph StateGraph
+│   │   ├── supervisor.py         # Intent parsing
+│   │   ├── input_classifier.py   # NEW: text/drawing/sketch/photo routing
+│   │   ├── design_agent.py       # CADIR generation with dataset context
+│   │   ├── cadir_interpreter.py  # NEW: CADIR→build123d deterministic code gen
+│   │   ├── validator_agent.py    # Geometry validation + OCCT checks
+│   │   ├── cadir_repair_agent.py # NEW: dataset-informed CADIR repair
+│   │   ├── dfm_agent.py
+│   │   ├── engineering_agent.py
+│   │   ├── cost_agent.py
+│   │   ├── safety_agent.py
+│   │   ├── alternatives_agent.py
+│   │   ├── cam_agent.py
+│   │   └── doc_agent.py
+│   ├── api/                      # CREATE (referenced by main.py but missing)
+│   │   └── routes/
+│   │       ├── __init__.py
+│   │       ├── sessions.py
+│   │       ├── design.py
+│   │       ├── export.py
+│   │       └── websocket.py
 │   ├── cad/
 │   │   ├── executor.py            # DO NOT TOUCH
 │   │   ├── exporter.py            # DO NOT TOUCH
 │   │   ├── feature_tree.py        # EXTEND: add CADIR-aware feature tree
 │   │   ├── validator.py           # ENHANCE: add OCCT topology checks
+│   │   └── cadir/
+│   │       ├── __init__.py
+│   │       ├── schema.py          # CADIR Pydantic models
+│   │       ├── validator.py       # CADIR schema + dependency validation
+│   │       └── interpreter.py     # CADIR→build123d code generation
+│   ├── datasets/                  # NEW: dataset adapter layer
+│   │   ├── __init__.py
+│   │   ├── base.py               # Abstract DatasetAdapter base class
+│   │   ├── registry.py           # Dataset registry + availability checks
+│   │   ├── deepcad_adapter.py
+│   │   ├── benchcad_adapter.py
+│   │   ├── fusion360_adapter.py
+│   │   ├── drawing2cad_adapter.py
+│   │   ├── feature_extractor.py  # Cross-dataset feature extraction
+│   │   ├── cadir_mapper.py       # Features → CADIR mapping
+│   │   └── cadquery_translator.py # CadQuery→build123d translation
+│   ├── retrieval/                 # NEW: retrieval layer
+│   │   ├── __init__.py
+│   │   ├── index.py              # SQLite index build/query
+│   │   ├── query.py              # Structured query interface
+│   │   └── ranker.py             # Result ranking/filtering
+│   ├── drawing/                   # NEW: drawing understanding
+│   │   ├── __init__.py
+│   │   ├── parser.py             # SVG/DXF/image parsing
+│   │   ├── view_identifier.py    # View type detection
+│   │   ├── dimension_extractor.py # OCR + dimension parsing
+│   │   └── feature_recognizer.py # Drawing→feature interpretation
 │   ├── db/                        # DO NOT RESTRUCTURE
 │   ├── tasks/                     # DO NOT RESTRUCTURE
 │   └── utils/
 │       ├── llm.py                 # EXTEND: add Ollama local model support
 │       └── storage.py             # DO NOT TOUCH
 │
 ├── datasets/                      # RAW DATASETS — IMMUTABLE
 │   ├── DeepCAD/                   # ✅ exists
 │   ├── BenchCAD/                  # ✅ exists
 │   ├── Fusion360Gallery/          # ✅ exists (docs only, data TBD)
 │   ├── Drawing2CAD-main/          # ✅ exists (code only, data TBD)
+│   └── processed/                 # NEW: processed/derived data
+│       ├── deepcad/               # CADIR JSONs from DeepCAD
+│       ├── benchcad/              # CADIR JSONs + translated code from BenchCAD
+│       ├── fusion360/             # CADIR JSONs from Fusion360
+│       ├── drawing2cad/           # Drawing-CAD pairs
+│       └── knowledge.db           # SQLite retrieval index
 │
+├── scripts/                       # NEW: preprocessing scripts
+│   ├── preprocess_deepcad.py
+│   ├── preprocess_benchcad.py
+│   ├── preprocess_fusion360.py
+│   ├── preprocess_drawing2cad.py
+│   ├── build_index.py
+│   ├── validate_datasets.py
+│   └── benchmark.py
+│
+├── tests/                         # NEW: test suite
+│   ├── test_cadir_schema.py
+│   ├── test_dataset_adapters.py
+│   ├── test_cadir_interpreter.py
+│   ├── test_retrieval.py
+│   └── test_benchmark.py
 │
 ├── frontend/                      # DO NOT MODIFY until features reach UI
 ├── infra/                         # DO NOT MODIFY
 └── docker-compose.dev.yml         # DO NOT MODIFY
```

### 13.2 Files NOT to Touch

| File | Reason |
|------|--------|
| `backend/cad/executor.py` | Core sandbox architecture |
| `backend/cad/exporter.py` | Working STEP→STL→GLB |
| `backend/utils/storage.py` | Working MinIO integration |
| `backend/tasks/celery_app.py` | Working Celery config |
| `backend/db/base.py` | Working SQLAlchemy engine |
| `docker-compose.dev.yml` | Working infrastructure |
| `docker-compose.yml` | Production config |
| `frontend/*` | All frontend files until Phase 7+ |
| `datasets/DeepCAD/*` | Raw data — immutable |
| `datasets/BenchCAD/*` | Raw data — immutable |
| `datasets/Fusion360Gallery/*` | Raw data — immutable |
| `datasets/Drawing2CAD-main/*` | Raw data — immutable |

---

<a id="section-14"></a>
## SECTION 14 — WINDOWS WORKFLOW

### 14.1 Dataset Inspection Commands

```powershell
# Check dataset sizes
Get-ChildItem -Recurse datasets\DeepCAD\cad_json -File | Measure-Object -Property Length -Sum
Get-ChildItem -Recurse datasets\BenchCAD -File | Measure-Object -Property Length -Sum
Get-ChildItem -Recurse datasets\Fusion360Gallery -File | Measure-Object -Property Length -Sum
Get-ChildItem -Recurse datasets\Drawing2CAD-main -File | Measure-Object -Property Length -Sum

# Count DeepCAD JSON files
(Get-ChildItem -Recurse datasets\DeepCAD\cad_json -Filter "*.json").Count

# Inspect DeepCAD sample
Get-Content datasets\DeepCAD\cad_json\0002\00027103.json | python -m json.tool | Select-Object -First 50

# Check disk space
Get-PSDrive C | Select-Object Used, Free
```

### 14.2 Environment Setup

```powershell
# Create venv (if not exists)
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install current dependencies + new ones
pip install -r requirements.txt

# Additional dependencies for dataset processing (add to requirements.txt)
pip install pyarrow datasets svgpathtools easyocr pydantic-settings
```

### 14.3 Download Missing Data

```powershell
# Fusion360 Reconstruction Dataset (~2 GB)
Invoke-WebRequest -Uri "https://fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/reconstruction/r1.0.1/r1.0.1.zip" -OutFile "datasets\Fusion360Gallery\r1.0.1.zip"
Expand-Archive datasets\Fusion360Gallery\r1.0.1.zip -DestinationPath datasets\Fusion360Gallery\reconstruction

# Drawing2CAD data — must download from Google Drive manually
# URL: https://drive.google.com/drive/folders/1t9uO2iFh1eVDXRCKUEonKPBu8WGYA8wU
# Download svg_raw, svg_vec, cad_vec folders → datasets\Drawing2CAD-main\data\
```

### 14.4 Preprocessing Commands

```powershell
# Preprocess datasets (run from project root)
python scripts\preprocess_deepcad.py --input datasets\DeepCAD\cad_json --output datasets\processed\deepcad
python scripts\preprocess_benchcad.py --input datasets\BenchCAD --output datasets\processed\benchcad
python scripts\preprocess_fusion360.py --input datasets\Fusion360Gallery\reconstruction --output datasets\processed\fusion360
python scripts\preprocess_drawing2cad.py --input datasets\Drawing2CAD-main\data --output datasets\processed\drawing2cad

# Build retrieval index
python scripts\build_index.py --processed-dir datasets\processed --output datasets\processed\knowledge.db

# Validate
python scripts\validate_datasets.py --db datasets\processed\knowledge.db

# Run benchmarks
python scripts\benchmark.py --baseline --output results\baseline.json
python scripts\benchmark.py --enhanced --output results\enhanced.json
```

### 14.5 Testing

```powershell
# Run tests
python -m pytest tests\ -v
```

---

<a id="section-15"></a>
## SECTION 15 — LICENSING

| Dataset | License | Research Use | Commercial Use | Redistribution | Model Training | Notes |
|---------|---------|-------------|----------------|----------------|----------------|-------|
| **DeepCAD** | MIT | ✅ Unrestricted | ✅ Permitted | ✅ Permitted | ✅ Permitted | Copyright 2022 Rundi Wu. Parsed from Onshape public documents via ABC dataset. |
| **BenchCAD** | **UNVERIFIED** | ⚠️ Assume yes | ⚠️ Unknown | ⚠️ Unknown | ⚠️ Unknown | `dataset_info.json` has empty license field. **MUST verify on HuggingFace before any commercial use.** |
| **Fusion 360 Gallery** | **Autodesk Custom — Non-Commercial Only** | ✅ Non-commercial research only | ❌ PROHIBITED | ⚠️ Modified subsets only, with restrictions | ⚠️ Only for non-commercial research | Items 1-3 restrict to non-commercial research. Item 11: employer is also bound. Item 4: no re-association with creators. |
| **Drawing2CAD** | MIT | ✅ Unrestricted | ✅ Permitted | ✅ Permitted | ✅ Permitted | Copyright 2025 lllssc. Based on DeepCAD data (also MIT). |
| **Zenodo 7785223** | Not yet verified | ⚠️ Check | ⚠️ Check | ⚠️ Check | ⚠️ Check | Derived from Fusion360 Gallery — may inherit Autodesk restrictions. |

> [!CAUTION]
> **Fusion 360 Gallery Dataset is non-commercial research only.** If this project ever has commercial ambitions, all Fusion360-derived data must be kept separate and removable. The system must function without it.
>
> **BenchCAD license is unverified.** The HuggingFace dataset page must be checked before any reliance on this data for production use.

---

<a id="section-16"></a>
## SECTION 16 — PERFORMANCE

### 16.1 Hardware Constraints

| Resource | Capacity | Constraint |
|----------|----------|------------|
| GPU | RTX 3050 6GB VRAM | LLM inference only; no training |
| CPU | Assumed 8+ cores | Dataset processing, build123d execution |
| RAM | Assumed 16-32 GB | Dataset loading, index queries |
| Disk | Must verify free space | ~10 GB for all datasets + processed |

### 16.2 Memory Budget

| Operation | Memory Use | Location |
|-----------|-----------|----------|
| Ollama Qwen3:8b | ~5.5 GB VRAM | GPU |
| Ollama DeepSeek-R1:8b | ~5.5 GB VRAM | GPU |
| SQLite retrieval index | ~100 MB RAM | CPU |
| Dataset preprocessing | ~2 GB RAM peak | CPU |
| build123d execution | ~500 MB RAM | CPU (subprocess) |
| Frontend + API | ~500 MB RAM | CPU |

**Constraint:** Only ONE Ollama model loaded at a time. Model switching adds 10-30 seconds latency.

### 16.3 What MUST Stay on CPU

- All dataset parsing and preprocessing
- SQLite index queries
- CADIR schema validation
- build123d CAD execution
- Geometry validation
- Feature extraction
- CadQuery→build123d translation

### 16.4 What Goes to GPU

- LLM inference (Ollama): intent parsing, CADIR generation, repair reasoning
- Nothing else — the GPU is fully committed to LLM inference

### 16.5 Token Budget

For 8B models with 8K context window:

| Context Segment | Token Budget |
|-----------------|-------------|
| System prompt (CADIR schema + instructions) | ~1,500 tokens |
| User prompt + engineering intent | ~500 tokens |
| Retrieved examples (3-5 CADIR documents) | ~2,000-3,000 tokens |
| CADIR output generation | ~2,000 tokens |
| **Total** | ~6,000-7,000 tokens |

**This fits within 8K context.** Do NOT exceed 5 retrieved examples. Each CADIR example should be truncated to essential features only (no full coordinate sets).

---

<a id="section-17"></a>
## SECTION 17 — BENCHMARK

### 17.1 Test Components by Complexity Level

| Level | Components | Features |
|-------|-----------|----------|
| L1 - Trivial | Box, Cylinder, Sphere | 1 primitive |
| L2 - Simple | Box with hole, Cylinder with chamfer | 2-3 features |
| L3 - Moderate | Bracket with holes + fillets, Stepped cylinder | 4-6 features |
| L4 - Complex | Flanged shaft, Pulley with keyway, Mounting bracket with ribs | 7-10 features |
| L5 - Advanced | Bearing housing, Gearbox housing, Impeller | 10+ features |

### 17.2 Test Prompts (Exact Wording)

```
L1-1: "Create a rectangular box 100mm × 60mm × 40mm"
L1-2: "Create a cylinder with diameter 50mm and height 80mm"

L2-1: "Create a rectangular block 100×60×40mm with a 20mm through-hole centered on the top face"
L2-2: "Create a cylinder diameter 50mm, height 80mm, with a 2mm chamfer on the top edge"

L3-1: "Create an L-shaped bracket: base plate 100×60×10mm, vertical wall 60×80×10mm, with four 8mm mounting holes in the base plate and 3mm fillets at the junction"
L3-2: "Create a stepped cylinder: bottom section diameter 50mm height 30mm, top section diameter 30mm height 50mm, with 2mm fillets at the step"

L4-1: "Create a flanged shaft: shaft diameter 30mm length 100mm, flange diameter 80mm thickness 15mm at one end, with six 10mm bolt holes on a 60mm bolt circle, 1mm chamfers on shaft ends"
L4-2: "Create a V-belt pulley: outer diameter 120mm, V-groove with 38° included angle, hub diameter 50mm, 25mm bore with keyway 8mm wide × 4mm deep"

L5-1: "Create a bearing housing: base block 120×80×60mm, 62mm bearing bore centered, four M10 mounting holes on corners with 15mm edge distance, 2mm fillets on all external edges"
L5-2: "Create a support bracket: horizontal base 150×80×12mm, vertical back plate 80×100×12mm, two triangular gusset ribs 8mm thick, four M8 mounting holes in base, two M10 holes in back plate, lightening pocket in back plate, 3mm fillets on all junctions"
```

### 17.3 Metrics

| Metric | How Measured | Baseline | Target |
|--------|-------------|----------|--------|
| CADIR Schema Valid % | Pydantic validation | N/A (no CADIR yet) | >95% |
| CAD Execution Success % | build123d subprocess exit code 0 | Measure current | +20% improvement |
| OCCT Valid Solid % | trimesh watertight + manifold | Measure current | +15% improvement |
| Feature Completion % | Expected features vs actual features in output | Manual count | >80% at L3+ |
| Engineering Constraint Satisfaction | Dimensional accuracy vs spec | Manual check | >90% at L1-L3 |
| Repair Success Rate | Failed→repaired→valid | N/A (no repair) | >50% of failures repaired |
| Repair Attempts | Average retries before success | 5 max (brute force) | ≤3 with dataset repair |
| Generation Latency | End-to-end time | Measure current | <2× slowdown acceptable |
| Retrieval Latency | SQLite query time | N/A | <200ms |

### 17.4 Benchmark Protocol

```
FOR EACH test prompt P in levels L1-L5:
  1. BASELINE: Run current pipeline (no CADIR, no retrieval)
     Record: success/failure, geometry validity, latency, retries
  
  2. ENHANCED: Run enhanced pipeline (CADIR + retrieval + repair)
     Record: same metrics
  
  3. Compare BASELINE vs ENHANCED per-prompt and per-level
  
  4. Statistical summary: mean, median, improvement %
```

---

<a id="section-18"></a>
## SECTION 18 — IMPLEMENTATION PLAN

### P0 — Inspect & Audit (THIS DOCUMENT) ✅

- [x] Inspect all project files
- [x] Inspect all four datasets
- [x] Verify licenses
- [x] Understand actual data formats
- [x] Identify missing components (agents/, api/)

### P1 — Foundation (Create Missing Core + CADIR Schema)

**Files to CREATE:**

| File | Purpose |
|------|---------|
| `backend/cad/cadir/__init__.py` | Package init |
| `backend/cad/cadir/schema.py` | CADIR Pydantic models (CADIRDocument, CADIRFeature, CADIRSketchProfile, etc.) |
| `backend/cad/cadir/validator.py` | CADIR schema validation + dependency checking |
| `backend/agents/__init__.py` | Package init |
| `backend/agents/state.py` | AgentState TypedDict with CADIR fields |
| `backend/api/__init__.py` | Package init |
| `backend/api/routes/__init__.py` | Package init |

**Files to MODIFY:**

| File | Change |
|------|--------|
| `backend/config.py` | Add `datasets_dir`, `processed_dir`, `knowledge_db_path` settings |

**Dependencies to ADD to `requirements.txt`:**
- `pydantic>=2.0` (already likely present via FastAPI)
- `pyarrow>=14.0` (for BenchCAD)
- `svgpathtools>=1.6` (for drawing parsing)

**Validation:** CADIR schema can be instantiated and validated independently.

### P2 — Dataset Adapters

**Files to CREATE:**

| File | Purpose |
|------|---------|
| `backend/datasets/__init__.py` | Package init |
| `backend/datasets/base.py` | Abstract `DatasetAdapter` class |
| `backend/datasets/registry.py` | Adapter registry + availability checks |
| `backend/datasets/deepcad_adapter.py` | DeepCAD JSON parser |
| `backend/datasets/benchcad_adapter.py` | BenchCAD Arrow/Parquet loader |
| `backend/datasets/fusion360_adapter.py` | Fusion360 reconstruction JSON parser |
| `backend/datasets/drawing2cad_adapter.py` | Drawing2CAD SVG + vectorized data loader |

**Key interfaces:**

```python
class DatasetAdapter(ABC):
    def is_available(self) -> bool: ...
    def get_record_count(self) -> int: ...
    def iterate_records(self) -> Iterator[dict]: ...
    def get_record(self, record_id: str) -> dict: ...
```

**Validation:** Each adapter can load and iterate its dataset. Missing datasets return `is_available() = False` gracefully.

### P3 — Feature Extraction

**Files to CREATE:**

| File | Purpose |
|------|---------|
| `backend/datasets/feature_extractor.py` | Extract normalized feature sequences from parsed records |
| `backend/datasets/cadquery_translator.py` | CadQuery AST → build123d operation mapping |

**Validation:** Feature extractor produces consistent feature lists from all datasets.

### P4 — CADIR Mapping

**Files to CREATE:**

| File | Purpose |
|------|---------|
| `backend/datasets/cadir_mapper.py` | Normalized features → CADIR documents |

**Preprocessing scripts to CREATE:**

| File | Purpose |
|------|---------|
| `scripts/preprocess_deepcad.py` | Batch process DeepCAD → CADIR JSONs |
| `scripts/preprocess_benchcad.py` | Batch process BenchCAD → CADIR JSONs |
| `scripts/preprocess_fusion360.py` | Batch process Fusion360 → CADIR JSONs |
| `scripts/preprocess_drawing2cad.py` | Process Drawing2CAD pairs |
| `scripts/validate_datasets.py` | Validate all processed CADIR documents |

**Output:** `datasets/processed/` populated with valid CADIR documents.

### P5 — Drawing Understanding Pipeline

**Files to CREATE:**

| File | Purpose |
|------|---------|
| `backend/drawing/__init__.py` | Package init |
| `backend/drawing/parser.py` | SVG/DXF/image parsing |
| `backend/drawing/view_identifier.py` | View type detection |
| `backend/drawing/dimension_extractor.py` | OCR + dimension parsing |
| `backend/drawing/feature_recognizer.py` | Drawing→feature interpretation |

**Dependencies:** `easyocr` or `pytesseract`, `opencv-python`

### P6 — Retrieval Index

**Files to CREATE:**

| File | Purpose |
|------|---------|
| `backend/retrieval/__init__.py` | Package init |
| `backend/retrieval/index.py` | SQLite index build/management |
| `backend/retrieval/query.py` | Structured query interface |
| `backend/retrieval/ranker.py` | Result ranking/filtering |
| `scripts/build_index.py` | Index build script |

**Output:** `datasets/processed/knowledge.db` with searchable CADIR examples.

### P7 — CADIR Interpreter + LangGraph Enhancement

**Files to CREATE:**

| File | Purpose |
|------|---------|
| `backend/cad/cadir/interpreter.py` | CADIR→build123d deterministic code generation |
| `backend/agents/input_classifier.py` | Input type detection (text/drawing/sketch/photo) |
| `backend/agents/cadir_repair_agent.py` | Dataset-informed CADIR repair |
| `backend/agents/graph.py` | LangGraph StateGraph with new nodes |
| `backend/agents/supervisor.py` | Intent parsing |
| `backend/agents/design_agent.py` | CADIR generation with retrieval context |
| `backend/agents/validator_agent.py` | Enhanced geometry validation |
| Remaining agent files per graph spec | DFM, Engineering, Cost, Safety, etc. |

**Files to MODIFY:**

| File | Change |
|------|--------|
| `backend/utils/llm.py` | Add `get_ollama_llm()` for local models |
| `backend/cad/validator.py` | Add OCCT topology checks beyond trimesh |
| `backend/cad/feature_tree.py` | Add CADIR-aware feature tree generation |
| `backend/tasks/cad_tasks.py` | Update to use enhanced graph + CADIR state |

### P8 — Self-Healing Enhancement

- Implement `cadir_repair_agent.py` with dataset retrieval for failure context
- Add failure classification logic
- Connect to retrieval index for similar-but-working examples

### P9 — Benchmark

**Files to CREATE:**

| File | Purpose |
|------|---------|
| `scripts/benchmark.py` | Automated benchmark runner |
| `tests/test_benchmark.py` | Benchmark test assertions |

### P10 — Evaluate Fine-Tuning (Only if P9 shows retrieval ceiling)

- Construct training dataset from processed CADIR documents
- Evaluate cloud-based fine-tuning options (Qwen, DeepSeek APIs)
- Consider LoRA/QLoRA if VRAM permits (unlikely with RTX 3050)

---

<a id="section-19"></a>
## SECTION 19 — RISKS

### 19.1 Critical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **CadQuery ≠ build123d** — BenchCAD code cannot be directly executed | HIGH | Build systematic CadQuery→build123d translator. Start with common subset (Box, Cylinder, Hole, Fillet, Chamfer). Flag untranslatable operations. |
| **Dataset mismatch** — DeepCAD/Fusion360 only have sketch+extrude, but we need fillet/chamfer/hole/revolve | HIGH | BenchCAD is the primary source for advanced features. DeepCAD/Fusion360 provide base geometry knowledge. Accept that coverage is incomplete. |
| **CADIR→build123d interpreter complexity** — deterministic code generation for all CADIR feature types is a substantial engineering effort | HIGH | Start with extrude+hole+fillet+chamfer subset. Expand incrementally. Each feature type has well-defined build123d API. |
| **Fusion 360 license** — non-commercial restriction may affect project commercialization | MEDIUM | Keep Fusion360-derived data separate and optional. System must work without it. |
| **BenchCAD license unknown** | MEDIUM | Verify immediately. If restrictive, fall back to DeepCAD + Drawing2CAD (both MIT). |

### 19.2 Moderate Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **LLM hallucination in CADIR generation** | MEDIUM | CADIR schema validation catches malformed output. Retrieval provides grounding examples. Repair agent handles failures. |
| **Feature reference fragility** — fillet/chamfer reference specific edges that may not exist after boolean operations | MEDIUM | The CADIR interpreter must use robust edge/face selection strategies, not hardcoded indices. Use geometric queries (nearest edge to point, edges of type X) rather than ordinal references. |
| **Drawing→CAD ambiguity** — 2D→3D is inherently ambiguous | MEDIUM | Require multiple views. Flag when insufficient views to determine geometry. Request user clarification. |
| **Photo→CAD false confidence** — system might generate CAD that looks right but is dimensionally wrong | MEDIUM | MANDATORY user dimension input for all photo-based generation. Never auto-dimension from photos. |
| **RTX 3050 VRAM** — only one model at a time, slow model switching | MEDIUM | Design pipeline to minimize model switches. Use single model for entire CADIR generation pass. |
| **Dataset processing time** — 77K+ DeepCAD files, 17.9K BenchCAD records | LOW | Process once, store as CADIR JSON + SQLite. Preprocessing is a one-time batch operation. |

### 19.3 Low Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Overengineering the retrieval system | LOW | Start with SQLite. Only add complexity if benchmarks show need. |
| Memorization instead of generalization | LOW | Test with prompts that don't match any dataset example exactly. |
| Invalid topology from complex boolean operations | LOW | OCCT validation catches this. Repair agent can simplify. |
| Dataset download bandwidth/time | LOW | One-time downloads. Provide size estimates. Support partial processing. |

---

<a id="section-20"></a>
## SECTION 20 — FINAL ARCHITECTURE

### 20.1 Architecture Diagram

```
                         ┌──────────────────────────┐
                         │   USER INPUTS             │
                         │  ├── Text Prompt           │
                         │  ├── Engineering Drawing   │
                         │  ├── Rough Sketch          │
                         │  └── Reference Photo       │
                         └───────────┬────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        LANGGRAPH PIPELINE                            │
│                                                                      │
│  ┌───────────┐   ┌──────────────┐   ┌─────────────────────────┐     │
│  │ Supervisor │──▶│ Input        │──▶│ Drawing/Sketch/Photo    │     │
│  │ (Intent)   │   │ Classifier   │   │ Understanding Pipeline  │     │
│  └───────────┘   └──────────────┘   │ (if non-text input)     │     │
│                                      └──────────┬──────────────┘     │
│                                                  │                    │
│                         ┌────────────────────────┘                    │
│                         ▼                                             │
│                ┌──────────────────┐                                   │
│                │ Engineering      │                                   │
│                │ Intent           │                                   │
│                └────────┬─────────┘                                   │
│                         │                                             │
│                         ▼                                             │
│           ┌────────────────────────────┐                              │
│           │ Dataset Retrieval          │◄─── SQLite Knowledge DB      │
│           │ (find similar examples)    │     datasets/processed/      │
│           └────────────┬───────────────┘     knowledge.db             │
│                        │                                              │
│                        ▼                                              │
│           ┌────────────────────────────┐                              │
│           │ Design Agent               │                              │
│           │ (LLM: generates CADIR      │◄─── Ollama Qwen3:8b /       │
│           │  with retrieved examples)  │     DeepSeek-R1:8b           │
│           └────────────┬───────────────┘                              │
│                        │                                              │
│                        ▼                                              │
│           ┌────────────────────────────┐                              │
│           │ CADIR Validator            │                              │
│           │ (schema + dependencies)    │                              │
│           └────────────┬───────────────┘                              │
│                        │                                              │
│                        ▼                                              │
│           ┌────────────────────────────┐                              │
│           │ CADIR→build123d            │                              │
│           │ Interpreter                │                              │
│           │ (DETERMINISTIC code gen)   │                              │
│           └────────────┬───────────────┘                              │
│                        │                                              │
│                        ▼                                              │
│           ┌────────────────────────────┐                              │
│           │ CAD Executor               │                              │
│           │ (sandboxed subprocess)     │◄─── build123d + OCCT         │
│           └────────────┬───────────────┘                              │
│                        │                                              │
│                ┌───────┴───────┐                                      │
│              SUCCESS        FAILURE                                   │
│                │               │                                      │
│                ▼               ▼                                      │
│           ┌──────────┐  ┌─────────────────┐                          │
│           │ Geometry │  │ CADIR Repair     │                          │
│           │ Validator│  │ Agent            │◄── Dataset retrieval     │
│           │ (OCCT +  │  │ (classify error, │    for repair context    │
│           │ trimesh) │  │  find fix,       │                          │
│           └─────┬────┘  │  modify CADIR)   │                          │
│                 │       └───────┬───────────┘                         │
│                 │               │                                      │
│               VALID           RETRY ──────────▶ Back to CADIR         │
│                 │                                Validator              │
│                 ▼                                                      │
│   ┌──────────────────────────────────────────┐                        │
│   │ Downstream Agents (UNCHANGED)             │                       │
│   │ DFM → Engineering → Cost → Safety         │                       │
│   │ → Alternatives → CAM → Documentation      │                       │
│   └──────────────┬───────────────────────────┘                        │
│                  │                                                     │
│                  ▼                                                     │
│   ┌──────────────────────────────────────────┐                        │
│   │ Export: STEP + STL + GLB                  │                       │
│   └──────────────────────────────────────────┘                        │
└──────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────┐
              │ Frontend (Next.js + React Three Fiber)│
              │ ← WebSocket events from Redis pub/sub │
              └──────────────────────────────────────┘
```

### 20.2 Invariant Principles

1. **LLM = reasoning authority** — interprets requirements, generates CADIR, proposes repairs
2. **CADIR = structured design intent** — single canonical representation
3. **CADIR interpreter = deterministic** — CADIR→build123d is a pure function, no LLM
4. **build123d = parametric construction** — the CAD kernel API
5. **OCCT = geometric authority** — determines validity of geometry
6. **Python engineering modules = numerical authority** — calculates dimensions, stresses, etc.
7. **Datasets = knowledge sources** — inform LLM context, not geometric decisions
8. **Raw datasets = immutable** — never modified, only processed into derived artifacts

### 20.3 Data Flow Summary

```
Datasets ──► Adapters ──► Feature Extraction ──► CADIR Mapping ──► SQLite Index
                                                                        │
User Input ──► Supervisor ──► Intent ──► Retrieval Query ──────────────►│
                                              │                         │
                              Retrieved CADIR Examples ◄────────────────┘
                                              │
                              Design Agent + Examples ──► New CADIR
                                              │
                              CADIR Validator ──► CADIR Interpreter ──► build123d
                                              │
                              CAD Executor ──► OCCT ──► Validation ──► Export
```

### 20.4 Key Design Decisions for Implementation

| Decision | Choice | Rationale |
|----------|--------|-----------|
| CADIR before build123d code | CADIR is the LLM output target | Structured intent is more reliable than free-form code generation |
| SQLite for retrieval | Simplest local solution | Zero infrastructure, cross-platform, sufficient for ~200K records |
| No training in Phase 1-3 | Retrieval-first | Prove value before investing in training complexity |
| CadQuery translation | Partial, best-effort | BenchCAD code is CadQuery; translate common patterns, skip exotic ones |
| Drawing pipeline as separate path | Different input type | Drawing understanding requires different processing than text prompts |
| Single CADIR schema for all pathways | Architectural simplicity | Both text→CADIR and drawing→CADIR produce the same schema |
| Graceful degradation without datasets | Reliability | System must generate CAD even without any dataset installed |

### 20.5 Implementation Order for Gemini Pro High

```
PHASE 1 (Foundation):
  1. Create backend/cad/cadir/schema.py         — CADIR Pydantic models
  2. Create backend/cad/cadir/validator.py       — schema validation
  3. Create backend/agents/state.py              — AgentState with CADIR
  4. Extend backend/config.py                    — dataset settings

PHASE 2 (Adapters):
  5. Create backend/datasets/base.py             — abstract adapter
  6. Create backend/datasets/registry.py         — availability check
  7. Create backend/datasets/deepcad_adapter.py  — DeepCAD parser
  8. Create backend/datasets/benchcad_adapter.py — BenchCAD loader
  9. Create backend/datasets/fusion360_adapter.py
  10. Create backend/datasets/drawing2cad_adapter.py

PHASE 3 (Extraction + Mapping):
  11. Create backend/datasets/feature_extractor.py
  12. Create backend/datasets/cadquery_translator.py
  13. Create backend/datasets/cadir_mapper.py
  14. Create scripts/preprocess_*.py (all four)
  15. Create scripts/validate_datasets.py

PHASE 4 (Retrieval):
  16. Create backend/retrieval/index.py
  17. Create backend/retrieval/query.py
  18. Create backend/retrieval/ranker.py
  19. Create scripts/build_index.py

PHASE 5 (CADIR Interpreter + Graph):
  20. Create backend/cad/cadir/interpreter.py
  21. Create backend/agents/graph.py
  22. Create backend/agents/supervisor.py
  23. Create backend/agents/design_agent.py
  24. Create backend/agents/input_classifier.py
  25. Create backend/agents/validator_agent.py
  26. Create backend/agents/cadir_repair_agent.py
  27. Create remaining agent files
  28. Extend backend/utils/llm.py with Ollama
  29. Create backend/api/routes/*.py

PHASE 6 (Drawing Pipeline):
  30. Create backend/drawing/parser.py
  31. Create backend/drawing/view_identifier.py
  32. Create backend/drawing/dimension_extractor.py
  33. Create backend/drawing/feature_recognizer.py

PHASE 7 (Benchmark):
  34. Create scripts/benchmark.py
  35. Create tests/test_*.py
  36. Run baseline vs enhanced comparison
```

---

> [!IMPORTANT]
> **This specification is complete. No implementation has been performed. No files have been modified. No packages have been installed.**
>
> The next step is to hand this document to Gemini Pro High for systematic implementation following the phase order above.
>
> **Critical constraint for implementation:** The existing working project must remain functional at every phase boundary. Each phase should be independently testable.
