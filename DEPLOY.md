# 🚀 Immediate Deployment Guide

## Quick Start (5 Minutes)

### Prerequisites
```bash
# Required
- Docker & Docker Compose installed
- Git installed
- Python 3.12+
- Node.js 20+

# API Keys (at least one required)
- Gemini API Key (https://aistudio.google.com)
- Groq API Key (https://console.groq.com)
```

---

## Step 1: Clone and Configure (2 min)

```bash
# Clone the repository
git clone https://github.com/featuretransformer/cad-ai-workstation.git
cd cad-ai-workstation

# Checkout production-ready branch
git checkout production-ready-fixes

# Configure environment
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or vim, code, etc.
```

**Required in `.env`:**
```bash
GEMINI_API_KEY=your_actual_key_here
GROQ_API_KEY=your_actual_key_here

# For production deployment, also set:
# DEV_MODE=false
# CORS_ORIGINS=https://your-domain.com
# SECRET_KEY=<generate with: openssl rand -hex 32>
```

---

## Step 2: Run Automated Deployment (3 min)

```bash
# Make deployment script executable
chmod +x scripts/deploy-and-test.sh

# Deploy to staging (automatic: migrations, tests, health checks)
./scripts/deploy-and-test.sh staging
```

The script will automatically:
1. ✅ Validate environment variables
2. ✅ Run database migrations
3. ✅ Build Docker images
4. ✅ Run production readiness tests
5. ✅ Start all services
6. ✅ Run health checks
7. ✅ Execute integration test with real LLM

---

## Step 3: Verify Deployment

### Check Services
```bash
# All services should be running
docker compose ps

# Should show:
# - postgres (healthy)
# - redis (healthy)
# - minio (healthy)
# - backend (running)
# - celery-worker (running)
# - flower (running)
# - frontend (running)
```

### Test API
```bash
# Health check
curl http://localhost:8000/api/health

# Expected response:
# {"status":"ok","version":"1.0.0","dev_mode":true}
```

### Test Frontend
```bash
# Open browser
open http://localhost:3000

# Or test with curl
curl -I http://localhost:3000
```

---

## Step 4: Run Load Tests

### Full Load Test (5 scenarios)
```bash
# Install test dependencies
pip install httpx

# Run comprehensive load test
python3 scripts/load-test.py

# Tests:
# 1. Simple Washer
# 2. Hex Nut
# 3. Mounting Plate
# 4. Cylindrical Pin
# 5. L-Bracket
```

**Expected Output:**
```
🚀 CAD PIPELINE LOAD TEST
═══════════════════════════════════════════════════════

✅ Created test session: <session-id>

🔧 Testing: Simple Washer
   Prompt: Create a flat washer with outer diameter 30mm...
   📋 Design ID: <design-id>
   ⏳ Status: IN_PROGRESS (5s)
   ⏳ Status: IN_PROGRESS (10s)
   ✅ Completed in 45.2s
      Geometry Valid: True
      DFM Score: 85.3/100
      Est. Cost: $2.45

[... more tests ...]

📊 LOAD TEST SUMMARY
═══════════════════════════════════════════════════════
Total Tests:     5
✅ Passed:       4 (80.0%)
❌ Failed:       1 (20.0%)

Avg Generation Time: 52.3s per design
```

---

## Manual Testing (Alternative)

### Test via API

```bash
# 1. Create session
SESSION=$(curl -s -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name":"Manual Test"}' | jq -r '.id')

echo "Session ID: $SESSION"

# 2. Generate design
DESIGN=$(curl -s -X POST http://localhost:8000/api/design/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION\",
    \"prompt\": \"Create a simple washer with outer diameter 30mm, inner diameter 10mm, thickness 4mm\"
  }" | jq -r '.design_id')

echo "Design ID: $DESIGN"

# 3. Wait for completion (60-120 seconds)
sleep 60

# 4. Check result
curl -s http://localhost:8000/api/design/$DESIGN | jq '.'
```

### Test via Frontend

1. Open http://localhost:3000
2. Enter prompt: `"Create a washer with outer diameter 30mm"`
3. Click Generate
4. Watch real-time agent logs
5. View 3D model when complete
6. Download STEP/STL/GLB files

---

## Monitoring During Tests

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f celery-worker

# Filter for errors
docker compose logs backend | grep ERROR
```

### Check Task Queue
```bash
# Open Flower (Celery monitor)
open http://localhost:5555

