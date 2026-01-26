## Description

<!-- Provide a clear and concise description of your changes -->

## Type of Change

<!-- Mark the relevant option with an [x] -->

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🔧 Configuration change
- [ ] ♻️ Code refactoring
- [ ] 🧪 Test update

## Changes Made

<!-- List the specific changes made in this PR -->

-
-
-

## Testing

<!-- Describe the tests you ran and how to reproduce them -->

- [ ] All existing tests pass locally
- [ ] Added new tests for new functionality
- [ ] Manual testing completed

**Test Command**:

```bash
pytest short_term_mcp/tests/ -v
```

## Checklist

<!-- Verify you've completed these steps before submitting -->

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have updated the documentation (if applicable)
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Pre-Submission Checks

<!-- Run these commands locally before submitting -->

```bash
# Code formatting
black --check short_term_mcp/
isort --check-only short_term_mcp/

# Linting
flake8 short_term_mcp/

# Tests
pytest short_term_mcp/tests/ -v
```

**All checks passed?** ✅

## Related Issues

<!-- Link to related issues using: Closes #123, Fixes #456, Related to #789 -->

Closes #

## Screenshots (if applicable)

<!-- Add screenshots to help explain your changes -->

## Additional Context

<!-- Add any other context about the PR here -->

---

## For Reviewers

## **Focus Areas**:

- **Questions**:

-
- ***

  **CI/CD Pipeline**: The automated pipeline will run upon PR creation. Ensure all checks pass before requesting review.

- 🔨 Build & Setup
- 🔍 Code Quality
- 🔒 Security Scan
- 🧪 Unit Tests
- 🔗 Integration Tests

**Documentation**: [CI/CD Pipeline Guide](docs/CI-CD-PIPELINE.md)
