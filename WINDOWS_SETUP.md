# Windows Local Startup Guide

Complete instructions for running the AI-Native CAD-CAM Workstation on Windows 10/11.

---

## Prerequisites

### Required Software

1. **Python 3.11 or 3.12** (build123d requires 3.11+)
   - Download: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
   - Verify: `python --version` in PowerShell

2. **Node.js 18+ and npm**
   - Download: https://nodejs.org/ (LTS version)
   - Verify: `node --version` and `npm --version`

3. **Git**
   - Download: https://git-scm.com/download/win
   - Verify: `git --version`

4. **Docker Desktop** (optional, for Redis/PostgreSQL/MinIO)
   - Download: https://www.docker.com/products/docker-desktop/
   - ⚠️ Requires Windows 10/11 Pro/Enterprise or WSL2 on Home edition
   - Alternative: Run backend without Redis (fallback mode works)

### Optional but Recommended

5. **Ollama** (for local LLM inference without API keys)
   - Download: https://ollama.ai/download/windows
   - After install: `ollama pull llama3.3` (or another model)

---

## Step 1: Clone Repository

Open PowerShell or Command Prompt:

```powershell
git clone https://github.com/featuretransformer/cad-ai-workstation.git
cd cad-ai-workstation
```

---

## Step 2: Backend Setup

### 2.1 Create Virtual Environment

```powershell
cd backend
python -m venv .venv
```

### 2.2 Activate Virtual Environment

**PowerShell** (most common):
```powershell
.\.venv\Scripts\Activate.ps1
```

If you get an execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Command Prompt** (cmd.exe):
```cmd
.venv\Scripts\activate.bat
```

You should see `(.venv)` prefix in your prompt.

### 2.3 Install Python Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected**: ~50-100 packages installed including:
- FastAPI
- build123d
- LangGraph
- SQLAlchemy
- trimesh
- etc.

⚠️ **If build123d fails**:
- Ensure Python 3.11 or 3.12 (not 3.13)
- Try: `pip install --no-cache-dir build123d`

### 2.4 Configure Environment Variables

```powershell
copy .env.example .env
notepad .env
```

**Minimal working configuration** (no paid API needed):

```env
# Development mode
DEV_MODE=true

# Database (SQLite fallback)
DATABASE_URL=sqlite:///./cad_workstation.db

# Redis (optional - backend works without it)
# REDIS_URL=redis://localhost:6379/0

# LLM APIs (optional - system works offline with Ollama)
# GEMINI_API_KEY=your_key_here
# GROQ_API_KEY=your_key_here

# Ollama (local LLM - free)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.3

# CORS (allow frontend to connect)
CORS_ORIGINS=http://localhost:3000

# Retries and timeouts
MAX_RETRIES=3
CAD_TIMEOUT_SECONDS=60

# Knowledge base (optional)
KNOWLEDGE_DB_PATH=./knowledge/cadir_examples.db
```

**Save and close** notepad.

### 2.5 Initialize Database

```powershell
# Run Alembic migrations
alembic upgrade head
```

**Expected**: Database tables created (designs, sessions, agent_logs, exports).

---

## Step 3: Frontend Setup

Open a **new PowerShell window** (keep backend terminal open):

```powershell
cd cad-ai-workstation\frontend
npm install
```

**Expected**: ~1000+ packages installed (Next.js, React, Three.js, etc.)

⚠️ **If errors occur**:
```powershell
# Clear cache and retry
rm -r node_modules
rm package-lock.json
npm install
```

---

## Step 4: Start Services

### Option A: Without Docker (Simplest)

Backend runs with SQLite database and no Redis (background task fallback).

**Terminal 1 — Backend**:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

**Expected output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx]
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Terminal 2 — Frontend**:
```powershell
cd frontend
npm run dev
```

**Expected output**:
```
   ▲ Next.js 14.x.x
   - Local:        http://localhost:3000
   - Ready in 2.5s
```

✅ **Open browser**: http://localhost:3000

---

### Option B: With Docker (Full Stack)

Requires **Docker Desktop** running.

**Terminal 1 — Start infrastructure** (PostgreSQL, Redis, MinIO):
```powershell
docker compose -f docker-compose.dev.yml up -d
```

