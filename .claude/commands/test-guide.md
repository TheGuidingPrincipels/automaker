# Testing Guide

Complete guide for running and debugging tests in Automaker.

## Test Commands

| Command                 | Purpose                       | Framework  |
| ----------------------- | ----------------------------- | ---------- |
| `npm run test`          | E2E tests (headless)          | Playwright |
| `npm run test:headed`   | E2E tests (visible browser)   | Playwright |
| `npm run test:server`   | Server unit tests             | Vitest     |
| `npm run test:packages` | Shared package tests          | Vitest     |
| `npm run test:all`      | All tests (packages + server) | Both       |

## Running Specific Tests

### Single E2E Test File

```bash
npx playwright test tests/e2e/specific.spec.ts
```

### Single Unit Test File

```bash
npm run test:server -- tests/unit/specific.test.ts
```

### Tests Matching Pattern

```bash
# E2E
npx playwright test --grep "feature name"

# Unit
npm run test:server -- --grep "feature name"
```

## E2E vs Unit Tests

| Aspect       | E2E (Playwright)      | Unit (Vitest)                         |
| ------------ | --------------------- | ------------------------------------- |
| Location     | `tests/e2e/`          | `apps/server/tests/`, `libs/*/tests/` |
| Scope        | Full app flow         | Single function/module                |
| Speed        | Slow (~minutes)       | Fast (~seconds)                       |
| Dependencies | Real server + browser | Mocked                                |
| Parallelism  | Limited               | High                                  |

## Worktree Testing

Each worktree has its own port range. Tests automatically use `.env` configuration.

### From Main Repo

```bash
cd /Users/ruben/Documents/GitHub/automaker
npm run test  # Uses ports 3007/3008
```

### From Worktree

```bash
cd /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1
npm run test  # Uses ports 3017/3018
```

### Unit Tests (Safe in Parallel)

```bash
# These use mocks, no port conflicts
npm run test:server
npm run test:packages
```

### E2E Tests (One at a Time Per Worktree)

```bash
# Run from the worktree you want to test
cd .worktrees/feature-1 && npm run test
```

## Mock Agent Mode

For CI or testing without real API calls:

```bash
AUTOMAKER_MOCK_AGENT=true npm run test
```

This mode:

- Returns predefined responses
- Doesn't hit Claude API
- Runs faster
- Good for CI pipelines

## Debugging Failures

### E2E Test Failures

1. **Run headed mode** to see what's happening:

   ```bash
   npm run test:headed
   ```

2. **Check screenshots** in `test-results/` directory

3. **Add debug logging**:

   ```typescript
   await page.screenshot({ path: 'debug.png' });
   console.log(await page.content());
   ```

4. **Slow down execution**:
   ```typescript
   // In playwright.config.ts
   use: {
     launchOptions: {
       slowMo: 500;
     }
   }
   ```

### Unit Test Failures

1. **Run single test** with verbose output:

   ```bash
   npm run test:server -- tests/unit/failing.test.ts --reporter=verbose
   ```

2. **Add debug statements**:

   ```typescript
   console.log('State:', JSON.stringify(result, null, 2));
   ```

3. **Check mock setup** - ensure mocks match expected interface

### Common Issues

| Issue               | Solution                                               |
| ------------------- | ------------------------------------------------------ |
| Port already in use | Kill process: `lsof -i :3007` then `kill -9 <PID>`     |
| Test timeout        | Increase timeout in test or check for hanging promises |
| Mock not working    | Verify mock path matches actual import path            |
| Flaky tests         | Add explicit waits, avoid race conditions              |

## Test Structure

### E2E Test Example

```typescript
import { test, expect } from '@playwright/test';

test('feature workflow', async ({ page }) => {
  await page.goto('/');
  await page.click('button:has-text("Create")');
  await expect(page.locator('.feature-card')).toBeVisible();
});
```

### Unit Test Example

```typescript
import { describe, it, expect, vi } from 'vitest';
import { myFunction } from '../src/service';

describe('myFunction', () => {
  it('should return expected result', () => {
    const result = myFunction('input');
    expect(result).toBe('expected');
  });
});
```

## CI/CD Integration

```yaml
# Example GitHub Actions
- name: Run unit tests
  run: npm run test:all

- name: Run E2E tests
  run: AUTOMAKER_MOCK_AGENT=true npm run test
  env:
    CI: true
```

## Tips

1. **Always run unit tests first** - they're faster and catch most issues
2. **Use mock agent** in CI to avoid API costs and flakiness
3. **Keep tests isolated** - each test should clean up after itself
4. **Use meaningful assertions** - test behavior, not implementation
5. **Run tests before committing** - catch issues early
