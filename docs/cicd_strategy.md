# CI/CD Strategy & Version Control Guide

> Comprehensive guide for the CI/CD pipeline, version control strategy,
> and gray/canary release process.

---

## Table of Contents
1. [Branch Strategy](#1-branch-strategy)
2. [Semantic Versioning](#2-semantic-versioning)
3. [CI Pipeline (Continuous Integration)](#3-ci-pipeline)
4. [CD Pipeline (Continuous Deployment)](#4-cd-pipeline)
5. [Gray / Canary Release](#5-gray--canary-release)
6. [Rollback Strategy](#6-rollback-strategy)
7. [Feature Flags](#7-feature-flags)
8. [Monitoring & Health Checks](#8-monitoring--health-checks)

---

## 1. Branch Strategy

```
main          ← production-ready, tagged releases
  ↑
develop       ← integration branch, staging deployments
  ↑
feature/*     ← individual features, PR into develop
release/*     ← release prep, PR into main
hotfix/*      ← emergency fixes from main
```

### Rules
| Branch | Purpose | Deploy to |
|--------|---------|-----------|
| `main` | Production code, tagged releases | Production (via CD) |
| `develop` | Integration, latest dev changes | Staging |
| `feature/*` | New features | None (PR-only) |
| `release/*` | Release preparation | Staging → Production |
| `hotfix/*` | Emergency fixes | Production |

### Workflow
1. Create `feature/xyz` from `develop`
2. Work on feature, push to GitHub
3. Open PR → `develop` (CI runs on PR)
4. Merge to `develop` → auto-deploy to staging
5. Create `release/v1.2.0` from `develop`
6. Open PR → `main`, tag `v1.2.0` → canary release
7. Canary passes → full production rollout

---

## 2. Semantic Versioning

Format: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)

| Segment | When to bump | Example |
|---------|-------------|---------|
| MAJOR | Breaking changes | 1.x.x → 2.0.0 |
| MINOR | New features (backward compatible) | 1.0.x → 1.1.0 |
| PATCH | Bug fixes | 1.0.0 → 1.0.1 |

### Tags
```bash
# Create a release tag
git tag -a v1.1.0 -m "Release v1.1.0 - GNS3 support"
git push origin v1.1.0

# This triggers the CD pipeline canary release
```

---

## 3. CI Pipeline

**File**: `.github/workflows/ci.yml`
**Triggers**: Push to `main`/`develop`, PR to `main`/`develop`

### Jobs

```
push/PR to main or develop
        │
        ├──► lint (flake8 + black --check)
        │
        ├──► test (pytest + coverage ≥ 70%)
        │
        ├──► security (bandit scan, no HIGH issues)
        │
        └──► build (Docker image build + health check)
              (depends on test + security passing)
```

### CI Checks

| Check | Tool | Fail Condition |
|-------|------|----------------|
| Code style | flake8 | Any error |
| Format | black --check | Unformatted file |
| Tests | pytest | Any test fails |
| Coverage | pytest-cov | < 70% coverage |
| Security | bandit | Any HIGH severity issue |
| Build | docker build | Build fails or health check fails |

---

## 4. CD Pipeline

**File**: `.github/workflows/cd.yml`
**Triggers**: Push to `main`, tag `v*.*.*`

### Deployment Flow

```
push to main                    tag v1.2.0
    │                               │
    ▼                               ▼
build & push image             build & push image
    │                               │
    ▼                               ▼
deploy to staging              canary release
    │                          (10% traffic initially)
    ▼                               │
smoke tests                         ▼
    │                          health check (30s soak)
    ▼                               │
notification                    ┌──────┴──────┐
                           pass │             │ fail
                                ▼             ▼
                        promote to prod    rollback
```

---

## 5. Gray / Canary Release

### Architecture

```
           ┌─────────────────────────────────┐
           │      Nginx Load Balancer         │
           │      (port 8080)                 │
           │  90% → app-blue  10% → canary   │
           └────────┬────────────┬───────────┘
                    │            │
           ┌────────▼──┐   ┌────▼────────┐
           │ app-blue  │   │ app-canary  │
           │ :5000     │   │ :5001       │
           │ v1.0.0    │   │ v1.1.0      │
           │ (stable)  │   │ (canary)    │
           └───────────┘   └────────────┘
```

### Canary Phases

| Phase | Traffic | Duration | Pass Criteria |
|-------|---------|----------|---------------|
| Phase 1 | 10% | 5 min | 0 errors, p99 < 500ms |
| Phase 2 | 30% | 5 min | 0 errors, p99 < 500ms |
| Phase 3 | 50% | 5 min | 0 errors, p99 < 500ms |
| Phase 4 | 100% | — | Full promotion |

### Starting a Canary Release

```bash
# 1. Tag a release
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0

# 2. CD pipeline auto-starts canary at 10%
# 3. Monitor health: http://localhost:8080/health
# 4. Access canary directly: http://localhost:5001/health
# 5. Access canary via LB: http://localhost:8080/canary/

# Manual canary (docker-compose)
docker-compose --profile canary up -d

# Adjust canary traffic (edit nginx.conf weights, reload)
docker exec challenge-net-nginx nginx -s reload
```

### Canary Feature Flags

```bash
# Environment variables (CI/CD injection)
export FEATURE_CANARY_RELEASE=true
export FEATURE_CANARY_PERCENTAGE=10

# Or edit config/feature_flags.json
{
  "canary_release": true,
  "canary_percentage": 10
}

# Verify via API
curl http://localhost:5000/api/features | python -m json.tool
```

---

## 6. Rollback Strategy

### Quick Rollback

```bash
# 1. Stop canary, revert to stable
docker-compose down
docker-compose up -d  # only blue container starts

# 2. Reset feature flags
export FEATURE_CANARY_RELEASE=false
export FEATURE_CANARY_PERCENTAGE=0

# 3. Re-deploy previous version tag
git checkout v1.1.0
docker-compose build --no-cache
docker-compose up -d
```

### Git-based Rollback

```bash
# Find previous stable tag
git tag --sort=-creatordate | head -5

# Revert to that commit
git revert HEAD --no-commit
git commit -m "Rollback to v1.1.0"
git push origin main
```

---

## 7. Feature Flags

**Module**: `backend/feature_flags.py`
**Config**: `config/feature_flags.json`

### Available Flags

| Flag | Default | Description |
|------|---------|-------------|
| `canary_release` | false | Enable canary routing |
| `canary_percentage` | 0 | Traffic % to canary (0-100) |
| `enable_validation_alerts` | true | Show validation alerts in UI |
| `enable_backup_on_config` | true | Auto-backup after config change |
| `enable_sim_mode_default` | false | Default to simulation mode |
| `max_vlans_per_request` | 50 | Max VLANs per API call |
| `maintenance_mode` | false | Put app in maintenance mode |
| `enable_audit_log` | true | Enable audit logging |

### Override via Environment

```bash
# Format: FEATURE_<FLAG_NAME_UPPERCASE>
export FEATURE_CANARY_RELEASE=true
export FEATURE_CANARY_PERCENTAGE=25
export FEATURE_MAINTENANCE_MODE=false
```

---

## 8. Monitoring & Health Checks

### Endpoints

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `/health` | Liveness probe | status, uptime, version |
| `/ready` | Readiness probe | checks, ready bool, canary status |
| `/api/features` | Debug flag state | all flag values |

### Docker Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; \
    urllib.request.urlopen('http://localhost:5000/health').read()"
```

### Monitoring Commands

```bash
# Check all containers
docker-compose ps

# View logs (follow)
docker-compose logs -f app-blue
docker-compose logs -f app-canary

# Health check from host
curl http://localhost:5000/health
curl http://localhost:5001/health   # canary
curl http://localhost:8080/health   # via LB

# Check which backend served request
curl -v http://localhost:8080/ 2>&1 | grep X-Served-By
```