# Shows:
# - Active tasks
# - Task history
# - Worker status
```

### Database Queries
```bash
# Connect to database
docker compose exec postgres psql -U caduser caddb

# Check recent designs
SELECT id, status, geometry_valid, created_at 
FROM designs 
ORDER BY created_at DESC 
LIMIT 10;

# Check agent logs
SELECT agent_name, status, created_at 
FROM agent_logs 
WHERE design_id = '<design-id>' 
ORDER BY created_at;
```

---

## Troubleshooting

### Issue: LLM API Error
```bash
# Check API keys
grep API_KEY .env

# Test Gemini connection
curl https://generativelanguage.googleapis.com/v1/models?key=$GEMINI_API_KEY

# Test Groq connection  
curl https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY"
```

### Issue: Docker Build Fails
```bash
# Clean rebuild
docker compose down -v
docker system prune -af
docker compose build --no-cache
docker compose up -d
```

### Issue: Migration Fails
```bash
# Check migration status
cd backend
source .venv/bin/activate
alembic current

# Reset and reapply (DEV ONLY!)
alembic downgrade base
alembic upgrade head
```

### Issue: CAD Execution Timeout
```bash
# Increase timeout in .env
CAD_TIMEOUT_SECONDS=120

# Restart services
docker compose restart backend celery-worker
```

---

## Performance Benchmarks

### Expected Performance (local deployment)

| Metric | Value |
|--------|-------|
| Simple design (washer) | 45-60s |
| Complex design (assembly) | 90-120s |
| LLM latency | 2-5s per call |
| CAD execution | 5-15s |
| DFM analysis | 3-8s |
| Throughput | 30-40 designs/hour |

### Optimization Tips

1. **Use Groq for faster inference** (DeepSeek-R1)
2. **Scale Celery workers**: `celery-worker: deploy: replicas: 4`
3. **Cache embeddings**: Implement Redis caching
4. **GPU acceleration**: Use CUDA for trimesh operations

---

## Production Deployment

### Before Going Live

1. **Set production environment**
   ```bash
   # In .env
   DEV_MODE=false
   CORS_ORIGINS=https://your-domain.com
   SECRET_KEY=<secure-random-32-chars>
   ```

2. **Use production database**
   ```bash
   DATABASE_URL=postgresql://user:pass@prod-db.example.com:5432/caddb
   ```

3. **Enable HTTPS**
   - Configure reverse proxy (Nginx/Traefik)
   - Add SSL certificates (Let's Encrypt)
   - Update `NEXT_PUBLIC_API_URL` to HTTPS

4. **Set up monitoring**
   - Health check endpoints
   - Log aggregation (ELK stack)
   - Metrics (Prometheus + Grafana)

5. **Configure backups**
   ```bash
   # Database backup cron
   0 2 * * * docker compose exec postgres pg_dump -U caduser caddb > backup.sql
   
   # MinIO backup
   0 3 * * * docker compose exec minio mc mirror /data/cad-exports /backup/
   ```

---

## Success Criteria

Your deployment is successful when:

- [x] All health checks pass (Step 2)
- [x] Production readiness tests pass (Step 2)
- [x] Integration test completes (Step 2)
- [x] Load test passes ≥80% (Step 4)
- [x] Manual test generates valid geometry (Manual Testing)
- [x] Frontend loads and connects to backend
- [x] STEP/STL/GLB files export correctly

---

## Next Steps

After successful deployment:

1. **Review PR #2** on GitHub
2. **Merge to main** if all tests pass
3. **Tag release**: `git tag v1.0.0-production`
4. **Set up CI/CD** (GitHub Actions)
5. **Scale infrastructure** (Kubernetes)
6. **Add monitoring** (Prometheus/Grafana)
7. **Implement backups** (automated)

---

## Support

- **Documentation**: [PRODUCTION.md](./PRODUCTION.md)
- **Fixes Summary**: [FIXES.md](./FIXES.md)
- **PR Discussion**: [PR #2](https://github.com/featuretransformer/cad-ai-workstation/pull/2)
- **Logs**: `docker compose logs -f`
- **Issues**: https://github.com/featuretransformer/cad-ai-workstation/issues

---

**Ready to deploy? Run:**
```bash
./scripts/deploy-and-test.sh staging
```

🚀 **Good luck with your production deployment!**
