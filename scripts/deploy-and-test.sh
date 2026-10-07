#!/bin/bash
# Production Deployment and Testing Script
# Usage: ./deploy-and-test.sh [staging|production]

set -e  # Exit on error

ENV=${1:-staging}
echo "🚀 Deploying to $ENV environment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

function log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

function log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ═══════════════════════════════════════════════════════
# 1. PRE-DEPLOYMENT CHECKS
# ═══════════════════════════════════════════════════════
log_info "Step 1: Pre-deployment checks..."

# Check if .env exists
if [ ! -f .env ]; then
    log_error ".env file not found! Copy from .env.example and configure."
    exit 1
fi

# Check required environment variables
source .env

if [ -z "$GEMINI_API_KEY" ] && [ -z "$GROQ_API_KEY" ]; then
    log_error "At least one LLM API key (GEMINI_API_KEY or GROQ_API_KEY) is required!"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    log_error "DATABASE_URL not set in .env"
    exit 1
fi

if [ "$ENV" == "production" ] && [ "$DEV_MODE" == "true" ]; then
    log_error "DEV_MODE=true in production environment! Set DEV_MODE=false"
    exit 1
fi

log_info "✅ Environment variables validated"

# ═══════════════════════════════════════════════════════
# 2. DATABASE MIGRATIONS
# ═══════════════════════════════════════════════════════
log_info "Step 2: Running database migrations..."

cd backend

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    log_info "Creating Python virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install/upgrade dependencies
log_info "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Run migrations
log_info "Applying Alembic migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    log_info "✅ Migrations applied successfully"
else
    log_error "Migration failed!"
    exit 1
fi

cd ..

# ═══════════════════════════════════════════════════════
# 3. BUILD DOCKER IMAGES
# ═══════════════════════════════════════════════════════
log_info "Step 3: Building Docker images..."

docker compose build --no-cache

if [ $? -eq 0 ]; then
    log_info "✅ Docker images built successfully"
else
    log_error "Docker build failed!"
    exit 1
fi

# ═══════════════════════════════════════════════════════
# 4. RUN TESTS
# ═══════════════════════════════════════════════════════
log_info "Step 4: Running test suite..."

cd backend
source .venv/bin/activate

log_info "Running production readiness tests..."
pytest tests/test_production_readiness.py -v --tb=short

if [ $? -eq 0 ]; then
    log_info "✅ Production tests passed"
else
    log_error "Tests failed! Fix issues before deploying."
    exit 1
fi

log_info "Running full test suite..."
pytest tests/ -v --tb=short -m "not slow"

cd ..

# ═══════════════════════════════════════════════════════
# 5. START SERVICES
# ═══════════════════════════════════════════════════════
log_info "Step 5: Starting services..."

# Stop existing containers
docker compose down

# Start services
docker compose up -d

if [ $? -eq 0 ]; then
    log_info "✅ Services started"
else
    log_error "Failed to start services!"
    exit 1
fi

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
sleep 10

# ═══════════════════════════════════════════════════════
# 6. HEALTH CHECKS
# ═══════════════════════════════════════════════════════
log_info "Step 6: Running health checks..."

# Check backend health
BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
if [ "$BACKEND_HEALTH" == "200" ]; then
    log_info "✅ Backend health check passed"
else
    log_error "Backend health check failed (HTTP $BACKEND_HEALTH)"
    docker compose logs backend
    exit 1
fi

# Check frontend
FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
if [ "$FRONTEND_HEALTH" == "200" ] || [ "$FRONTEND_HEALTH" == "307" ]; then
    log_info "✅ Frontend health check passed"
else
    log_warn "Frontend health check returned HTTP $FRONTEND_HEALTH"
fi

# Check database
docker compose exec -T postgres pg_isready -U caduser
if [ $? -eq 0 ]; then
    log_info "✅ Database health check passed"
else
    log_error "Database not ready!"
    exit 1
fi

# Check Redis
docker compose exec -T redis redis-cli ping > /dev/null
if [ $? -eq 0 ]; then
    log_info "✅ Redis health check passed"
else
    log_error "Redis not ready!"
    exit 1
fi

# ═══════════════════════════════════════════════════════
# 7. INTEGRATION TESTS WITH REAL LLM
# ═══════════════════════════════════════════════════════
log_info "Step 7: Running integration test with real LLM..."

# Create a simple test design request
TEST_PAYLOAD=$(cat <<EOF
{
  "session_id": "test-session-$(date +%s)",
  "prompt": "Create a simple washer with outer diameter 30mm, inner diameter 10mm, and thickness 4mm"
}
EOF
)

# Create test session first
SESSION_RESPONSE=$(curl -s -X POST \
  http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "Integration Test Session"}')

SESSION_ID=$(echo $SESSION_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -z "$SESSION_ID" ]; then
    log_error "Failed to create test session"
    exit 1
fi

log_info "Created test session: $SESSION_ID"

# Send design generation request
TEST_PAYLOAD=$(cat <<EOF
{
  "session_id": "$SESSION_ID",
  "prompt": "Create a simple washer with outer diameter 30mm, inner diameter 10mm, and thickness 4mm"
}
EOF
)

DESIGN_RESPONSE=$(curl -s -X POST \
  http://localhost:8000/api/design/generate \
  -H "Content-Type: application/json" \
  -d "$TEST_PAYLOAD")

DESIGN_ID=$(echo $DESIGN_RESPONSE | grep -o '"design_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$DESIGN_ID" ]; then
    log_error "Failed to initiate design generation"
    echo "Response: $DESIGN_RESPONSE"
    exit 1
fi

log_info "✅ Design generation initiated: $DESIGN_ID"
log_info "Waiting for pipeline to complete (60s)..."
sleep 60

# Check design status
DESIGN_STATUS=$(curl -s http://localhost:8000/api/design/$DESIGN_ID)
echo "$DESIGN_STATUS" | grep -q '"geometry_valid":true'

if [ $? -eq 0 ]; then
    log_info "✅ Integration test PASSED - Geometry generated and validated!"
else
    log_warn "Integration test completed but geometry may not be valid"
    echo "Design status: $DESIGN_STATUS"
fi

# ═══════════════════════════════════════════════════════
# 8. DEPLOYMENT SUMMARY
# ═══════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════════"
log_info "🎉 Deployment to $ENV completed successfully!"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Service URLs:"
echo "  Backend API:  http://localhost:8000"
echo "  Frontend:     http://localhost:3000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  Flower:       http://localhost:5555"
echo "  MinIO:        http://localhost:9001"
echo ""
echo "Health Check:"
echo "  curl http://localhost:8000/api/health"
echo ""
echo "View Logs:"
echo "  docker compose logs -f backend"
echo "  docker compose logs -f celery-worker"
echo ""
echo "Test Design ID: $DESIGN_ID"
echo ""

# ═══════════════════════════════════════════════════════
# 9. NEXT STEPS
# ═══════════════════════════════════════════════════════
log_info "Next Steps:"
echo "  1. Open http://localhost:3000 in browser"
echo "  2. Monitor logs: docker compose logs -f"
echo "  3. Run load tests: ./scripts/load-test.sh"
echo "  4. Check metrics: ./scripts/collect-metrics.sh"
echo ""

if [ "$ENV" == "staging" ]; then
    log_warn "This is a STAGING deployment. For production:"
    echo "  - Set DEV_MODE=false in .env"
    echo "  - Configure CORS_ORIGINS with production domains"
    echo "  - Use production database credentials"
    echo "  - Enable HTTPS/TLS"
    echo "  - Set up monitoring and backups"
fi