**Verify services**:
```powershell
docker compose -f docker-compose.dev.yml ps
```

**Expected**:
```
NAME                COMMAND                  STATUS
cad-postgres        "docker-entrypoint.s…"   Up
cad-redis           "docker-entrypoint.s…"   Up
cad-minio           "minio server /data"     Up
```

**Terminal 2 — Backend**:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

**Terminal 3 — Celery Worker** (optional, for async task queue):
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A tasks.celery_app worker --loglevel=info -Q cad_generation --pool=solo
```

⚠️ **Windows note**: Use `--pool=solo` or `--pool=gevent` (Celery's default prefork doesn't work on Windows).

**Terminal 4 — Frontend**:
```powershell
cd frontend
npm run dev
```

✅ **Open browser**: http://localhost:3000

---

## Step 5: Verify Installation

### Health Check

Visit: http://localhost:8000/api/health

**Expected response**:
```json
{
  "status": "healthy",
  "service": "cad-ai-workstation-api",
  "version": "0.1.0"
}
```

### API Docs

Visit: http://localhost:8000/docs

**Expected**: FastAPI Swagger UI showing all endpoints.

### Frontend UI

Visit: http://localhost:3000

**Expected**: 3-panel CAD workstation interface with:
- Left: Chat/prompt input
- Center: 3D viewer (dark grid)
- Right: Agent log panel

---

## Step 6: Test CAD Generation

### Test 1: Simple Geometry

1. In the chat panel, type:
   ```
   create a 50mm x 30mm x 10mm rectangular plate
   ```

2. Click **Generate** or press Enter

3. **Expected behavior**:
   - Agent log shows pipeline steps (Supervisor → Design Agent → Interpreter → Executor → Validator)
   - 3D viewer displays a rectangular box
   - Export buttons appear (STEP, STL, GLB)
   - Download works

### Test 2: Verify Fix

1. Submit prompt:
   ```
   create a simple mounting plate
   ```

2. Note the bounding box dimensions in viewer

3. Submit **different** prompt:
   ```
   make a sturdy bracket
   ```

4. **Verify**: Bounding box dimensions are **different** from step 2

✅ **If dimensions differ**: Repeated geometry bug is fixed!

---

## Common Issues & Solutions

### Issue 1: Port Already in Use

**Error**: `Address already in use: 127.0.0.1:8000`

**Solution**:
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <PID> /F
```

### Issue 2: build123d Import Error

**Error**: `ModuleNotFoundError: No module named 'build123d'`

**Solutions**:
1. Ensure Python 3.11 or 3.12 (not 3.13):
   ```powershell
   python --version
   ```

2. Reinstall:
   ```powershell
   pip uninstall build123d
   pip install --no-cache-dir build123d
   ```

3. Check for OpenCASCADE installation issues (build123d dependency)

### Issue 3: Frontend Build Errors

**Error**: `Error: Cannot find module...`

**Solution**:
```powershell
cd frontend
rm -r node_modules, .next, package-lock.json
npm install
npm run dev
```

### Issue 4: Execution Policy Error (PowerShell)

**Error**: `... cannot be loaded because running scripts is disabled...`

**Solution**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue 5: Docker Not Starting

**Error**: `Docker daemon is not running`

**Solutions**:
1. Open **Docker Desktop** app (must be running)
2. Wait for "Docker Desktop is running" in system tray
3. Retry: `docker compose -f docker-compose.dev.yml up -d`

**Alternative**: Use Option A (without Docker) — backend works with SQLite.

### Issue 6: CAD Execution Timeout

**Error**: `CAD execution timed out after 60 seconds`

**Solutions**:
1. Increase timeout in `.env`:
   ```env
   CAD_TIMEOUT_SECONDS=120
   ```

2. Simplify the prompt (complex geometry takes longer)

3. Check system resources (CPU/RAM)

---

## Optional: Ollama Setup (Local LLM)

For **offline operation** without API keys:

### 1. Install Ollama

Download and install from: https://ollama.ai/download/windows

### 2. Pull a Model

```powershell
ollama pull llama3.3
```

**Expected**: ~4GB download for Llama 3.3 70B quantized model.

### 3. Verify

