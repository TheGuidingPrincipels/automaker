# CI/CD Pipeline Quick Reference

Quick commands and references for the CI/CD pipeline.

---

## 🚀 Common Operations

### Run Tests Locally

```bash
# Install dependencies
uv sync

# Run linting
uv pip install --system ruff black isort
ruff check .
black --check .
isort --check-only .

# Run unit tests
uv run pytest tests/unit/ --cov=. --cov-report=term-missing

# Run integration tests (requires services)
docker-compose up -d
uv run pytest tests/integration/ tests/e2e/

# Run security scans
uv pip install --system bandit safety
bandit -r . -ll
safety check
```

### Trigger Pipeline

```bash
# Automatic trigger - just push
git push origin <branch-name>

# Manual trigger - use GitHub UI
# Go to: Actions → CI/CD Pipeline → Run workflow
```

### Deploy to Staging

```bash
# Merge to develop branch
git checkout develop
git merge feature/my-feature
git push origin develop
# Pipeline automatically deploys to staging
```

### Deploy to Production

```bash
# Create PR from develop to main
git checkout main
git merge develop
git push origin main
# Wait for approval, then deployment proceeds
```

### Rollback

```bash
# Use GitHub UI:
# 1. Go to Actions → CI/CD Pipeline → Run workflow
# 2. Select environment: production
# 3. Enter version tag: v0.1.0-main-abc12345
# 4. Click "Run workflow"
```

---

## 📊 Pipeline Stages

| Stage          | Duration  | Runs On      | Purpose                         |
| -------------- | --------- | ------------ | ------------------------------- |
| Lint           | 5-10 min  | All branches | Code quality checks             |
| Security       | 10-15 min | All branches | Vulnerability scanning          |
| Unit Tests     | 15-20 min | All branches | Fast tests without dependencies |
| Integration    | 25-30 min | All branches | Tests with Neo4j, Redis         |
| Build          | 10-15 min | All branches | Package creation                |
| Deploy Staging | 15-20 min | `develop`    | Auto-deploy to staging          |
| Deploy Prod    | 20-30 min | `main`       | Manual approval required        |

---

## 🌳 Branch Strategy

```
feature/xyz ──► develop ──► main
     │            │          │
     │            │          │
  Tests only   Staging    Production
                          (approval)
```

**Branch Naming**:

- Feature: `feature/description`
- Hotfix: `hotfix/description`
- Release: `release/v1.0.0`

**Protection**:

- `main`: Requires 1+ approval, all tests must pass
- `develop`: All tests must pass

---

## 🔐 Required Secrets

### Repository Secrets

| Secret                  | Purpose              | Example           |
| ----------------------- | -------------------- | ----------------- |
| `DEPLOY_SSH_KEY`        | SSH deployment       | Private key       |
| `DOCKER_REGISTRY_TOKEN` | Docker registry auth | Token             |
| `KUBE_CONFIG`           | Kubernetes config    | Base64 kubeconfig |
| `NEO4J_PROD_PASSWORD`   | Production database  | Strong password   |
| `SLACK_WEBHOOK_URL`     | Notifications        | Webhook URL       |

### Environment Secrets

Set in **Settings → Environments → [env] → Add secret**

**Staging**:

- `STAGING_DATABASE_URL`
- `STAGING_API_KEY`

**Production**:

- `PRODUCTION_DATABASE_URL`
- `PRODUCTION_API_KEY`

---

## ⚙️ Configuration Files

| File                          | Purpose                   |
| ----------------------------- | ------------------------- |
| `.github/workflows/ci-cd.yml` | Pipeline definition       |
| `.ruff.toml`                  | Linting rules (Ruff)      |
| `.bandit`                     | Security scan config      |
| `pyproject.toml`              | Black, isort, mypy config |

---

## 🐛 Troubleshooting

### Pipeline Fails on Lint

```bash
# Fix locally first
ruff check . --fix
black .
isort .

# Commit and push
git add .
git commit -m "fix: Resolve linting issues"
git push
```

### Coverage Below Threshold

```bash
# Check current coverage
uv run pytest tests/ --cov=. --cov-report=term-missing

# Add tests or adjust threshold in workflow
# .github/workflows/ci-cd.yml: COVERAGE_THRESHOLD: 55
```

### Integration Tests Fail

```bash
# Ensure services are running locally
docker-compose up -d
docker-compose ps  # Verify all healthy

# Run tests locally
uv run pytest tests/integration/ -v
```

### Deployment Fails

1. Check deployment logs in GitHub Actions
2. Verify secrets are set correctly
3. Test SSH/Docker/K8s access manually
4. Check smoke tests pass locally

### Production Approval Not Working

- Verify environment protection rules set
- Check designated reviewers have permissions
- Cannot approve your own deployments

---

## 📈 Metrics to Monitor

### Pipeline Health

- **Success Rate**: Target > 95%
- **Average Duration**: Target < 40 minutes
- **Time to Deploy**: Target < 60 minutes (commit to production)

### Test Coverage

- **Current**: 55%
- **Target**: 70%
- **Trend**: Should increase over time

### Deployment Frequency

- **Staging**: Multiple times per day
- **Production**: At least weekly
- **Rollback Rate**: < 5%

---

## 🔗 Quick Links

- **Pipeline Runs**: [Actions Tab](../../actions)
- **Full Documentation**: [CI-CD-PIPELINE.md](./CI-CD-PIPELINE.md)
- **Setup Guide**: [PIPELINE-SETUP-GUIDE.md](./PIPELINE-SETUP-GUIDE.md)
- **Onboarding**: [PIPELINE-ONBOARDING-CHECKLIST.md](./PIPELINE-ONBOARDING-CHECKLIST.md)

---

## 📞 Support

**Pipeline Issues**:

1. Check logs in GitHub Actions
2. Review this quick reference
3. Consult full documentation
4. Contact DevOps team

**Emergency Rollback**:

1. Use manual workflow dispatch
2. Select production environment
3. Enter last known good version tag
4. Notify team in Slack

---

## 🎯 Best Practices

✅ **DO**:

- Run tests locally before pushing
- Write meaningful commit messages
- Keep PRs small and focused
- Review pipeline logs after merge
- Monitor deployment notifications

❌ **DON'T**:

- Push directly to `main` or `develop`
- Ignore pipeline failures
- Skip code review
- Deploy without testing in staging first
- Bypass branch protection rules

---

**Last Updated**: 2025-11-14
**Version**: 1.0
