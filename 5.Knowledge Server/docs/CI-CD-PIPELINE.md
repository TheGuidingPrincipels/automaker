# CI/CD Pipeline Documentation

## Overview

This repository uses **GitHub Actions** for a fully automated CI/CD pipeline that implements industry best practices for continuous integration and continuous delivery.

**Pipeline File**: `.github/workflows/ci-cd.yml`

---

## 🎯 Pipeline Architecture

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRIGGER (Push/PR)                        │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ├──► Stage 1: Code Quality & Linting (parallel)
              │    └─ ruff, black, isort, mypy
              │
              ├──► Stage 2: Security Scanning (parallel)
              │    └─ bandit (SAST), safety, pip-audit
              │
              ├──► Stage 3: Unit Tests (parallel, matrix)
              │    └─ pytest on Python 3.11 & 3.12
              │    └─ Coverage threshold: 55%
              │
              ├──► Stage 4: Integration Tests (parallel)
              │    └─ pytest with Neo4j, Redis services
              │    └─ E2E workflow tests
              │
              ├──► Stage 5: Build & Package (after quality gates)
              │    └─ Python wheel + source dist
              │    └─ Artifact with commit SHA
              │
              ├──► Stage 6: Deploy to Staging (develop branch only)
              │    └─ Automatic deployment
              │    └─ Smoke tests
              │
              └──► Stage 7: Deploy to Production (main branch only)
                   └─ Manual approval required
                   └─ Rollback point creation
                   └─ Production smoke tests
