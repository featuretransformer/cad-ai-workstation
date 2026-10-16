# Windows Local Startup Guide

**Target**: Get the fixed CAD-AI-Workstation running locally on Windows with the geometry bug fix applied.

---

## Prerequisites

### Required Software
1. **Python 3.11+** (Python 3.12 recommended)
   - Download: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation

2. **Node.js 18+** and npm
   - Download: https://nodejs.org/
   - LTS version recommended

3. **Git**
   - Download: https://git-scm.com/download/win
   - Or use GitHub Desktop

4. **Docker Desktop** (optional, for Redis/PostgreSQL/MinIO)
   - Download: https://www.docker.com/products/docker-desktop/
   - Required for full production mode
   - Can skip for basic CAD generation testing

### Optional (Recommended)
- **Visual Studio Code** with Python extension
- **Windows Terminal** for better command line experience

---

## Quick Start (Development Mode)

### 1. Clone and Switch to Fix Branch

```powershell
# Clone the repository
git clone https://github.com/featuretransformer/cad-ai-workstation.git
cd cad-ai-workstation

# Switch to the fix branch
git checkout fix/deterministic-geometry-generation

# Verify you're on the right branch
git branch
```

### 2. Backend Setup

```powershell
# Navigate to backend
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment (PowerShell)
.\.venv\Scripts\Activate.ps1

# If you get execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or use Command Prompt activation:
# .\.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# This will install:
# - FastAPI and Uvicorn (API server)
# - build123d (CAD kernel)
# - LangGraph (agent framework)
# - pytest (testing)
```

### 3. Run Tests (Verify Fix)

```powershell
# Still in backend directory with venv activated

# Run unit tests
pytest tests/test_deterministic_geometry.py -v

# Expected output:
# test_deterministic_geometry.py::TestDimensionExtraction::test_extract_mm_dimensions PASSED
# test_deterministic_geometry.py::TestPromptSeeding::test_same_prompt_same_seed PASSED
# test_deterministic_geometry.py::TestDeterministicGeometry::test_different_prompts_different_dimensions PASSED
# ... (12 tests should pass)

# Run integration tests (requires CAD execution)
pytest tests/test_e2e_pipeline.py -v -s

# This will:
# - Generate real CADIR documents
# - Compile to build123d code
# - Execute CAD operations
# - Export STEP/STL files
# - Verify different prompts → different files
```

### 4. Configure Environment (Optional)

```powershell
# Copy environment template
cp .env.example .env

# Edit .env in your text editor
notepad .env

# Add API keys (optional for basic testing):
# GEMINI_API_KEY=your_key_here  (for Google Gemini - free tier available)
# GROQ_API_KEY=your_key_here    (for Groq LLM - free tier available)

# NOTE: The geometry fix works WITHOUT API keys!
# The deterministic fallback is what we fixed.
```

### 5. Start Backend Server

```powershell
# Still in backend directory with venv activated
uvicorn main:app --reload --port 8000

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.

# Test health endpoint in browser or curl:
# http://localhost:8000/api/health
```

### 6. Frontend Setup (Separate Terminal)

```powershell
# Open NEW terminal/PowerShell window
cd cad-ai-workstation\frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Expected output:
# > frontend@0.1.0 dev
# > next dev
#   ▲ Next.js 14.x.x
#   - Local:        http://localhost:3000
#   - Ready in 2.3s
```

### 7. Test the Fix

Open browser: **http://localhost:3000**

#### Test Prompts (Verify Different Geometries):

**Test 1: Mounting Plate**
```
Create a mounting plate 80mm x 60mm x 10mm with a 15mm diameter hole in the center
```

**Test 2: Stepped Shaft**
```
Design a stepped shaft 12mm diameter and 100mm long
```

**Test 3: Washer**
```
Make a washer with 30mm outer diameter, 15mm inner diameter, and 4mm thickness
```

**Test 4: Mounting Bracket**
```
Create a mounting bracket 50mm x 40mm with two mounting holes
```

**Expected Results**:
- ✅ Each prompt produces a **different 3D preview**
- ✅ Download STEP files have **different sizes**
- ✅ Dimensions match the prompt specifications
- ✅ Agent log shows dimension extraction working

---

## Verification Checklist

After running the application, verify:

