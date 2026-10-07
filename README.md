# 🤖 AI-Native CAD-CAM Workstation

> **Natural language → parametric 3D geometry → manufacturable part** — powered by a multi-agent LangGraph pipeline and build123d CAD kernel.

![Phase 1 Alpha](https://img.shields.io/badge/Phase-1%20Alpha-cyan)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ What it does

Type a natural language design brief → the system autonomously:

1. **Parses intent** (Supervisor Agent — Gemini Pro)
2. **Generates parametric CAD code** (Design Agent — DeepSeek-R1 / Llama 3.3 via Groq)
3. **Executes in a sandboxed subprocess** using [build123d](https://github.com/gumyr/build123d) + OpenCASCADE
4. **Self-heals errors** (up to 5 retries with root-cause repair)
5. **Validates geometry** — watertight, manifold, non-degenerate
6. **Runs DFM analysis** — CNC/3D-print/injection molding checks
7. **Estimates cost** — material + machining time
8. **Checks safety/compliance** — ISO/OSHA flags
9. **Generates 5 design alternatives** — Pareto variants
10. **Exports STEP / STL / GLB** — download directly from the UI

All agent activity streams live to the browser via **WebSocket + Redis pub/sub**.

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, React Three Fiber, Zustand, Framer Motion |
| **3D Viewer** | Three.js + @react-three/drei (GLB, Orbit Controls, Infinite Grid) |
| **Backend API** | FastAPI + WebSocket |
| **Agent Pipeline** | LangGraph 1.2 (StateGraph with retry loop) |
| **LLM — Supervisor** | Google Gemini 1.5 Pro |
| **LLM — Design** | DeepSeek-R1 / Llama 3.3 70B via Groq |
| **CAD Kernel** | build123d 0.8 + OCCT |
| **Mesh Export** | trimesh → STEP / STL / GLB |
| **Task Queue** | Celery + Redis |
| **Database** | PostgreSQL (sessions, designs, agent logs) |
| **Object Storage** | MinIO |

---

## 🚀 Quick Start

### 1. Clone & enter

```bash
git clone https://github.com/YOUR_USERNAME/cad-ai-workstation.git
cd cad-ai-workstation
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your API keys:
# GEMINI_API_KEY=...  (https://aistudio.google.com — free)
# GROQ_API_KEY=...    (https://console.groq.com — free)
```

### 3. Start infrastructure (Docker)

```bash
sudo docker compose -f docker-compose.dev.yml up -d
# Starts: PostgreSQL, Redis, MinIO
```

### 4. Start backend

```bash
# Terminal 1 — FastAPI
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 — Celery worker
cd backend && source .venv/bin/activate
celery -A tasks.celery_app worker --loglevel=info -Q cad_generation
```

### 5. Start frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## 🏗️ Project Structure

```
cad/
├── docker-compose.yml          # Full production stack
├── docker-compose.dev.yml      # Dev: Redis + Postgres + MinIO only
├── .env.example                # Environment template
│
├── backend/
│   ├── agents/                 # LangGraph agent nodes
│   │   ├── state.py            # Shared AgentState TypedDict
│   │   ├── graph.py            # LangGraph StateGraph pipeline
│   │   ├── supervisor.py       # Intent parsing (Gemini)
│   │   ├── design_agent.py     # CAD code generation (Groq/DeepSeek)
│   │   ├── validator_agent.py  # Geometry validation + executor
│   │   ├── dfm_agent.py        # Design for manufacturability
│   │   ├── engineering_agent.py# Material + safety factor
│   │   ├── cost_agent.py       # Cost estimation
│   │   ├── safety_agent.py     # ISO/OSHA compliance
│   │   ├── alternatives_agent.py # 5 design variants
│   │   └── ...
│   ├── cad/
│   │   ├── executor.py         # Sandboxed build123d subprocess
│   │   ├── exporter.py         # STEP → STL → GLB pipeline
│   │   ├── validator.py        # trimesh mesh validation
│   │   └── feature_tree.py     # Feature extraction from code
│   ├── api/routes/             # FastAPI REST + WebSocket routes
│   ├── tasks/                  # Celery task definitions
│   └── db/                     # SQLAlchemy models + CRUD
│
├── frontend/src/
│   ├── components/
│   │   ├── Workstation.tsx     # 3-panel layout
│   │   ├── ViewerCanvas.tsx    # React Three Fiber 3D viewport
│   │   ├── ChatPanel.tsx       # Natural language input
│   │   ├── AgentLog.tsx        # Live agent activity stream
│   │   ├── FeatureTree.tsx     # CAD feature tree panel
│   │   └── ExportPanel.tsx     # Download STEP/STL/GLB
│   ├── store/cadStore.ts       # Zustand global state
│   └── hooks/useWebSocket.ts   # Real-time agent streaming
│
└── infra/
    ├── nginx/nginx.conf
    └── postgres/init.sql
```

---

## 🔄 Agent Pipeline Flow

```
User Prompt
  → Supervisor Agent      (parse intent → JSON)
  → Design Agent          (generate build123d Python code)
  → CAD Executor          (subprocess sandbox, 60s timeout)
  → Geometry Validator    (trimesh: watertight, manifold)
  → [retry loop if error, max 5x]
  → DFM Agent             (CNC/3DP manufacturability)
  → Engineering Agent     (material, mass, safety factor)
  → Cost Agent            (unit cost estimate)
  → Safety Agent          (ISO/OSHA flags)
  → Alternatives Agent    (5 design variants)
  → CAM Agent             (toolpath stub → Phase 4)
  → Documentation Agent   (BOM + drawing notes)
  → Export (STEP + STL + GLB)
  → WebSocket broadcast → Frontend
```

---

## 📋 Roadmap

- [x] **Phase 1** — Core CAD loop: NL → geometry → 3D viewer → STEP export
- [ ] **Phase 2** — Conversational editing, visual diff, Pareto optimization, sketch-to-CAD
- [ ] **Phase 3** — FEA (Calculix), CFD (OpenFOAM), neural surrogate models
- [ ] **Phase 4** — Real G-code (FreeCAD Path), assembly design, 3D scan → parametric

---

## ⚠️ Important Notes

- **Never commit `.env`** — it contains your API keys (already in `.gitignore`)
- build123d requires Python 3.11+ and system OpenGL libraries
- Docker is required for Redis, PostgreSQL, MinIO
- CAD execution runs in a sandboxed subprocess with a 60s timeout

---

## 📄 License

MIT — open source, use freely.
