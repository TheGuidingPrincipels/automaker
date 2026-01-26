# CI/CD Pipeline Documentation

## 📋 Table of Contents

1. [Overview](#overview)
2. [Pipeline Architecture](#pipeline-architecture)
3. [Branch Strategy](#branch-strategy)
4. [Pipeline Stages](#pipeline-stages)
5. [Setup & Configuration](#setup--configuration)
6. [Environment Management](#environment-management)
7. [Secrets & Security](#secrets--security)
8. [Triggering the Pipeline](#triggering-the-pipeline)
9. [Monitoring & Observability](#monitoring--observability)
10. [Troubleshooting](#troubleshooting)
11. [Onboarding Checklist](#onboarding-checklist)
12. [Customization Guide](#customization-guide)
13. [Rollback Procedures](#rollback-procedures)
14. [Best Practices](#best-practices)

---

## Overview

This repository implements a comprehensive, industry-standard CI/CD pipeline using **GitHub Actions**. The pipeline ensures code quality, security, and reliable deployments through automated testing, security scanning, and controlled release processes.

### Key Features

- ✅ **Fully Automated**: From code commit to production deployment
- 🚀 **Fast Feedback**: Fail-fast approach with parallel job execution
- 🔒 **Security First**: SAST scanning, dependency vulnerability checks
- 🧪 **Comprehensive Testing**: 159 unit tests + integration tests
- 📦 **Artifact Management**: Versioned packages with build manifests
- 🎯 **Multi-Environment**: Staging and production environments
- 🔄 **Rollback Support**: Easy rollback to previous releases
- 📊 **Observable**: Detailed logging and status reporting

### Technology Stack

- **CI/CD Platform**: GitHub Actions
- **Language**: Python 3.11+
- **Package Manager**: pip, uv
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Code Quality**: flake8, black, isort, mypy
- **Security**: bandit (SAST), safety (dependency scanning)
- **Deployment**: GitHub Releases

---

## Pipeline Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        CODE COMMIT/PR                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1: BUILD & SETUP                                          │
│  • Install dependencies                                          │
│  • Build Python package                                          │
│  • Cache dependencies for speed                                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┬──────────────────┐
          ▼                               ▼                  ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ STAGE 2:             │  │ STAGE 3:             │  │ STAGE 4:             │
│ CODE QUALITY         │  │ SECURITY SCANNING    │  │ UNIT TESTS           │
│ • Black formatting   │  │ • Bandit SAST        │  │ • 159 tests          │
│ • isort imports      │  │ • Safety deps        │  │ • Coverage >80%      │
│ • flake8 linting     │  │ • Vulnerability scan │  │ • Multi-version      │
│ • mypy type check    │  │                      │  │                      │
└──────────┬───────────┘  └──────────┬───────────┘  └──────────┬───────────┘
           │                         │                         │
           └─────────────────────────┴─────────────────────────┘
                                     │
                                     ▼
                     ┌──────────────────────────────┐
                     │ STAGE 5:                     │
                     │ INTEGRATION TESTS            │
                     │ • End-to-end workflows       │
                     │ • Tool integration tests     │
                     │ • Health checks              │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │ STAGE 6:                     │
                     │ PACKAGE ARTIFACTS            │
                     │ • Build wheel & sdist        │
                     │ • Version with commit hash   │
                     │ • Generate build manifest    │
                     └──────────────┬───────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼ (develop)                     ▼ (main)
        ┌──────────────────────┐      ┌──────────────────────────┐
        │ STAGE 7:             │      │ STAGE 8:                 │
        │ STAGING DEPLOYMENT   │      │ PRODUCTION DEPLOYMENT    │
        │ • Auto on develop    │      │ • Manual approval        │
        │ • Create pre-release │      │ • Create release         │
        │ • Notify team        │      │ • Post-deploy checks     │
        └──────────────────────┘      └──────────────────────────┘
```

### Parallel Execution

Jobs run in parallel where possible to minimize build time:

- **Build** runs first (required by all)
- **Code Quality**, **Security**, **Unit Tests** run in parallel after Build
- **Integration Tests** waits for Unit Tests + Code Quality
- **Package** waits for all quality gates to pass
- **Deployment** runs after Package (branch-specific)

**Target Pipeline Time**: <10 minutes end-to-end

---

## Branch Strategy

### Branch Model

This repository follows a **Git Flow** inspired branching strategy:

```
main (production)
  │
  ├─→ develop (staging)
  │     │
  │     ├─→ feature/user-authentication
  │     ├─→ feature/new-api-endpoint
  │     └─→ feature/performance-improvements
  │
  └─→ hotfix/critical-bug-fix
```

### Branch Policies

| Branch Pattern | Purpose                 | Pipeline Behavior               | Deployment                   |
| -------------- | ----------------------- | ------------------------------- | ---------------------------- |
| `main`         | Production-ready code   | Full pipeline + manual approval | → Production (with approval) |
| `develop`      | Integration/staging     | Full pipeline                   | → Staging (automatic)        |
| `feature/*`    | Feature development     | Build + Tests only              | None                         |
| `hotfix/*`     | Emergency fixes         | Full pipeline                   | → Production (expedited)     |
| `claude/*`     | Claude Code development | Full pipeline                   | None                         |

### Merge Requirements

**To `develop`:**

- ✅ All tests pass
- ✅ Code quality checks pass
- ✅ Security scans pass
- ✅ 1 peer review (recommended)

**To `main`:**

- ✅ All tests pass
- ✅ Code quality checks pass
- ✅ Security scans pass
- ✅ Merged from `develop` only
- ✅ 2 peer reviews (recommended)
- ✅ Manual deployment approval

---

## Pipeline Stages

### Stage 1: Build & Setup (5 min timeout)

**Purpose**: Install dependencies and build the package

**Steps**:

1. Checkout code with full git history
2. Set up Python 3.11 with pip caching
3. Install production dependencies from `requirements.txt`
4. Install development/testing dependencies
5. Build Python wheel and source distribution
6. Upload build artifacts (30-day retention)

**Outputs**:

- Built packages (`.whl`, `.tar.gz`)
- Cached dependencies for subsequent jobs

**Fail Conditions**:

- Dependency installation fails
- Package build fails
- Timeout exceeded

---

### Stage 2: Code Quality (5 min timeout)

**Purpose**: Enforce code quality standards

**Tools & Checks**:

| Tool       | Purpose         | Failure Behavior    |
| ---------- | --------------- | ------------------- |
| **black**  | Code formatting | ❌ Blocks pipeline  |
| **isort**  | Import sorting  | ❌ Blocks pipeline  |
| **flake8** | Linting (PEP 8) | ❌ Blocks on errors |
| **mypy**   | Type checking   | ⚠️ Warning only     |

**Configuration Files**:

- `.flake8` - Linting rules
- `pyproject.toml` - black, isort, mypy config

**Auto-Fix Commands**:

```bash
# Fix formatting issues
black short_term_mcp/
isort short_term_mcp/

# Verify
flake8 short_term_mcp/
mypy short_term_mcp/
```

**Artifacts**:

- `code-quality-report.txt` - Summary of checks

---

### Stage 3: Security Scanning (5 min timeout)

**Purpose**: Identify security vulnerabilities

**Scans Performed**:

1. **Bandit (SAST - Static Application Security Testing)**
   - Scans Python code for common security issues
   - Checks for: SQL injection, command injection, weak crypto, etc.
   - Output: `bandit-report.json`
   - Severity threshold: Medium/High failures block pipeline

2. **Safety (Dependency Vulnerability Scanning)**
   - Checks `requirements.txt` against vulnerability database
   - Identifies known CVEs in dependencies
   - Output: `safety-report.json`
   - Currently: Warning only (configurable to block)

**Configuration**:

```toml
# pyproject.toml
[tool.bandit]
exclude_dirs = ["tests", ".venv", "data", "logs"]
skips = ["B101"]  # Skip assert_used in tests
```

**Artifacts**:

- `bandit-report.json` (90-day retention)
- `safety-report.json` (90-day retention)

---

### Stage 4: Unit Tests (10 min timeout)

**Purpose**: Validate code correctness and coverage

**Test Execution**:

- **Framework**: pytest with pytest-asyncio
- **Test Count**: 159 tests across 7 phases
- **Coverage Target**: >80%
- **Python Versions**: 3.11, 3.12 (matrix)
- **Parallelization**: `pytest-xdist` for speed

**Test Organization**:

```
short_term_mcp/tests/
├── test_setup.py          # Phase 0: Setup (3 tests)
├── test_database.py       # Phase 1: Database (24 tests)
├── test_tools.py          # Phase 2: Core Tools (24 tests)
├── test_integration.py    # Phase 3: Integration (19 tests)
├── test_reliability_tools.py  # Phase 4: Reliability (17 tests)
├── test_code_teacher.py   # Phase 5: Code Teacher (20 tests)
├── test_future_features.py    # Phase 6: Knowledge Graph (25 tests)
└── test_production.py     # Phase 7: Production (27 tests)
```

**Coverage Reports**:

- Terminal output (summary)
- XML format (for CI integration)
- HTML format (browsable)

**Artifacts**:

- `test-results.xml` - JUnit format
- `htmlcov/` - Coverage HTML report
- `.coverage` - Raw coverage data

**Optional**: Upload to Codecov for tracking over time

---

### Stage 5: Integration Tests (10 min timeout)

**Purpose**: Test end-to-end workflows and component integration

**Tests**:

- Full pipeline workflows (Research → Storage)
- MCP tool integration
- Database operations (SQLite)
- Caching mechanisms
- Health check systems

**Specific Test Files**:

- `test_integration.py` - Core integration tests
- `test_research_cache_integration.py` - Cache integration
- `test_production.py` - Production health checks

**Dependencies**:

- Requires Unit Tests to pass
- Requires Code Quality to pass

---

### Stage 6: Package Artifacts (5 min timeout)

**Purpose**: Build versioned, deployable packages

**Versioning Strategy**:

```
Base Version: 1.1.1 (from pyproject.toml)
Build Version: 1.1.1+abc1234 (version + commit hash)
Artifact Name: short-term-mcp-1.1.1+abc1234
```

**Build Outputs**:

1. **Wheel**: `short_term_mcp-1.1.1+abc1234-py3-none-any.whl`
2. **Source Distribution**: `short-term-mcp-1.1.1+abc1234.tar.gz`
3. **Build Manifest**: `BUILD_MANIFEST.txt`

**Build Manifest Contents**:

```
Version: 1.1.1+abc1234
Commit: abc1234567890abcdef1234567890abcdef12345
Branch: main
Build Date: 2025-11-12 07:35:00 UTC
Workflow: CI/CD Pipeline
Run Number: 42
Triggered By: username

Packages:
short_term_mcp-1.1.1+abc1234-py3-none-any.whl
short-term-mcp-1.1.1+abc1234.tar.gz

Git Info:
Commit: abc1234567890abcdef1234567890abcdef12345
Author: John Doe <john@example.com>
Date: 2025-11-12 07:30:00
Message: feat: add new caching mechanism
```

**Verification**:

- Package integrity checked with `twine check`
- All packages validated before upload

**Artifacts**:

- All build outputs (90-day retention)

---

### Stage 7: Staging Deployment (5 min timeout)

**Trigger**: Automatic on push to `develop` branch

**Actions**:

1. Download packaged artifacts
2. Create GitHub pre-release
3. Tag: `staging-<version>`
4. Upload all artifacts to release
5. Mark as pre-release

**Release Notes** (Auto-generated):

- Version and commit information
- Changes in this deployment
- Test results summary
- ⚠️ Pre-release warning

**Environment**: `staging`

**Use Case**: Testing in staging environment before production

---

### Stage 8: Production Deployment (10 min timeout)

**Trigger**: Automatic on push to `main` branch + **MANUAL APPROVAL**

**Approval Gate**:

- GitHub Environment protection rules
- Requires approval from designated approvers
- Configurable wait time before auto-reject

**Actions**:

1. Wait for manual approval
2. Download packaged artifacts
3. Extract changelog for this version
4. Create GitHub release (not pre-release)
5. Tag: `v<version>`
6. Upload all artifacts
7. Mark as latest release
8. Run post-deployment smoke test

**Release Notes** (Auto-generated):

- Version and release date
- Changelog entries
- Quality metrics (tests passed, coverage, etc.)
- Installation instructions
- Deployment checklist
- Rollback instructions
- Support links

**Post-Deployment**:

- Smoke test (verify package imports correctly)
- Status summary with next steps

**Environment**: `production`

---

## Setup & Configuration

### Initial Setup

#### 1. Repository Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/short-term-memory-mcp.git
cd short-term-memory-mcp

# Verify pipeline files exist
ls -la .github/workflows/
# Should see: ci-cd.yml, pr-checks.yml
```

#### 2. GitHub Settings

**a) Enable GitHub Actions**

1. Go to: `Settings` → `Actions` → `General`
2. Set **Actions permissions**: "Allow all actions and reusable workflows"
3. Set **Workflow permissions**: "Read and write permissions"
4. Check: "Allow GitHub Actions to create and approve pull requests"

**b) Configure Environments**

Navigate to: `Settings` → `Environments`

**Staging Environment**:

```
Name: staging
Deployment branches: develop only
Required reviewers: None (automatic)
Environment secrets: (none required for this project)
```

**Production Environment**:

```
Name: production
Deployment branches: main only
Required reviewers: 2+ reviewers (configure your team)
Wait timer: 0 minutes (or set a delay)
Environment secrets: (none required for this project)
```

**c) Branch Protection Rules**

Navigate to: `Settings` → `Branches` → `Add rule`

**For `main` branch**:

```
Branch name pattern: main

Protect matching branches:
☑ Require a pull request before merging
  ☑ Require approvals (2 recommended)
☑ Require status checks to pass before merging
  ☑ Require branches to be up to date before merging
  Status checks:
    - 🔨 Build & Setup
    - 🔍 Code Quality
    - 🔒 Security Scan
    - 🧪 Unit Tests
    - 🔗 Integration Tests
    - 📦 Package Artifacts
☑ Require conversation resolution before merging
☑ Do not allow bypassing the above settings
```

**For `develop` branch**:

```
Branch name pattern: develop

Protect matching branches:
☑ Require a pull request before merging
  ☑ Require approvals (1 recommended)
☑ Require status checks to pass before merging
  Status checks:
    - 🔨 Build & Setup
    - 🔍 Code Quality
    - 🧪 Unit Tests
```

#### 3. Local Development Setup

```bash
# Set up Python environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install pytest pytest-asyncio pytest-cov
pip install flake8 black isort mypy bandit safety

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install
```

#### 4. Verify Setup

```bash
# Run tests locally
pytest short_term_mcp/tests/ -v

# Run code quality checks
black --check short_term_mcp/
isort --check-only short_term_mcp/
flake8 short_term_mcp/
mypy short_term_mcp/

# Run security scans
bandit -r short_term_mcp/ -ll
safety check
```

---

## Environment Management

### Environment Variables

Pipeline environment variables are defined in `.github/workflows/ci-cd.yml`:

```yaml
env:
  PYTHON_VERSION: '3.11' # Python version to use
  CACHE_KEY_PREFIX: 'short-term-mcp' # Cache key prefix
  MIN_COVERAGE_PERCENT: 80 # Minimum test coverage
  MAX_BUILD_TIME_MINUTES: 10 # Maximum build time
  ARTIFACT_RETENTION_DAYS: 30 # Artifact retention period
```

### Customizing Environment Variables

To change these values for your repository:

1. Edit `.github/workflows/ci-cd.yml`
2. Modify the `env:` section at the top
3. Commit and push changes

**Example**: Increase coverage requirement to 90%:

```yaml
env:
  MIN_COVERAGE_PERCENT: 90
```

### GitHub Environments

Two environments are configured:

**1. Staging** (`staging`)

- Auto-deploys from `develop` branch
- No approval required
- For testing and validation

**2. Production** (`production`)

- Deploys from `main` branch
- **Manual approval required**
- For production releases

### Environment-Specific Configuration

Currently, this MCP server doesn't require environment-specific configuration (it runs locally). For repositories that deploy to servers, you would configure:

- Deployment targets (URLs, servers)
- Service accounts
- Database connection strings
- API keys

---

## Secrets & Security

### Required Secrets

This repository uses **only built-in GitHub secrets**:

| Secret         | Purpose           | Auto-provided |
| -------------- | ----------------- | ------------- |
| `GITHUB_TOKEN` | GitHub API access | ✅ Yes        |

No additional secrets are required because:

- No external deployment targets
- No third-party service integrations
- No API keys needed
- Local-only MCP server

### Optional Secrets (for Enhanced Features)

If you want to add optional integrations:

**Codecov** (code coverage tracking):

```bash
# Add in: Settings → Secrets → Actions
Name: CODECOV_TOKEN
Value: <your-codecov-token>
```

**Slack Notifications**:

```bash
Name: SLACK_WEBHOOK_URL
Value: <your-slack-webhook>
```

### Adding Secrets

1. Go to: `Settings` → `Secrets and variables` → `Actions`
2. Click: `New repository secret`
3. Enter name and value
4. Click: `Add secret`

### Using Secrets in Workflows

```yaml
- name: Example step using secret
  env:
    API_KEY: ${{ secrets.MY_SECRET }}
  run: |
    echo "Using secret (not printed)"
```

### Security Best Practices

1. **Never commit secrets** to the repository
2. **Rotate secrets** regularly
3. **Use environment-specific secrets** when needed
4. **Limit secret access** to necessary workflows only
5. **Audit secret usage** periodically

---

## Triggering the Pipeline

### Automatic Triggers

The pipeline automatically runs on:

```yaml
on:
  push:
    branches:
      - main # Production deployment
      - develop # Staging deployment
      - 'feature/**' # Feature development (tests only)
      - 'hotfix/**' # Hotfix branches
      - 'claude/**' # Claude Code branches

  pull_request:
    branches:
      - main
      - develop
```

### Manual Trigger

You can manually trigger the pipeline:

1. Go to: `Actions` tab
2. Select: `CI/CD Pipeline`
3. Click: `Run workflow`
4. Choose branch
5. Optionally set: `skip_tests: true` (for testing pipeline only)
6. Click: `Run workflow`

### Trigger Scenarios

| Scenario                  | Pipeline Runs    | Deployment                   |
| ------------------------- | ---------------- | ---------------------------- |
| Push to `main`            | ✅ Full pipeline | → Production (with approval) |
| Push to `develop`         | ✅ Full pipeline | → Staging (automatic)        |
| Push to `feature/*`       | ✅ Tests only    | None                         |
| Pull request to `main`    | ✅ Full pipeline | None                         |
| Pull request to `develop` | ✅ Tests only    | None                         |
| Manual trigger            | ✅ Full pipeline | Based on branch              |

---

## Monitoring & Observability

### Real-Time Monitoring

**GitHub Actions UI**:

1. Navigate to: `Actions` tab
2. View: Running/completed workflows
3. Click: Workflow run for details
4. Expand: Each job to see logs

**Pipeline Summary**:

- Automatically generated at end of each run
- Shows job status in table format
- Overall success/failure status

### Artifacts & Reports

All pipeline runs generate downloadable artifacts:

| Artifact                   | Content                  | Retention |
| -------------------------- | ------------------------ | --------- |
| `dist-packages`            | Built Python packages    | 30 days   |
| `code-quality-report`      | Code quality summary     | 30 days   |
| `security-reports`         | Bandit + Safety results  | 90 days   |
| `test-results-py3.11`      | Test results + coverage  | 30 days   |
| `test-results-py3.12`      | Test results + coverage  | 30 days   |
| `integration-test-results` | Integration test results | 30 days   |
| `<version>`                | Final release artifacts  | 90 days   |

**Downloading Artifacts**:

1. Go to: Workflow run page
2. Scroll to: "Artifacts" section
3. Click: Artifact name to download

### Viewing Test Results

**Option 1: GitHub UI**

- Test results displayed in "Checks" tab of PRs
- Summary shows passed/failed counts

**Option 2: Download HTML Coverage Report**

```bash
# Download artifact from workflow run
unzip test-results-py3.11.zip
open htmlcov/index.html  # View in browser
```

### Monitoring Metrics

**Key metrics to track**:

- ⏱️ Pipeline execution time (target: <10 min)
- ✅ Test pass rate (target: 100%)
- 📊 Code coverage (target: >80%)
- 🔒 Security issues found (target: 0 critical/high)
- 📦 Build success rate (target: >95%)

### Notifications

**Built-in GitHub Notifications**:

- Email on workflow failure (configurable in GitHub settings)
- Browser notifications (if enabled)

**Custom Notifications** (optional):
Add Slack/Discord webhook steps to workflow:

```yaml
- name: Notify Slack on failure
  if: failure()
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
      -H 'Content-Type: application/json' \
      -d '{"text":"Pipeline failed: ${{ github.workflow }}"}'
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Pipeline Fails on Code Formatting

**Symptoms**:

```
❌ Code formatting issues found. Run 'black short_term_mcp/' to fix.
```

**Solution**:

```bash
# Fix automatically
black short_term_mcp/
isort short_term_mcp/

# Commit fixes
git add .
git commit -m "style: fix code formatting"
git push
```

---

#### Issue 2: Tests Fail Locally But Pass in CI (or vice versa)

**Symptoms**:

- Different test results between local and CI

**Causes**:

- Different Python versions
- Missing dependencies
- Environment-specific issues

**Solution**:

```bash
# Match CI environment exactly
python3.11 -m venv .venv
source .venv/bin/activate

# Clean install
pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov

# Run tests exactly as CI does
pytest short_term_mcp/tests/ -v --cov=short_term_mcp --cov-report=term-missing
```

---

#### Issue 3: Coverage Below Threshold

**Symptoms**:

```
❌ Coverage failed: 75% is less than 80%
```

**Solution**:

1. **Identify uncovered code**:

```bash
pytest short_term_mcp/tests/ --cov=short_term_mcp --cov-report=html
open htmlcov/index.html  # View coverage report
```

2. **Add missing tests** for uncovered lines

3. **Or adjust threshold** (if acceptable):

```yaml
# .github/workflows/ci-cd.yml
env:
  MIN_COVERAGE_PERCENT: 75 # Lower threshold
```

---

#### Issue 4: Security Scan Failures

**Symptoms**:

```
❌ Bandit found high severity issues
```

**Solution**:

1. **Review security report**:

```bash
# Download bandit-report.json from artifacts
cat bandit-report.json | jq '.results'
```

2. **Fix security issues** in code

3. **Or suppress false positives**:

```python
# In code, if issue is false positive
def example():
    value = input("Enter value: ")  # nosec B101
```

---

#### Issue 5: Deployment Fails (Manual Approval Not Granted)

**Symptoms**:

- Production deployment step waiting indefinitely

**Solution**:

1. **Grant approval**:
   - Go to: Workflow run page
   - Click: "Review deployments"
   - Select: `production` environment
   - Click: "Approve and deploy"

2. **Or cancel**:
   - Click: "Reject"
   - Re-run workflow when ready

---

#### Issue 6: Cache Issues

**Symptoms**:

- Slow builds despite caching
- "Cache not found" warnings

**Solution**:

1. **Clear cache** (GitHub Actions UI):
   - Go to: `Settings` → `Actions` → `Caches`
   - Delete old caches

2. **Or update cache key**:

```yaml
# .github/workflows/ci-cd.yml
env:
  CACHE_KEY_PREFIX: 'short-term-mcp-v2' # Increment version
```

---

### Getting Help

**Check workflow logs**:

1. Go to: `Actions` tab
2. Click: Failed workflow run
3. Click: Failed job
4. Expand: Failed step
5. Review: Error messages and stack traces

**Debug with workflow dispatch**:

```yaml
# Manually trigger with debugging
workflow_dispatch:
  inputs:
    debug_enabled:
      description: 'Enable debug mode'
      required: false
      default: 'false'
```

**Common log locations**:

- Build errors: "Build & Setup" job
- Test failures: "Unit Tests" job
- Security issues: "Security Scan" job
- Deployment issues: "Deploy to Production" job

---

## Onboarding Checklist

Use this checklist when onboarding a new repository or team member:

### For Repository Administrators

- [ ] **GitHub Actions enabled** (`Settings` → `Actions`)
- [ ] **Workflow permissions set** (Read and write)
- [ ] **Staging environment configured** (automatic deployment)
- [ ] **Production environment configured** (manual approval, 2+ reviewers)
- [ ] **Branch protection rules** applied to `main`
- [ ] **Branch protection rules** applied to `develop`
- [ ] **Required status checks** configured
- [ ] **Team approvers** designated for production deployments
- [ ] **Secrets configured** (if any external services)
- [ ] **First pipeline run** successful

### For Developers

- [ ] **Repository cloned** locally
- [ ] **Python 3.11+** installed
- [ ] **Virtual environment** created (`.venv`)
- [ ] **Dependencies installed** (`pip install -r requirements.txt`)
- [ ] **Development tools installed** (pytest, black, flake8, etc.)
- [ ] **Pre-commit hooks** installed (optional)
- [ ] **Local tests pass** (`pytest short_term_mcp/tests/ -v`)
- [ ] **Code formatting verified** (`black --check short_term_mcp/`)
- [ ] **Branch strategy** understood
- [ ] **Pipeline documentation** reviewed

### For Operations/DevOps

- [ ] **Pipeline stages** understood
- [ ] **Deployment process** documented
- [ ] **Rollback procedure** tested
- [ ] **Monitoring configured** (if applicable)
- [ ] **Notification channels** set up (Slack, email, etc.)
- [ ] **Artifact retention** configured
- [ ] **Backup strategy** defined
- [ ] **Incident response** plan documented

### For Managers/Stakeholders

- [ ] **Pipeline overview** understood
- [ ] **Deployment frequency** aligned with business needs
- [ ] **Quality gates** approved
- [ ] **Approval process** clear
- [ ] **Risk mitigation** strategies in place

---

## Customization Guide

### Adjusting Pipeline for Different Repositories

This pipeline is designed to be **template-ready**. Customize for other repositories:

#### 1. Change Python Version

```yaml
# .github/workflows/ci-cd.yml
env:
  PYTHON_VERSION: '3.12' # Change version
```

#### 2. Add/Remove Test Frameworks

```yaml
# Example: Add tox for multi-environment testing
- name: Install tox
  run: pip install tox

- name: Run tox
  run: tox
```

#### 3. Change Deployment Targets

For repositories that deploy to actual servers:

```yaml
deploy-production:
  steps:
    - name: Deploy to AWS
      run: |
        aws s3 sync dist/ s3://my-bucket/
        aws cloudfront create-invalidation --distribution-id XYZ
```

#### 4. Add Docker Support

```yaml
- name: Build Docker image
  run: |
    docker build -t my-app:${{ github.sha }} .
    docker push my-app:${{ github.sha }}
```

#### 5. Integrate Additional Services

**SonarQube** (code quality):

```yaml
- name: SonarQube scan
  uses: sonarsource/sonarqube-scan-action@v2
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

**Snyk** (security):

```yaml
- name: Snyk scan
  uses: snyk/actions/python-3.8@master
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

#### 6. Customize Branch Strategy

```yaml
on:
  push:
    branches:
      - main
      - staging # Add staging branch
      - 'release/*' # Add release branches
```

#### 7. Adjust Timeouts

```yaml
jobs:
  unit-tests:
    timeout-minutes: 20 # Increase for slow tests
```

#### 8. Multi-OS Testing

```yaml
unit-tests:
  strategy:
    matrix:
      os: [ubuntu-latest, macos-latest, windows-latest]
      python-version: ['3.11', '3.12']
  runs-on: ${{ matrix.os }}
```

---

## Rollback Procedures

### Scenario 1: Rollback Production Deployment

**When**: New release causes issues in production

**Steps**:

1. **Identify previous working version**:

```bash
# View releases
gh release list

# Example output:
v1.1.1+abc1234  Latest    2025-11-12
v1.1.0+def5678  Previous  2025-11-10
```

2. **Download previous version artifacts**:

```bash
# Download previous release
gh release download v1.1.0+def5678

# Or via GitHub UI: Releases → Select version → Download assets
```

3. **Install previous version**:

```bash
# Uninstall current version
pip uninstall short-term-mcp

# Install previous version
pip install short_term_mcp-1.1.0+def5678-py3-none-any.whl
```

4. **Verify rollback**:

```bash
# Check version
python -c "from short_term_mcp import __version__; print(__version__)"

# Run health check
# (Use MCP tool: health_check)
```

5. **Update documentation**:

- Update README.md with rollback notice
- Notify team of rollback
- Create incident report

**Time to Rollback**: ~5 minutes

---

### Scenario 2: Rollback via Git Revert

**When**: Need to remove problematic commit from `main`

**Steps**:

1. **Identify problematic commit**:

```bash
git log --oneline main
# Find commit hash, e.g., abc1234
```

2. **Revert commit**:

```bash
git revert abc1234
git push origin main
```

3. **Pipeline re-runs automatically**:

- Tests run on reverted code
- If successful, new release created

---

### Scenario 3: Emergency Hotfix

**When**: Critical bug needs immediate fix

**Steps**:

1. **Create hotfix branch from main**:

```bash
git checkout main
git pull
git checkout -b hotfix/critical-bug-fix
```

2. **Make fix and test**:

```bash
# Make changes
vim short_term_mcp/module.py

# Test locally
pytest short_term_mcp/tests/ -v

# Commit
git add .
git commit -m "hotfix: critical bug fix"
git push origin hotfix/critical-bug-fix
```

3. **Create PR to main** (skip develop):

```bash
gh pr create --base main --head hotfix/critical-bug-fix \
  --title "HOTFIX: Critical bug fix" \
  --body "Emergency fix for production issue"
```

4. **Fast-track approval**:

- Get required approvals
- Merge to main
- Pipeline runs automatically
- Approve production deployment immediately

5. **Backport to develop**:

```bash
git checkout develop
git cherry-pick <hotfix-commit-hash>
git push origin develop
```

**Time to Deploy Hotfix**: ~15-30 minutes (depending on approvals)

---

## Best Practices

### Development Best Practices

1. **Always work on feature branches**

   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Run tests locally before pushing**

   ```bash
   pytest short_term_mcp/tests/ -v
   ```

3. **Fix formatting before committing**

   ```bash
   black short_term_mcp/
   isort short_term_mcp/
   ```

4. **Keep commits atomic and meaningful**

   ```bash
   git commit -m "feat: add user authentication"
   git commit -m "fix: resolve caching issue"
   git commit -m "docs: update API documentation"
   ```

5. **Use conventional commit messages**
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `style:` - Formatting changes
   - `refactor:` - Code refactoring
   - `test:` - Adding/updating tests
   - `chore:` - Maintenance tasks

### Pipeline Best Practices

1. **Monitor pipeline health**
   - Track pipeline success rate
   - Investigate recurring failures
   - Optimize slow jobs

2. **Keep pipeline fast**
   - Target: <10 minutes end-to-end
   - Use caching effectively
   - Parallelize independent jobs

3. **Fail fast**
   - Run critical checks first
   - Don't wait for slow jobs if fast ones fail

4. **Version everything**
   - Artifacts tagged with commit hash
   - Releases use semantic versioning
   - Build manifests include full context

5. **Secure secrets properly**
   - Never commit secrets
   - Use GitHub Secrets for sensitive data
   - Rotate secrets regularly

### Deployment Best Practices

1. **Test in staging first**
   - Always deploy to staging before production
   - Validate in staging environment
   - Get sign-off before production

2. **Deploy during low-traffic periods**
   - Schedule production deployments
   - Have rollback plan ready
   - Monitor post-deployment

3. **Communicate deployments**
   - Notify team before deploying
   - Share release notes
   - Document any manual steps

4. **Monitor after deployment**
   - Watch error logs
   - Check health metrics
   - Verify functionality

5. **Keep deployment history**
   - Don't delete old releases immediately
   - Keep artifacts for rollback
   - Document deployment issues

### Code Quality Best Practices

1. **Maintain high test coverage** (>80%)
2. **Fix linting errors immediately**
3. **Address security warnings promptly**
4. **Keep dependencies up to date**
5. **Document complex code**

---

## Conclusion

This CI/CD pipeline provides:

✅ **Automated quality gates** - Code quality, security, and testing enforced automatically
✅ **Fast feedback** - Parallel execution and fail-fast approach minimize wait time
✅ **Safe deployments** - Multi-stage pipeline with approval gates
✅ **Easy rollback** - Versioned artifacts and clear rollback procedures
✅ **Observable** - Comprehensive logging and reporting
✅ **Maintainable** - Well-documented and customizable

### Next Steps

1. ✅ Complete [Onboarding Checklist](#onboarding-checklist)
2. 🧪 Test pipeline with a sample PR
3. 📚 Review [Pipeline Stages](#pipeline-stages) in detail
4. 🚀 Deploy to staging
5. 🎯 Deploy to production (with approval)
6. 📊 Monitor and optimize

### Support & Resources

- **Pipeline Workflow**: `.github/workflows/ci-cd.yml`
- **PR Checks**: `.github/workflows/pr-checks.yml`
- **Code Quality Config**: `pyproject.toml`, `.flake8`
- **This Documentation**: `docs/CI-CD-PIPELINE.md`

For questions or issues, refer to the [Troubleshooting](#troubleshooting) section or contact the DevOps team.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Pipeline Version**: v1.0 (ci-cd.yml)
**Status**: ✅ Production Ready
