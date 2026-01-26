/**
 * Knowledge Library E2E Test
 *
 * Verifies the Knowledge Library UI components:
 * - Navigation from Knowledge Hub
 * - Tab navigation (Input/Library/Query)
 * - Connection status indicator
 * - Basic component rendering
 */

import { test, expect } from '@playwright/test';
import {
  authenticateForTests,
  getFixturePath,
  handleLoginScreenIfPresent,
  setupProjectWithFixture,
} from '../utils';

test.describe('Knowledge Library', () => {
  test.beforeEach(async ({ page }) => {
    test.setTimeout(60_000);
    await setupProjectWithFixture(page, getFixturePath());
    await authenticateForTests(page);
  });

  test('appears in Knowledge Hub and can be navigated to', async ({ page }) => {
    // Navigate to Knowledge Hub
    await page.goto('/knowledge-hub');
    await page.waitForLoadState('load');
    await handleLoginScreenIfPresent(page);

    // Verify Knowledge Library card is visible
    await expect(page.getByText('Knowledge Library').first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Extract, organize, and query')).toBeVisible({ timeout: 5000 });

    // Click on Knowledge Library card
    await page.getByText('Knowledge Library').first().click();
    await page.waitForURL('**/knowledge-hub/knowledge-library');

    // Verify we're on the Knowledge Library page
    await expect(page.locator('h1').getByText('Knowledge Library')).toBeVisible({ timeout: 10000 });
  });

  test('displays connection status indicator', async ({ page }) => {
    await page.goto('/knowledge-hub/knowledge-library');
    await page.waitForLoadState('load');
    await handleLoginScreenIfPresent(page);

    // Connection status should be visible (either connected or offline)
    const connectionStatus = page.getByTestId('kl-connection-status');
    await expect(connectionStatus).toBeVisible({ timeout: 10000 });
  });

  test('has three tabs: Input, Library, Query', async ({ page }) => {
    await page.goto('/knowledge-hub/knowledge-library');
    await page.waitForLoadState('load');
    await handleLoginScreenIfPresent(page);

    // Verify all three tabs exist
    await expect(page.getByRole('tab', { name: /Input/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('tab', { name: /Library/i })).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('tab', { name: /Query/i })).toBeVisible({ timeout: 5000 });
  });

  test('can switch between tabs', async ({ page }) => {
    await page.goto('/knowledge-hub/knowledge-library');
    await page.waitForLoadState('load');
    await handleLoginScreenIfPresent(page);

    // Default tab should be Input
    const inputTab = page.getByRole('tab', { name: /Input/i });
    await expect(inputTab).toHaveAttribute('data-state', 'active', { timeout: 10000 });

    // Click Library tab
    const libraryTab = page.getByRole('tab', { name: /Library/i });
    await libraryTab.click();
    await expect(libraryTab).toHaveAttribute('data-state', 'active', { timeout: 5000 });

    // Click Query tab
    const queryTab = page.getByRole('tab', { name: /Query/i });
    await queryTab.click();
    await expect(queryTab).toHaveAttribute('data-state', 'active', { timeout: 5000 });

    // Go back to Input tab
    await inputTab.click();
    await expect(inputTab).toHaveAttribute('data-state', 'active', { timeout: 5000 });
  });

  test('Input tab shows upload area when no session active', async ({ page }) => {
    await page.goto('/knowledge-hub/knowledge-library');
    await page.waitForLoadState('load');
    await handleLoginScreenIfPresent(page);

    // Should see upload-related content or empty state
    const uploadButton = page.getByRole('button', { name: /Start Session/i });
    const uploadText = page.getByText(/Upload/i);

    // At least one of these should be visible
    const uploadVisible = await uploadButton.isVisible().catch(() => false);
    const textVisible = await uploadText
      .first()
      .isVisible()
      .catch(() => false);

    expect(uploadVisible || textVisible).toBe(true);
  });

  test('Query tab shows question input', async ({ page }) => {
    await page.goto('/knowledge-hub/knowledge-library');
    await page.waitForLoadState('load');
    await handleLoginScreenIfPresent(page);

    // Switch to Query tab
    await page.getByRole('tab', { name: /Query/i }).click();

    // Should see question input or empty state
    const questionInput = page.getByPlaceholder(/What would you like to know/i);
    const sendButton = page.getByRole('button').filter({ has: page.locator('svg') });

    await expect(questionInput).toBeVisible({ timeout: 10000 });
  });
});