- [ ] Backend health endpoint responds: `http://localhost:8000/api/health`
- [ ] Frontend loads without errors: `http://localhost:3000`
- [ ] Unit tests pass (12 tests in `test_deterministic_geometry.py`)
- [ ] Integration tests pass (4 tests in `test_e2e_pipeline.py`)
- [ ] Different prompts produce different 3D previews
- [ ] STEP file downloads work
- [ ] STL file downloads work
- [ ] Explicit dimensions (e.g., "100mm x 50mm") are respected
- [ ] Agent log shows `[DESIGN_AGENT] Extracted dimensions from prompt:`

---

## Troubleshooting

### Common Issues

#### 1. Python not found
```powershell
# Error: 'python' is not recognized
# Solution: Install Python 3.11+ and add to PATH
# Or use: py -m venv .venv
```

#### 2. build123d installation fails
```powershell
# Error during pip install build123d
# Solution: Install Visual C++ Build Tools
# Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Select "Desktop development with C++"
```

#### 3. Port already in use
```powershell
# Error: [Errno 10048] Only one usage of each socket address
# Solution: Change port
uvicorn main:app --reload --port 8001  # Use different port
```

#### 4. Module not found errors
```powershell
# Error: ModuleNotFoundError: No module named 'agents'
# Solution: Verify you're in backend directory with venv activated
cd backend
.\.venv\Scripts\Activate.ps1
```

#### 5. STEP export fails
```powershell
# Check exports directory exists
mkdir exports

# Check logs for errors
# Backend terminal will show detailed error messages
```

#### 6. Tests fail with timeout
```powershell
# Integration tests may take time on first run
# Increase timeout:
pytest tests/test_e2e_pipeline.py -v -s --timeout=120
```

### Getting Help

1. **Check logs**:
   - Backend: Terminal running `uvicorn main:app`
   - Frontend: Terminal running `npm run dev`
   - Browser console: Press F12 → Console tab

2. **Verify fix is applied**:
   ```powershell
   git branch
   # Should show: * fix/deterministic-geometry-generation
   
   git log --oneline -5
   # Should show commits about geometry fix
   ```

3. **Clean restart**:
   ```powershell
   # Backend
   deactivate
   rm -rf .venv
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   
   # Frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

---

## Production Mode (Full Stack with Docker)

### Prerequisites
- Docker Desktop installed and running

### Steps

```powershell
# From project root
cd cad-ai-workstation

# Start infrastructure (PostgreSQL, Redis, MinIO)
docker-compose -f docker-compose.dev.yml up -d

# Wait for services to start (30 seconds)
timeout /t 30

# Start backend (terminal 1)
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000

# Start Celery worker (terminal 2)
cd backend
.\.venv\Scripts\Activate.ps1
celery -A tasks.celery_app worker --loglevel=info -Q cad_generation

# Start frontend (terminal 3)
cd frontend
npm run dev
```

### Verify Services

```powershell
# Check Docker containers
docker ps

# Expected:
# - cad-postgres
# - cad-redis
# - cad-minio

# Check Redis connection
docker exec -it cad-redis redis-cli ping
# Expected: PONG

# Check PostgreSQL
docker exec -it cad-postgres psql -U caduser -d caddb -c "\dt"
# Expected: List of tables
```

---

## Next Steps After Verification

Once you've verified the fix works locally:

1. **Review Pull Request**:
   - https://github.com/featuretransformer/cad-ai-workstation/pull/3
   - Check diff, tests, documentation

2. **Merge to Main**:
   ```powershell
   git checkout main
   git pull origin main
   git merge fix/deterministic-geometry-generation
   git push origin main
   ```

3. **Update your local environment**:
   ```powershell
   git checkout main
   git pull origin main
   cd backend
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. **Continue development**:
   - Add more component templates
   - Improve dimension extraction with ML
   - Implement CAM toolpath generation
   - Add FEA integration

---

## Summary

This guide walks you through:
1. ✅ Installing prerequisites
2. ✅ Cloning and switching to fix branch
3. ✅ Setting up Python backend with build123d
4. ✅ Running comprehensive tests
5. ✅ Starting local dev servers
6. ✅ Testing the geometry fix with real prompts
7. ✅ Troubleshooting common issues
8. ✅ (Optional) Running full production stack with Docker

**Result**: Fully functional local CAD-AI-Workstation with the critical geometry bug fixed and verified.

---

**Branch**: `fix/deterministic-geometry-generation`  
**Status**: ✅ Tested and working locally  
**Next**: Merge to main and deploy
