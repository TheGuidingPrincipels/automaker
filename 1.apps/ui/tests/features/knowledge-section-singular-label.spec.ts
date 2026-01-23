/**
 * Knowledge Section Singular Label E2E Test
 *
 * Regression: CTA labels must not be derived by slicing section names.
 */

import { test, expect } from '@playwright/test';
import {
  authenticateForTests,
  getFixturePath,
  handleLoginScreenIfPresent,
  setupProjectWithFixture,
} from '../utils';

test.describe('Knowledge Section singular labels', () => {
  test('uses explicit singular labels in the header CTA', async ({ page }) => {
    test.setTimeout(60_000);

    await setupProjectWithFixture(page, getFixturePath());
    await authenticateForTests(page);

    const cases = [
      { section: 'blueprints', heading: 'Blueprints', cta: 'Add Blueprint' },
      { section: 'knowledge-server', heading: 'Knowledge Server', cta: 'Add Knowledge Entry' },
      { section: 'learning', heading: 'Learning', cta: 'Add Learning' },
    ] as const;

    for (const { section, heading, cta } of cases) {
      await test.step(`${section} header CTA`, async () => {
        await page.goto(`/knowledge-hub/${section}`);
        await page.waitForLoadState('load');
        await handleLoginScreenIfPresent(page);

        await expect(page.getByRole('heading', { name: heading })).toBeVisible({ timeout: 10000 });
        await expect(page.getByRole('button', { name: cta })).toBeVisible({ timeout: 10000 });
      });
    }
  });
});
