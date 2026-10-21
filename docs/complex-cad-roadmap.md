# AI-Native CAD-CAM Workstation — Complex Mechanical Design Roadmap

## 1. Current Architecture Audit

### 1.1 What Works

| Component | Status | Evidence |
|-----------|--------|----------|
| FastAPI backend (`main.py`) | ✅ Working | Sessions, design, export endpoints functional |
| Celery async pipeline (`tasks/cad_tasks.py`) | ✅ Working | Redis pub/sub, real-time WebSocket events |
| LangGraph workflow (`agents/graph.py`) | ✅ Working | 14-node graph: classifier → supervisor → design → validate → interpret → execute → validate → downstream |
| CADIR schema (`cad/cadir/schema.py`) | ✅ Working | Pydantic v2, 15 feature types, sketch profiles, engineering intent |
| CADIR → build123d interpreter (`cad/cadir/interpreter.py`) | ✅ Working | Deterministic code generation, 316 LOC |
| Sandboxed executor (`cad/executor.py`) | ✅ Working | AST validation, subprocess isolation, STEP/STL export |
| Geometry validation (`agents/validator_nodes.py`) | ✅ Working | Volume, bbox, solid count, watertight checks |
| Self-healing repair (`agents/cadir_repair_agent.py`) | ✅ Working | Error-driven CADIR repair with retry loop |
| Downstream analysis (7 agents) | ✅ Working | DFM, engineering, cost, safety, alternatives, CAM, documentation |
| LLM provider abstraction (`utils/llm.py`) | ✅ Working | Gemini → Groq → Ollama failover chain |
| FAISS vector retrieval (`retrieval/`) | ✅ Working | DeepCAD, BenchCAD, Drawing2CAD, Fusion360 datasets |
| Next.js 14 frontend | ✅ Working | Workstation layout, chat, viewer, feature tree, export |
| Three.js/react-three-fiber viewer | ✅ Working | GLB model loading and interactive 3D rendering |

### 1.2 Verified Pipeline Performance (Diagnosis Results)

| Prompt | CADIR Valid | Execution | Volume (mm³) | BBox (mm) | STEP/STL |
|--------|------------|-----------|--------------|-----------|----------|
| Washer 30/10/3mm | ✅ | ✅ | 1,885 | 30×30×3 | ✅ |
| Stepped shaft 20→15mm | ✅ | ✅ | 19,609 | 20×20×80 | ✅ |
| Bracket 50×40×5mm + M8 holes | ✅ | ✅ | 9,295 | 50×40×5 | ✅ |
| M10 hex bolt 40mm | ❌ (LLM) | ❌ | — | — | — |
| Spur gear 48mm PD | ✅ | ✅ | 39,665 | 52×52×20 | ✅ |

**4/5 unique geometries generated** with correct dimensions and valid STEP/STL exports.

### 1.3 Confirmed Fundamental Limitations

1. **No assembly support**: CADIR represents a single `CADIRDocument` with one flat feature list
2. **No component decomposition**: Pipeline generates one monolithic solid per prompt
3. **No assembly placement or constraints**: No mating interfaces, joints, or clearances
4. **Limited feature complexity**: Missing sweep, loft, shell, rib, thread, draft
5. **No parametric propagation**: Parameters set once, no re-evaluation chain
6. **No image input pathway**: Stubs exist but no actual image processing
7. **LLM fragility**: Complex parts often fail validation
8. **No iterative design refinement**: Each request generates from scratch
9. **Single-body export**: No multi-body or assembly STEP export

---

## 2. CAD Technology Evaluation

### 2.1 CADFusion Assessment

| Aspect | Finding |
|--------|---------|
| Architecture | LLaMA-3-8B fine-tuned with visual feedback DPO |
| Input | Text descriptions only |
| Output | Sketch-and-extrude DSL |
| Assembly support | ❌ Single-body only |
| VRAM requirement | ~16 GB FP16, ~8 GB INT4 |
| User's GPU | RTX 3050 6GB — **insufficient** |
| Feature set | Basic sketches + extrude + boolean only |
| Image input | ❌ Not supported |

**Verdict: CADFusion is NOT viable.** Cannot run on available hardware, does not support assemblies, limited features.

### 2.2 CAD Backend Decision

**Retain build123d.** It already works, supports assemblies via `BuildAssembly`, and has the richest Python-native API with sweep/loft/shell support.

### 2.3 Model Decision

**Keep current LLM stack** (Gemini 3.8 Flash → Groq Qwen 3.8-27B → Ollama local). Add specialized prompting for assembly decomposition.

---

## 3. Target Architecture

```
User Input (text/image)
       │
       ▼
┌─────────────────────┐
│  Input Interpreter   │  ← Classify + extract requirements
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Design Planner      │  ← Decompose into components + interfaces
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Assembly Spec       │  ← Machine-readable shared design truth
└──────────┬──────────┘
           ▼
┌──────────┴──────────┐
│  Per-Component       │  ← Individual part CADIR generation
│  CAD Generation      │  ← (uses existing pipeline per part)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Assembly Executor   │  ← build123d BuildAssembly + placement
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Verification        │  ← Collision, clearance, dimension checks
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Export & Report     │  ← Assembly STEP, per-part STL, BOM
└─────────────────────┘
```

---

## 4. Phased Implementation

### Phase 1: Assembly Schema (Foundation)
- `backend/cad/assembly/schema.py` — AssemblySpec, ComponentSpec, MatingInterface, Placement3D
- Extend AgentState with assembly fields
- Backward compatible with single-part workflow

### Phase 2: Design Planner Agent
- `backend/agents/design_planner.py` — LLM-based component decomposition
- Deterministic fallback for known assembly families
- Wire into LangGraph workflow

### Phase 3: Per-Component Generation Loop
- Modify design agent to accept ComponentSpec
- Loop over components, generate CADIR per part
- Collect results into assembly state

### Phase 4: Assembly Execution
- `backend/cad/assembly/executor.py` — build123d BuildAssembly
- Placement transforms, multi-body STEP export
- Per-part STL export

### Phase 5: Assembly Validation
- Collision/interference detection
- Clearance verification
- Dimensional validation

### Phase 6: Enhanced Features
- Sweep, loft, shell in CADIR schema + interpreter
- Thread representation for fasteners

### Phase 7: Image Input & Iteration
- Vision model integration
- Parameter change propagation

---

## 5. Acceptance Criteria

### Three-Finger Gripper Benchmark
1. Decompose into: mounting plate, 3 fingers, pivots, links, actuator
2. Generate parametric CADIR for each component
3. Assemble with correct spacing and alignment
4. Export assembly STEP with separate named solids
5. Report assumptions and unresolved parameters

### Regression
All existing single-part prompts must continue to work.
