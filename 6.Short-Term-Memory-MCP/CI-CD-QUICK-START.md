# CI/CD Pipeline - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Enable GitHub Actions (1 min)

1. Go to: **Settings** → **Actions** → **General**
2. Set: **"Allow all actions and reusable workflows"**
3. Set: **"Read and write permissions"** ✅
4. Check: **"Allow GitHub Actions to create and approve pull requests"** ✅
5. Click: **Save**

### Step 2: Configure Environments (2 min)

**Staging Environment**:

1. Go to: **Settings** → **Environments** → **New environment**
2. Name: `staging`
3. Deployment branches: **Selected branches** → `develop`
4. Click: **Save**

**Production Environment**:

1. **New environment** → Name: `production`
2. Deployment branches: **Selected branches** → `main`
3. **Environment protection rules**:
   - Check: **Required reviewers**
   - Add: 2+ reviewers from your team
4. Click: **Save**

### Step 3: Set Up Branch Protection (2 min)

**Protect `main` branch**:

1. Go to: **Settings** → **Branches** → **Add rule**
2. Branch name pattern: `main`
3. Check:
   - ☑ Require a pull request before merging (2 approvals)
   - ☑ Require status checks to pass before merging
   - ☑ Require conversation resolution before merging
4. Click: **Create**

### Step 4: Test the Pipeline

```bash
# Make a small change
echo "# CI/CD Pipeline Active" >> README.md

# Commit and push
git checkout -b test-pipeline
git add README.md
git commit -m "test: verify CI/CD pipeline"
git push origin test-pipeline

# Create PR
gh pr create --base develop --title "Test: Verify CI/CD"
```

✅ **You're done!** Watch your pipeline run in the **Actions** tab.

---

## 📋 Daily Developer Workflow

### Starting New Work

```bash
# 1. Create feature branch
git checkout develop
git pull
git checkout -b feature/my-feature

# 2. Make changes
vim short_term_mcp/module.py

# 3. Test locally
pytest short_term_mcp/tests/ -v

# 4. Format code
black short_term_mcp/
isort short_term_mcp/

# 5. Commit
git add .
git commit -m "feat: add new feature"

# 6. Push
git push origin feature/my-feature

# 7. Create PR
gh pr create --base develop --title "feat: add new feature"
```

### Pre-Commit Checklist

Before pushing code, run:

```bash
# Quick validation
black --check short_term_mcp/      # Formatting
isort --check-only short_term_mcp/ # Imports
flake8 short_term_mcp/             # Linting
pytest short_term_mcp/tests/ -v    # Tests
```

**All pass?** ✅ Safe to push!

---

## 🎯 Pipeline Cheat Sheet

### Pipeline Triggers

| Action | Branch      | Pipeline Runs? | Deploys To                    |
| ------ | ----------- | -------------- | ----------------------------- |
| Push   | `main`      | ✅ Full        | 🌟 Production (with approval) |
| Push   | `develop`   | ✅ Full        | 🚀 Staging (automatic)        |
| Push   | `feature/*` | ✅ Tests only  | -                             |
| PR     | `main`      | ✅ Full        | -                             |
| PR     | `develop`   | ✅ Tests only  | -                             |

### Pipeline Stages (in order)

```
1. 🔨 Build & Setup        (~2 min)  ← Installs dependencies
2. 🔍 Code Quality         (~1 min)  ← black, isort, flake8
3. 🔒 Security Scan        (~1 min)  ← bandit, safety
4. 🧪 Unit Tests           (~2 min)  ← 159 tests, coverage
5. 🔗 Integration Tests    (~2 min)  ← End-to-end tests
6. 📦 Package Artifacts    (~1 min)  ← Build wheel/sdist
7. 🚀 Deploy Staging       (~1 min)  ← If develop branch
8. 🌟 Deploy Production    (manual)  ← If main + approval
```

**Total Time**: ~10 minutes

### Quick Fixes

**Formatting issues?**

```bash
black short_term_mcp/
isort short_term_mcp/
git add . && git commit -m "style: fix formatting" && git push
```

**Tests failing?**

```bash
pytest short_term_mcp/tests/ -v --tb=short
# Fix issues, then:
git add . && git commit -m "test: fix failing tests" && git push
```

**Coverage too low?**

```bash
# View coverage report
pytest short_term_mcp/tests/ --cov=short_term_mcp --cov-report=html
open htmlcov/index.html
# Add tests for uncovered code
```

---

## 🆘 Common Issues & Solutions

### Issue: "Code formatting issues found"

**Quick Fix**:

```bash
black short_term_mcp/ && isort short_term_mcp/
git add . && git commit -m "style: auto-fix" && git push
```

### Issue: "Coverage below 80%"

**Options**:

1. Add more tests (recommended)
2. Lower threshold in `.github/workflows/ci-cd.yml`:
   ```yaml
   env:
     MIN_COVERAGE_PERCENT: 75
   ```

### Issue: "Production deployment waiting"

**Action Required**:

1. Go to: **Actions** → Select workflow run
2. Click: **Review deployments**
3. Select: `production`
4. Click: **Approve and deploy**

### Issue: "Security issues found"

**Steps**:

1. Download `security-reports` artifact from workflow
2. Review `bandit-report.json`
3. Fix security issues in code
4. Re-run pipeline

---

## 📊 Monitoring Your Pipeline

### View Pipeline Status

```bash
# Via GitHub CLI
gh run list --limit 5

# View specific run
gh run view <run-id>

# Watch live
gh run watch
```

### Download Artifacts

```bash
# List artifacts
gh run download <run-id> --name security-reports

# Download all artifacts
gh run download <run-id>
```

### Check Release Status

```bash
# List releases
gh release list

# View latest release
gh release view
```

---

## 🎓 Learn More

- **Full Documentation**: [`docs/CI-CD-PIPELINE.md`](docs/CI-CD-PIPELINE.md)
- **Pipeline Config**: [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml)
- **Code Quality Config**: [`pyproject.toml`](pyproject.toml)

---

## 📞 Need Help?

1. Check: [Full Documentation](docs/CI-CD-PIPELINE.md) → [Troubleshooting Section](docs/CI-CD-PIPELINE.md#troubleshooting)
2. Review: Workflow logs in **Actions** tab
3. Ask: Team in Slack/Discord

---

**Status**: ✅ Ready to use
**Last Updated**: 2025-11-12
**Pipeline Version**: v1.0
