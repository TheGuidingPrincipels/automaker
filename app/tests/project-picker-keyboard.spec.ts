import { test, expect } from "@playwright/test";
import {
  setupMockMultipleProjects,
  waitForElement,
  isProjectPickerDropdownOpen,
  waitForProjectPickerDropdown,
  waitForProjectPickerDropdownHidden,
  pressShortcut,
  pressNumberKey,
  isProjectHotkeyVisible,
  getProjectPickerShortcut,
} from "./utils";

test.describe("Project Picker Keyboard Shortcuts", () => {
  test("pressing P key opens the project picker dropdown", async ({ page }) => {
    // Setup with multiple projects
    await setupMockMultipleProjects(page, 3);
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Wait for sidebar to be visible
    await waitForElement(page, "sidebar");

    // Dropdown should initially be closed
    expect(await isProjectPickerDropdownOpen(page)).toBe(false);

    // Press P to open project picker
    await pressShortcut(page, "p");

    // Dropdown should now be open
    await waitForProjectPickerDropdown(page);
    expect(await isProjectPickerDropdownOpen(page)).toBe(true);
  });

  test("project options show hotkey indicators (1-5)", async ({ page }) => {
    // Setup with 5 projects
    await setupMockMultipleProjects(page, 5);
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Wait for sidebar
    await waitForElement(page, "sidebar");

    // Open project picker
    await pressShortcut(page, "p");
    await waitForProjectPickerDropdown(page);

    // Check that all 5 hotkey indicators are visible
    for (let i = 1; i <= 5; i++) {
      expect(await isProjectHotkeyVisible(page, i)).toBe(true);
      const hotkey = page.locator(`[data-testid="project-hotkey-${i}"]`);
      expect(await hotkey.textContent()).toBe(i.toString());
    }
  });

  test("pressing number key selects the corresponding project", async ({
    page,
  }) => {
    // Setup with 3 projects
    await setupMockMultipleProjects(page, 3);
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Wait for sidebar
    await waitForElement(page, "sidebar");

    // Check initial project (should be Test Project 1)
    const projectSelector = page.locator('[data-testid="project-selector"]');
    await expect(projectSelector).toContainText("Test Project 1");

    // Open project picker
    await pressShortcut(page, "p");
    await waitForProjectPickerDropdown(page);

    // Press 2 to select the second project
    await pressNumberKey(page, 2);

    // Dropdown should close
    await waitForProjectPickerDropdownHidden(page);

    // Project should now be Test Project 2
    await expect(projectSelector).toContainText("Test Project 2");
  });

  test("pressing number key for non-existent project does nothing", async ({
    page,
  }) => {
    // Setup with 2 projects
    await setupMockMultipleProjects(page, 2);
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Wait for sidebar
    await waitForElement(page, "sidebar");

    // Check initial project
    const projectSelector = page.locator('[data-testid="project-selector"]');
    await expect(projectSelector).toContainText("Test Project 1");

    // Open project picker
    await pressShortcut(page, "p");
    await waitForProjectPickerDropdown(page);

    // Press 5 (there's no 5th project)
    await pressNumberKey(page, 5);

    // Dropdown should remain open
    expect(await isProjectPickerDropdownOpen(page)).toBe(true);

    // Project should still be Test Project 1
    await expect(projectSelector).toContainText("Test Project 1");
  });

  test("pressing Escape closes the project picker dropdown", async ({
    page,
  }) => {
    // Setup with multiple projects
    await setupMockMultipleProjects(page, 3);
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Wait for sidebar
    await waitForElement(page, "sidebar");

    // Open project picker
    await pressShortcut(page, "p");
    await waitForProjectPickerDropdown(page);

    // Press Escape
    await page.keyboard.press("Escape");

    // Dropdown should close
    await waitForProjectPickerDropdownHidden(page);
    expect(await isProjectPickerDropdownOpen(page)).toBe(false);
  });

  test("project selector button shows P shortcut indicator", async ({
    page,
  }) => {
    // Setup with multiple projects
    await setupMockMultipleProjects(page, 3);
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Wait for sidebar and project selector
    await waitForElement(page, "sidebar");
    await waitForElement(page, "project-selector");

    // Check that P shortcut indicator is visible
    const shortcutIndicator = await getProjectPickerShortcut(page);
    await expect(shortcutIndicator).toBeVisible();
    await expect(shortcutIndicator).toHaveText("P");
  });

  test("only first 5 projects are shown with hotkeys", async ({ page }) => {
    // Setup with 7 projects
    await setupMockMultipleProjects(page, 7);
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Wait for sidebar
    await waitForElement(page, "sidebar");

    // Open project picker
    await pressShortcut(page, "p");
    await waitForProjectPickerDropdown(page);

    // Only 5 hotkey indicators should be visible (1-5)
    for (let i = 1; i <= 5; i++) {
      expect(await isProjectHotkeyVisible(page, i)).toBe(true);
    }

    // 6th and 7th should not exist
    const hotkey6 = page.locator('[data-testid="project-hotkey-6"]');
    const hotkey7 = page.locator('[data-testid="project-hotkey-7"]');
    await expect(hotkey6).not.toBeVisible();
    await expect(hotkey7).not.toBeVisible();
  });

  test("clicking a project option also works", async ({ page }) => {
    // Setup with 3 projects
    await setupMockMultipleProjects(page, 3);
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Wait for sidebar
    await waitForElement(page, "sidebar");

    // Open project picker by clicking
    await page.locator('[data-testid="project-selector"]').click();
    await waitForProjectPickerDropdown(page);

    // Click on second project option
    await page.locator('[data-testid="project-option-test-project-2"]').click();

    // Dropdown should close
    await waitForProjectPickerDropdownHidden(page);

    // Project should now be Test Project 2
    const projectSelector = page.locator('[data-testid="project-selector"]');
    await expect(projectSelector).toContainText("Test Project 2");
  });

  test("P shortcut does not work when no projects exist", async ({ page }) => {
    // Setup with empty projects
    await page.addInitScript(() => {
      const mockState = {
        state: {
          projects: [],
          currentProject: null,
          currentView: "welcome",
          theme: "dark",
          sidebarOpen: true,
          apiKeys: { anthropic: "", google: "" },
          chatSessions: [],
          chatHistoryOpen: false,
          maxConcurrency: 3,
        },
        version: 0,
      };
      localStorage.setItem("automaker-storage", JSON.stringify(mockState));
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Wait for sidebar
    await waitForElement(page, "sidebar");

    // Press P - should not open any dropdown since there are no projects
    await pressShortcut(page, "p");
    await page.waitForTimeout(300);

    // Dropdown should not be visible
    expect(await isProjectPickerDropdownOpen(page)).toBe(false);
  });
});
