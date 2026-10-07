# 🚀 Production Deployment Guide

## Pre-Deployment Checklist

### 1. Environment Configuration
```bash
cp .env.example .env
# Edit .env and set:
# - DEV_MODE=false
# - CORS_ORIGINS=https://your-domain.com
# - SECRET_KEY=<random-32-char-string>
# - All API keys (GEMINI_API_KEY, GROQ_API_KEY)
# - Production database credentials
```

### 2. Database Setup
```bash
# Apply migrations
cd backend
alembic upgrade head

# Verify
alembic current
```

### 3. Build Production Images
```bash
# Full stack build
docker compose build

# Or individual services
docker compose build backend
docker compose build frontend
```

### 4. Start Services
```bash
# Production stack
docker compose up -d

# Check health
docker compose ps
docker compose logs -f backend
```

## Security Hardening

### API Security
- ✅ CORS restricted to specific origins
- ✅ Credentials only in dev mode
- ✅ CAD code execution sandboxed
- ✅ AST validation before execution
- ✅ No wildcard CORS in production

### Database
- ✅ Migrations managed via Alembic
- ✅ Connection pooling configured
- ✅ Cascading deletes for data integrity

### Container Security
- ✅ Multi-stage builds
- ✅ Non-root user (nextjs:nodejs)
- ✅ Minimal base images (alpine)
- ✅ .dockerignore for build optimization

## Monitoring

### Health Checks
```bash
# Backend
curl http://localhost:8000/api/health

# Frontend
curl http://localhost:3000

# Redis
docker compose exec redis redis-cli ping

# PostgreSQL
docker compose exec postgres pg_isready
```

### Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f celery-worker
```

## Scaling

### Horizontal Scaling
```yaml
# In docker-compose.yml
celery-worker:
  deploy:
    replicas: 4  # Scale workers

backend:
  deploy:
    replicas: 2  # Scale API servers
```

### Resource Limits
```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
```

## Troubleshooting

### Issue: CAD execution timeout
**Solution:** Increase `CAD_TIMEOUT_SECONDS` in `.env`

### Issue: LLM rate limits
**Solution:** Implement exponential backoff or add more API keys

### Issue: Database connection errors
**Solution:** Check `DATABASE_URL` and pg_isready

### Issue: Redis unavailable
**Solution:** Pipeline runs but no real-time WebSocket events

## Performance Optimization

1. **Enable PostgreSQL connection pooling**
2. **Configure Celery worker concurrency** (currently 2)
3. **Use Redis persistence** for task queue durability
4. **MinIO clustering** for high-availability storage
5. **CDN for static assets** (Next.js public/ folder)

## Backup Strategy

### Database
```bash
# Backup
docker compose exec postgres pg_dump -U caduser caddb > backup.sql

# Restore
docker compose exec -T postgres psql -U caduser caddb < backup.sql
```

### File Storage (MinIO)
```bash
# Export bucket
docker compose exec minio mc mirror /data/cad-exports /backup/
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Deploy Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push
        run: |
          docker compose build
          docker compose push
      - name: Deploy
        run: |
          ssh user@server "cd /app && docker compose pull && docker compose up -d"
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEV_MODE` | No | `true` | Enable development features |
| `CORS_ORIGINS` | Yes | `http://localhost:3000` | Comma-separated allowed origins |
| `SECRET_KEY` | Yes | - | Session secret (32+ chars) |
| `GEMINI_API_KEY` | Yes* | - | Google Gemini API key |
| `GROQ_API_KEY` | Yes* | - | Groq API key |
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `REDIS_URL` | Yes | - | Redis connection string |
| `CAD_TIMEOUT_SECONDS` | No | `60` | Max CAD execution time |
| `MAX_RETRIES` | No | `5` | Agent retry limit |

*At least one LLM API key required

## License
MIT - See LICENSE file
