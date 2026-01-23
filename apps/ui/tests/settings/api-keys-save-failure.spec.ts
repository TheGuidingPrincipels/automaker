import { test, expect } from '@playwright/test';
import { authenticateForTests, waitForErrorToast } from '../utils';

test.describe('API key save failure handling', () => {
  test('does not mark saved when any provider fails to persist', async ({ page }) => {
    await page.route('**/api/setup/auth-mode', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          mode: 'api_key',
          status: {
            isAuthTokenMode: false,
            isApiKeyMode: true,
            apiKeyAllowed: true,
            envApiKeyCleared: false,
            hasEnvApiKey: false,
          },
        },
      });
    });

    await page.route('**/api/setup/openai-auth-mode', async (route) => {
      await route.fulfill({
        json: {
          success: true,
          mode: 'api_key',
          status: {
            isAuthTokenMode: false,
            isApiKeyMode: true,
            apiKeyAllowed: true,
            envApiKeyCleared: false,
            hasEnvApiKey: false,
          },
        },
      });
    });

    await page.route('**/api/setup/store-api-key', async (route) => {
      const payload = (await route.request().postDataJSON()) as {
        provider?: string;
      } | null;

      if (payload?.provider === 'openai') {
        await route.fulfill({
          status: 500,
          json: { success: false, error: 'Failed to save OpenAI key' },
        });
        return;
      }

      await route.fulfill({ json: { success: true } });
    });

    await authenticateForTests(page);
    await page.goto('/settings');
    await page.locator('[data-testid="settings-view"]').waitFor({ state: 'visible' });

    const authModeResponse = page.waitForResponse('**/api/setup/auth-mode');
    const openaiAuthModeResponse = page.waitForResponse('**/api/setup/openai-auth-mode');
    await page.getByRole('button', { name: 'API Keys' }).first().click();
    await Promise.all([authModeResponse, openaiAuthModeResponse]);

    await page.locator('[data-testid="anthropic-api-key-input"]').waitFor({ state: 'visible' });
    await page.locator('[data-testid="openai-api-key-input"]').waitFor({ state: 'visible' });

    await page.locator('[data-testid="anthropic-api-key-input"]').fill('sk-ant-test');
    await page.locator('[data-testid="openai-api-key-input"]').fill('sk-openai-test');

    await page.locator('[data-testid="save-settings"]').click();

    await waitForErrorToast(page, 'Some API keys failed to save');
    await expect(page.getByRole('button', { name: 'Saved!' })).not.toBeVisible({ timeout: 2000 });
  });
});