```

---

## 🚀 How the Pipeline Works

### Trigger Conditions

| Trigger             | Branches                | Stages Executed                                          | Deployment                               |
| ------------------- | ----------------------- | -------------------------------------------------------- | ---------------------------------------- |
| **Push**            | `feature/*`, `hotfix/*` | Lint → Security → Unit Tests → Integration Tests → Build | None                                     |
| **Push**            | `develop`               | All stages                                               | Auto-deploy to **Staging**               |
| **Push**            | `main`, `master`        | All stages                                               | Deploy to **Production** (with approval) |
| **Pull Request**    | `→ main`, `→ develop`   | Lint → Security → Unit Tests → Integration Tests         | None                                     |
| **Manual Dispatch** | Any                     | All stages                                               | Deploy to selected environment           |

### Branch Strategy

```
feature/my-feature ──► develop ──► main
     │                   │           │
     │                   │           │
     └─ Runs tests       └─ Staging  └─ Production
                                          (requires approval)
```

**Recommended Workflow**:

1. Create feature branch from `develop`: `git checkout -b feature/my-feature develop`
2. Make changes, commit, and push
3. Pipeline runs: lint, security, tests, build
4. Create PR to `develop` when ready
5. After merge to `develop`: automatic staging deployment
6. Create PR from `develop` to `main` for production
7. After merge to `main`: manual approval required for production deployment

---

## 📊 Pipeline Jobs Explained

### Job 1: Code Quality & Linting (10 min)

**Purpose**: Fast feedback on code quality issues before expensive test runs.

**Tools**:

- **Ruff**: Fast Python linter (replaces flake8, pylint)
- **Black**: Code formatter (enforces consistent style)
- **isort**: Import sorting and organization
- **mypy**: Type checking (non-blocking)

**Customization**:

```yaml
# In .github/workflows/ci-cd.yml
- name: Install linting tools
  run: |
    uv pip install --system ruff black isort mypy
    # Add more linters here if needed
```

**Configuration Files** (optional):

- `.ruff.toml` - Ruff linter settings
- `pyproject.toml` - Black, isort, mypy settings

---

### Job 2: Security Scanning (15 min)

**Purpose**: Identify security vulnerabilities early (SAST + dependency scanning).

**Tools**:

- **Bandit**: Static Application Security Testing (SAST)
  - Checks for: hardcoded passwords, SQL injection, unsafe YAML, etc.
  - Severity levels: low, medium, high
- **Safety**: Known vulnerability database for Python packages
- **pip-audit**: Official Python package auditor

**Security Threshold**:

```yaml
env:
  BANDIT_SEVERITY: medium # Fail on medium+ severity issues
```

**Artifacts**:

- `bandit-report.json` - Detailed security report (retained 30 days)

**Customization**:

- Adjust `BANDIT_SEVERITY` in workflow file
- Add `.bandit` config file to exclude false positives

---

### Job 3: Unit Tests (20 min)

**Purpose**: Fast tests without external dependencies, verify core logic.

**Test Matrix**: Runs on Python 3.11 and 3.12 in parallel

**Coverage Requirements**:

```yaml
env:
  COVERAGE_THRESHOLD: 55 # Minimum 55% coverage required
```

**Commands**:

```bash
uv run pytest tests/unit/ \
  --cov=. \
  --cov-report=xml \
  --cov-fail-under=55 \
  --maxfail=5  # Stop after 5 failures
```

**Artifacts**:

- `coverage.xml` - Coverage report (for Codecov)
- `htmlcov/` - HTML coverage report
- `junit-unit-tests.xml` - Test results

**Customization**:

- Change `COVERAGE_THRESHOLD` to match your project goals
- Add/remove Python versions in matrix strategy
- Configure coverage in `pyproject.toml` (tool.coverage section)

---

### Job 4: Integration Tests (30 min)

**Purpose**: Test interactions with real external services.

**Services** (via Docker):

- **Neo4j 5**: Graph database
- **Redis 7**: Cache and session storage

**Service Health Checks**:

```yaml
services:
  neo4j:
    options: >-
      --health-cmd "cypher-shell -u neo4j -p test_password_12345 'RETURN 1'"
      --health-interval 10s
```

**Environment Variables**:

```yaml
env:
  NEO4J_URI: bolt://localhost:7687
  NEO4J_PASSWORD: test_password_12345
  REDIS_URL: redis://localhost:6379
```

**Database Initialization**:

```bash
uv run python scripts/init_database.py
uv run python scripts/init_neo4j.py
uv run python scripts/init_chromadb.py
```

**Customization**:

- Add more services (PostgreSQL, MongoDB, etc.) in `services:` section
- Update credentials in workflow environment variables
- Modify initialization scripts as needed

---

### Job 5: Build & Package (15 min)

**Purpose**: Create distributable artifacts with proper versioning.

**Versioning Strategy**:

```
Format: 0.1.0-{branch}-{commit-sha}
Example: 0.1.0-develop-a1b2c3d4
```

**Build Process**:

1. Generate version from Git branch + commit SHA
2. Build Python wheel and source distribution (`python -m build`)
3. Verify package integrity (`twine check`)
4. Create deployment artifact bundle:
   - Python distributions
   - Dependencies (`requirements.txt`, `uv.lock`)
   - Configuration files (`.env.example`, `docker-compose.yml`)
   - Initialization scripts
   - Version metadata

**Artifacts**:

- `mcp-knowledge-server-{version}.tar.gz` - Complete deployment bundle
- `dist/*.whl` - Python wheel
- `dist/*.tar.gz` - Source distribution

**Retention**: 90 days

**Customization**:

- Modify version format in `Generate version from git` step
- Add/remove files in artifact bundle
- Change build tool (currently uses `build`, could use `poetry`, `flit`, etc.)

---

### Job 6: Deploy to Staging (20 min)

**Purpose**: Automatic deployment to staging for testing before production.

**Trigger**: Push to `develop` branch OR manual dispatch

**Environment**: `staging`

- URL: `https://staging.mcp-knowledge-server.example.com` (customize this)

**Process**:

1. Download build artifacts
2. Extract deployment bundle
3. **Deploy** (placeholder - customize for your infrastructure)
4. Run smoke tests
5. Notify on success/failure

**Customization Required**:

```yaml
- name: Deploy to staging (Placeholder)
  run: |
    # Replace with actual deployment commands:
    # Examples:
    # - Kubernetes: kubectl apply -f k8s/staging/
    # - Docker: docker-compose -f docker-compose.staging.yml up -d
    # - AWS: aws deploy ...
    # - SSH: scp artifacts/* user@staging:/app/
```

**Smoke Tests** (customize):

```bash
# Example smoke tests:
curl -f https://staging.example.com/health || exit 1
python scripts/smoke_tests.py --env staging
```

---

### Job 7: Deploy to Production (30 min)

**Purpose**: Production deployment with manual approval gate.

**Trigger**: Push to `main`/`master` branch OR manual dispatch

**Environment**: `production`

- URL: `https://mcp-knowledge-server.example.com` (customize this)
- **Requires manual approval** (configure in GitHub Settings → Environments)

**Process**:

1. Wait for manual approval
2. Create rollback point (save current state)
3. Download build artifacts
4. **Deploy** (placeholder - customize for your infrastructure)
5. Run production smoke tests
6. Create Git release tag
7. Notify stakeholders

**Rollback Point**:

```yaml
- name: Create rollback point
  run: |
    # Examples:
    # - Tag current Docker image
    # - Backup database
    # - Save Kubernetes state
    echo "Previous version saved for rollback"
```

**Customization Required**:

- Add real deployment commands
- Implement rollback strategy
- Add notification integrations (Slack, email, PagerDuty)
- Configure production smoke tests

---

### Job 8: Rollback (Manual Only)

**Purpose**: Emergency rollback to previous version.

**Trigger**: Manual workflow dispatch ONLY

**Usage**:

1. Go to Actions → CI/CD Pipeline → Run workflow
2. Select environment: `staging` or `production`
3. Enter version tag to roll back to: `v0.1.0-main-abc12345`
4. Click "Run workflow"

**Customization Required**:

```yaml
- name: Perform rollback
  run: |
    # Examples:
    # - Restore previous Docker image
    # - Revert Kubernetes deployment
    # - Restore database backup
```

---

## ⚙️ Configuration & Customization

### Environment Variables (Workflow Level)

Edit in `.github/workflows/ci-cd.yml`:

```yaml
env:
  PYTHON_VERSION: '3.11' # Python version for build/deploy
  COVERAGE_THRESHOLD: 55 # Minimum test coverage %
  BANDIT_SEVERITY: medium # Security scan sensitivity
  NEO4J_PASSWORD: test_password_12345 # Neo4j test password
```

### GitHub Secrets (Required for Deployment)

Add in **Settings → Secrets and variables → Actions**:

| Secret Name             | Description                       | Used In             |
| ----------------------- | --------------------------------- | ------------------- |
| `DEPLOY_SSH_KEY`        | SSH private key for VM deployment | Deploy jobs         |
| `DOCKER_REGISTRY_TOKEN` | Docker Hub/Registry auth token    | Build/Deploy        |
| `KUBE_CONFIG`           | Kubernetes config (base64)        | K8s deployment      |
| `NEO4J_PROD_PASSWORD`   | Production Neo4j password         | Production deploy   |
| `SLACK_WEBHOOK_URL`     | Slack notifications               | All jobs (optional) |

### GitHub Environments (Required for Deployment)

Set up in **Settings → Environments**:

1. **Create `staging` environment**:
   - No protection rules needed
   - Add environment secrets if different from repo secrets
   - Set environment URL: `https://staging.example.com`

2. **Create `production` environment**:
   - ✅ Enable "Required reviewers" (at least 1)
   - Add production-specific secrets
   - Set environment URL: `https://example.com`
   - Optional: Limit to `main` branch only

---

## 📝 Maintenance & Troubleshooting

### How to Trigger the Pipeline

1. **Automatic** (on every push):

   ```bash
   git push origin feature/my-feature
   ```

2. **Manual** (for deployments):
   - GitHub UI → Actions → CI/CD Pipeline → Run workflow
   - Select branch, environment, and version tag

### Common Issues

#### ❌ Coverage Below Threshold

```
Error: Coverage is 52%, minimum is 55%
```

**Solutions**:

- Add more tests to improve coverage
- Lower `COVERAGE_THRESHOLD` temporarily (not recommended)
- Exclude files in `pyproject.toml`:
  ```toml
  [tool.coverage.run]
  omit = ["tests/*", "*/migrations/*"]
  ```

#### ❌ Integration Tests Fail (Service Unavailable)

```
Error: Connection refused to Neo4j at localhost:7687
```

**Solutions**:

- Check service health check timeouts
- Increase `health-start-period` in workflow
- Verify service credentials match environment variables

#### ❌ Security Scan Failures

```
Error: Bandit found high-severity issue
```

**Solutions**:

- Review and fix security issues
- Add `.bandit` exclusion file for false positives:
  ```yaml
  # .bandit
  skips: ['B101', 'B601']
  ```

#### ❌ Build Artifacts Not Found

```
Error: Unable to download artifact
```

**Solutions**:

- Ensure `build` job completed successfully
- Check artifact retention period (90 days)
- Verify `needs:` dependencies in deploy jobs

### Viewing Pipeline Results

1. **GitHub UI**: Actions tab → Select workflow run
2. **Logs**: Click on job → Expand step to see detailed logs
3. **Artifacts**: Scroll to bottom of workflow run → Artifacts section

### Performance Optimization

**Current Timings** (approximate):

- Lint: 5-10 min
- Security: 10-15 min
- Unit Tests: 15-20 min (parallelized)
- Integration Tests: 25-30 min
- Build: 10-15 min
- **Total**: ~30-40 min (parallel execution)

**Optimization Tips**:

1. **Cache dependencies**: Already enabled via `cache: 'pip'`
2. **Parallelize tests**: Use pytest-xdist
   ```bash
   uv run pytest -n auto
   ```
3. **Skip slow tests in PR**: Use markers
   ```bash
   pytest -m "not slow"
   ```
4. **Self-hosted runners**: For faster builds (GitHub-hosted are free but slower)

---

## 🔄 Updating the Pipeline

### Adding a New Test Stage

```yaml
new-test-stage:
  name: My New Test Stage
  runs-on: ubuntu-latest
  needs: [lint] # Dependencies
  steps:
    - uses: actions/checkout@v4
    - name: Run custom tests
      run: |
        # Your test commands
```

### Adding a New Environment

1. Create environment in GitHub Settings
2. Add deployment job:
   ```yaml
   deploy-qa:
     name: Deploy to QA
     needs: [build]
     if: github.ref == 'refs/heads/qa'
     environment:
       name: qa
       url: https://qa.example.com
   ```

### Changing Python Version

Update in multiple places:

```yaml
env:
  PYTHON_VERSION: '3.12' # Top-level env

# AND update matrix in unit-tests job:
strategy:
  matrix:
    python-version: ['3.12', '3.13']
```

---

## 📚 Additional Resources

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **UV Package Manager**: https://github.com/astral-sh/uv
- **Pytest Documentation**: https://docs.pytest.org/
- **Security Tools**:
  - Bandit: https://bandit.readthedocs.io/
  - Safety: https://pyup.io/safety/

---

## 🎓 Pipeline Best Practices Implemented

✅ **Fail-Fast**: Linting and security run first (fastest feedback)
✅ **Parallel Execution**: Independent jobs run simultaneously
✅ **Test Matrix**: Multiple Python versions tested
✅ **Coverage Enforcement**: Minimum 55% coverage required
✅ **Security Scanning**: SAST + dependency vulnerabilities
✅ **Artifact Versioning**: Commit SHA + branch in version
✅ **Manual Production Approval**: Prevent accidental deployments
✅ **Rollback Capability**: Emergency rollback via manual trigger
✅ **Environment Separation**: Staging → Production progression
✅ **Audit Trail**: All deployments logged with Git tags
✅ **Declarative Pipeline**: Entire CI/CD in version-controlled YAML

---

## 🆘 Support

For pipeline issues:

1. Check this documentation
2. Review workflow logs in GitHub Actions tab
3. Consult `docs/PIPELINE-SETUP-GUIDE.md` for initial setup
4. Contact DevOps team or create an issue

---

**Last Updated**: 2025-11-14
**Pipeline Version**: 1.0
**Maintained By**: DevOps Team