```powershell
ollama list
```

**Expected**:
```
NAME              ID              SIZE
llama3.3:latest   abc123def456    4.7 GB
```

### 4. Configure Backend

In `backend/.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.3
```

### 5. Test

Restart backend and submit a prompt. Check logs for:
```
[design_agent] LLM parsing failed (attempted=True, error=...), using parametric fallback
```

If Ollama works, you'll see structured CADIR output from the LLM before fallback.

---

## Directory Structure (After Setup)

```
cad-ai-workstation/
│
├── backend/
│   ├── .venv/              ← Python virtual environment
│   ├── exports/            ← Generated STEP/STL files
│   ├── cad_workstation.db  ← SQLite database (if not using Docker)
│   ├── .env                ← Your environment config
│   └── ...
│
├── frontend/
│   ├── node_modules/       ← npm dependencies
│   ├── .next/              ← Next.js build cache
│   └── ...
│
└── docker-compose.dev.yml  ← Optional Docker services
```

---

## Stopping Services

### Backend & Frontend

Press **CTRL+C** in each terminal window.

### Docker Services

```powershell
docker compose -f docker-compose.dev.yml down
```

**To remove data volumes** (reset database):
```powershell
docker compose -f docker-compose.dev.yml down -v
```

---

## Development Workflow

### Typical Development Session

1. **Start Docker** (if using):
   ```powershell
   docker compose -f docker-compose.dev.yml up -d
   ```

2. **Start backend** (terminal 1):
   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   uvicorn main:app --reload --port 8000
   ```

3. **Start frontend** (terminal 2):
   ```powershell
   cd frontend
   npm run dev
   ```

4. **Work on code**:
   - Backend changes auto-reload (Uvicorn `--reload`)
   - Frontend changes hot-reload (Next.js dev server)

5. **Run tests**:
   ```powershell
   cd backend
   pytest tests/test_repeated_geometry_fix.py -v
   ```

6. **Commit changes**:
   ```powershell
   git add .
   git commit -m "Your message"
   git push
   ```

---

## Next Steps

### Learn the System

1. **Architecture**: Read `architecture_specification.md`
2. **Agent Pipeline**: Explore `backend/agents/graph.py`
3. **CADIR Schema**: Read `backend/cad/cadir/schema.py`
4. **Frontend Components**: Check `frontend/src/components/`

### Test the Fix

1. Run regression tests:
   ```powershell
   cd backend
   pytest tests/test_repeated_geometry_fix.py -v -s
   ```

2. Submit different prompts and verify unique geometry:
   - "create a simple mounting plate"
   - "make a sturdy bracket"
   - "50mm washer"

### Extend Functionality

1. **Add new component templates** in `design_agent.py::_synthesize_parametric_cadir()`
2. **Improve dimension extraction** in `_extract_dimensions_robust()`
3. **Add dataset integration** (DeepCAD, BenchCAD) in `backend/retrieval/`
4. **Implement CAM** in `backend/cam/` (Phase 4 milestone)

---

## Production Deployment

For production deployment:

1. Read: `PRODUCTION.md`
2. Build Docker images: `docker compose build`
3. Deploy stack: `docker compose up -d`
4. Configure reverse proxy (nginx) and HTTPS

---

## Troubleshooting Checklist

- [ ] Python 3.11 or 3.12 installed and in PATH
- [ ] Virtual environment activated (`.venv` prefix in prompt)
- [ ] `pip install -r requirements.txt` completed without errors
- [ ] `.env` file created from `.env.example`
- [ ] Database initialized (`alembic upgrade head`)
- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] Browser can access http://localhost:3000
- [ ] Health check passes: http://localhost:8000/api/health

If all checked and still issues, see **Common Issues** section above or open a GitHub issue.

---

## Getting Help

- **GitHub Issues**: https://github.com/featuretransformer/cad-ai-workstation/issues
- **Documentation**: `README.md`, `PRODUCTION.md`, `FIX_REPORT.md`
- **API Docs**: http://localhost:8000/docs (when backend running)

---

**Status**: ✅ Complete Windows local development setup guide  
**Last Updated**: 2026-10-16  
**Tested On**: Windows 10/11, Python 3.12, Node 18 LTS
