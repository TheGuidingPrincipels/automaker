import { Page, Locator, expect } from "@playwright/test";

/**
 * Get an element by its data-testid attribute
 */
export async function getByTestId(
  page: Page,
  testId: string
): Promise<Locator> {
  return page.locator(`[data-testid="${testId}"]`);
}

/**
 * Set up a mock project in localStorage to bypass the welcome screen
 * This simulates having opened a project before
 */
export async function setupMockProject(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const mockProject = {
      id: "test-project-1",
      name: "Test Project",
      path: "/mock/test-project",
      lastOpened: new Date().toISOString(),
    };

    const mockState = {
      state: {
        projects: [mockProject],
        currentProject: mockProject,
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
}

/**
 * Click an element by its data-testid attribute
 */
export async function clickElement(page: Page, testId: string): Promise<void> {
  const element = await getByTestId(page, testId);
  await element.click();
}

/**
 * Wait for an element with a specific data-testid to appear
 */
export async function waitForElement(
  page: Page,
  testId: string,
  options?: { timeout?: number; state?: "attached" | "visible" | "hidden" }
): Promise<Locator> {
  const element = page.locator(`[data-testid="${testId}"]`);
  await element.waitFor({
    timeout: options?.timeout ?? 5000,
    state: options?.state ?? "visible",
  });
  return element;
}

/**
 * Wait for an element with a specific data-testid to be hidden
 */
export async function waitForElementHidden(
  page: Page,
  testId: string,
  options?: { timeout?: number }
): Promise<void> {
  const element = page.locator(`[data-testid="${testId}"]`);
  await element.waitFor({
    timeout: options?.timeout ?? 5000,
    state: "hidden",
  });
}

/**
 * Get a button by its text content
 */
export async function getButtonByText(
  page: Page,
  text: string
): Promise<Locator> {
  return page.locator(`button:has-text("${text}")`);
}

/**
 * Click a button by its text content
 */
export async function clickButtonByText(
  page: Page,
  text: string
): Promise<void> {
  const button = await getButtonByText(page, text);
  await button.click();
}

/**
 * Fill an input field by its data-testid attribute
 */
export async function fillInput(
  page: Page,
  testId: string,
  value: string
): Promise<void> {
  const input = await getByTestId(page, testId);
  await input.fill(value);
}

/**
 * Navigate to the board/kanban view
 */
export async function navigateToBoard(page: Page): Promise<void> {
  await page.goto("/");

  // Wait for the page to load
  await page.waitForLoadState("networkidle");

  // Check if we're on the board view already
  const boardView = page.locator('[data-testid="board-view"]');
  const isOnBoard = await boardView.isVisible().catch(() => false);

  if (!isOnBoard) {
    // Try to click on a recent project first (from welcome screen)
    const recentProject = page.locator('p:has-text("Test Project")').first();
    if (await recentProject.isVisible().catch(() => false)) {
      await recentProject.click();
      await page.waitForTimeout(200);
    }

    // Then click on Kanban Board nav button to ensure we're on the board
    const kanbanNav = page.locator('[data-testid="nav-board"]');
    if (await kanbanNav.isVisible().catch(() => false)) {
      await kanbanNav.click();
    }
  }

  // Wait for the board view to be visible
  await waitForElement(page, "board-view", { timeout: 10000 });
}

/**
 * Check if the agent output modal is visible
 */
export async function isAgentOutputModalVisible(page: Page): Promise<boolean> {
  const modal = page.locator('[data-testid="agent-output-modal"]');
  return await modal.isVisible();
}

/**
 * Wait for the agent output modal to be visible
 */
export async function waitForAgentOutputModal(
  page: Page,
  options?: { timeout?: number }
): Promise<Locator> {
  return await waitForElement(page, "agent-output-modal", options);
}

/**
 * Wait for the agent output modal to be hidden
 */
export async function waitForAgentOutputModalHidden(
  page: Page,
  options?: { timeout?: number }
): Promise<void> {
  await waitForElementHidden(page, "agent-output-modal", options);
}

/**
 * Drag a kanban card from one column to another
 */
export async function dragKanbanCard(
  page: Page,
  featureId: string,
  targetColumnId: string
): Promise<void> {
  const card = page.locator(`[data-testid="kanban-card-${featureId}"]`);
  const dragHandle = page.locator(`[data-testid="drag-handle-${featureId}"]`);
  const targetColumn = page.locator(`[data-testid="kanban-column-${targetColumnId}"]`);

  // Perform drag and drop
  await dragHandle.dragTo(targetColumn);
}

/**
 * Get a kanban card by feature ID
 */
export async function getKanbanCard(
  page: Page,
  featureId: string
): Promise<Locator> {
  return page.locator(`[data-testid="kanban-card-${featureId}"]`);
}

/**
 * Click the view output button on a kanban card
 */
export async function clickViewOutput(
  page: Page,
  featureId: string
): Promise<void> {
  // Try the running version first, then the in-progress version
  const runningBtn = page.locator(`[data-testid="view-output-${featureId}"]`);
  const inProgressBtn = page.locator(
    `[data-testid="view-output-inprogress-${featureId}"]`
  );

  if (await runningBtn.isVisible()) {
    await runningBtn.click();
  } else if (await inProgressBtn.isVisible()) {
    await inProgressBtn.click();
  } else {
    throw new Error(`View output button not found for feature ${featureId}`);
  }
}

/**
 * Perform a drag and drop operation that works with @dnd-kit
 * This uses explicit mouse movements with pointer events
 */
export async function dragAndDropWithDndKit(
  page: Page,
  sourceLocator: Locator,
  targetLocator: Locator
): Promise<void> {
  const sourceBox = await sourceLocator.boundingBox();
  const targetBox = await targetLocator.boundingBox();

  if (!sourceBox || !targetBox) {
    throw new Error("Could not find source or target element bounds");
  }

  // Start drag from the center of the source element
  const startX = sourceBox.x + sourceBox.width / 2;
  const startY = sourceBox.y + sourceBox.height / 2;

  // End drag at the center of the target element
  const endX = targetBox.x + targetBox.width / 2;
  const endY = targetBox.y + targetBox.height / 2;

  // Perform the drag and drop with pointer events
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.waitForTimeout(150); // Give dnd-kit time to recognize the drag
  await page.mouse.move(endX, endY, { steps: 15 });
  await page.waitForTimeout(100); // Allow time for drop detection
  await page.mouse.up();
}

/**
 * Get the concurrency slider container
 */
export async function getConcurrencySliderContainer(
  page: Page
): Promise<Locator> {
  return page.locator('[data-testid="concurrency-slider-container"]');
}

/**
 * Get the concurrency slider
 */
export async function getConcurrencySlider(page: Page): Promise<Locator> {
  return page.locator('[data-testid="concurrency-slider"]');
}

/**
 * Get the displayed concurrency value
 */
export async function getConcurrencyValue(page: Page): Promise<string | null> {
  const valueElement = page.locator('[data-testid="concurrency-value"]');
  return await valueElement.textContent();
}

/**
 * Change the concurrency slider value by clicking on the slider track
 */
export async function setConcurrencyValue(
  page: Page,
  targetValue: number,
  min: number = 1,
  max: number = 10
): Promise<void> {
  const slider = page.locator('[data-testid="concurrency-slider"]');
  const sliderBounds = await slider.boundingBox();

  if (!sliderBounds) {
    throw new Error("Concurrency slider not found or not visible");
  }

  // Calculate position for target value
  const percentage = (targetValue - min) / (max - min);
  const targetX = sliderBounds.x + sliderBounds.width * percentage;
  const centerY = sliderBounds.y + sliderBounds.height / 2;

  // Click at the target position to set the value
  await page.mouse.click(targetX, centerY);
}

/**
 * Set up a mock project with custom concurrency value
 */
export async function setupMockProjectWithConcurrency(
  page: Page,
  concurrency: number
): Promise<void> {
  await page.addInitScript((maxConcurrency: number) => {
    const mockProject = {
      id: "test-project-1",
      name: "Test Project",
      path: "/mock/test-project",
      lastOpened: new Date().toISOString(),
    };

    const mockState = {
      state: {
        projects: [mockProject],
        currentProject: mockProject,
        theme: "dark",
        sidebarOpen: true,
        apiKeys: { anthropic: "", google: "" },
        chatSessions: [],
        chatHistoryOpen: false,
        maxConcurrency: maxConcurrency,
      },
      version: 0,
    };

    localStorage.setItem("automaker-storage", JSON.stringify(mockState));
  }, concurrency);
}

/**
 * Navigate to the context view
 */
export async function navigateToContext(page: Page): Promise<void> {
  await page.goto("/");

  // Wait for the page to load
  await page.waitForLoadState("networkidle");

  // Click on the Context nav button
  const contextNav = page.locator('[data-testid="nav-context"]');
  if (await contextNav.isVisible().catch(() => false)) {
    await contextNav.click();
  }

  // Wait for the context view to be visible
  await waitForElement(page, "context-view", { timeout: 10000 });
}

/**
 * Get the context file list element
 */
export async function getContextFileList(page: Page): Promise<Locator> {
  return page.locator('[data-testid="context-file-list"]');
}

/**
 * Click on a context file in the list
 */
export async function clickContextFile(
  page: Page,
  fileName: string
): Promise<void> {
  const fileButton = page.locator(`[data-testid="context-file-${fileName}"]`);
  await fileButton.click();
}

/**
 * Get the context editor element
 */
export async function getContextEditor(page: Page): Promise<Locator> {
  return page.locator('[data-testid="context-editor"]');
}

/**
 * Open the add context file dialog
 */
export async function openAddContextFileDialog(page: Page): Promise<void> {
  await clickElement(page, "add-context-file");
  await waitForElement(page, "add-context-dialog");
}

/**
 * Wait for an error toast to appear with specific text
 */
export async function waitForErrorToast(
  page: Page,
  titleText?: string,
  options?: { timeout?: number }
): Promise<Locator> {
  // Sonner toasts use data-sonner-toast and data-type="error" for error toasts
  const toastSelector = titleText
    ? `[data-sonner-toast][data-type="error"]:has-text("${titleText}")`
    : '[data-sonner-toast][data-type="error"]';

  const toast = page.locator(toastSelector).first();
  await toast.waitFor({
    timeout: options?.timeout ?? 5000,
    state: "visible",
  });
  return toast;
}

/**
 * Check if an error toast is visible
 */
export async function isErrorToastVisible(
  page: Page,
  titleText?: string
): Promise<boolean> {
  const toastSelector = titleText
    ? `[data-sonner-toast][data-type="error"]:has-text("${titleText}")`
    : '[data-sonner-toast][data-type="error"]';

  const toast = page.locator(toastSelector).first();
  return await toast.isVisible();
}

/**
 * Set up a mock project with specific running tasks to simulate concurrency limit
 */
export async function setupMockProjectAtConcurrencyLimit(
  page: Page,
  maxConcurrency: number = 1,
  runningTasks: string[] = ["running-task-1"]
): Promise<void> {
  await page.addInitScript(
    ({ maxConcurrency, runningTasks }: { maxConcurrency: number; runningTasks: string[] }) => {
      const mockProject = {
        id: "test-project-1",
        name: "Test Project",
        path: "/mock/test-project",
        lastOpened: new Date().toISOString(),
      };

      const mockState = {
        state: {
          projects: [mockProject],
          currentProject: mockProject,
          theme: "dark",
          sidebarOpen: true,
          apiKeys: { anthropic: "", google: "" },
          chatSessions: [],
          chatHistoryOpen: false,
          maxConcurrency: maxConcurrency,
          isAutoModeRunning: false,
          runningAutoTasks: runningTasks,
          autoModeActivityLog: [],
        },
        version: 0,
      };

      localStorage.setItem("automaker-storage", JSON.stringify(mockState));
    },
    { maxConcurrency, runningTasks }
  );
}

/**
 * Get the force stop button for a specific feature
 */
export async function getForceStopButton(
  page: Page,
  featureId: string
): Promise<Locator> {
  return page.locator(`[data-testid="force-stop-${featureId}"]`);
}

/**
 * Click the force stop button for a specific feature
 */
export async function clickForceStop(
  page: Page,
  featureId: string
): Promise<void> {
  const button = page.locator(`[data-testid="force-stop-${featureId}"]`);
  await button.click();
}

/**
 * Check if the force stop button is visible for a feature
 */
export async function isForceStopButtonVisible(
  page: Page,
  featureId: string
): Promise<boolean> {
  const button = page.locator(`[data-testid="force-stop-${featureId}"]`);
  return await button.isVisible();
}

/**
 * Wait for a success toast to appear with specific text
 */
export async function waitForSuccessToast(
  page: Page,
  titleText?: string,
  options?: { timeout?: number }
): Promise<Locator> {
  // Sonner toasts use data-sonner-toast and data-type="success" for success toasts
  const toastSelector = titleText
    ? `[data-sonner-toast][data-type="success"]:has-text("${titleText}")`
    : '[data-sonner-toast][data-type="success"]';

  const toast = page.locator(toastSelector).first();
  await toast.waitFor({
    timeout: options?.timeout ?? 5000,
    state: "visible",
  });
  return toast;
}

/**
 * Get the delete button for an in_progress feature
 */
export async function getDeleteInProgressButton(
  page: Page,
  featureId: string
): Promise<Locator> {
  return page.locator(`[data-testid="delete-inprogress-feature-${featureId}"]`);
}

/**
 * Click the delete button for an in_progress feature
 */
export async function clickDeleteInProgressFeature(
  page: Page,
  featureId: string
): Promise<void> {
  const button = page.locator(
    `[data-testid="delete-inprogress-feature-${featureId}"]`
  );
  await button.click();
}

/**
 * Check if the delete button is visible for an in_progress feature
 */
export async function isDeleteInProgressButtonVisible(
  page: Page,
  featureId: string
): Promise<boolean> {
  const button = page.locator(
    `[data-testid="delete-inprogress-feature-${featureId}"]`
  );
  return await button.isVisible();
}

/**
 * Set up a mock project with features in different states
 */
export async function setupMockProjectWithFeatures(
  page: Page,
  options?: {
    maxConcurrency?: number;
    runningTasks?: string[];
    features?: Array<{
      id: string;
      category: string;
      description: string;
      status: "backlog" | "in_progress" | "verified";
      steps?: string[];
    }>;
  }
): Promise<void> {
  await page.addInitScript(
    (opts: typeof options) => {
      const mockProject = {
        id: "test-project-1",
        name: "Test Project",
        path: "/mock/test-project",
        lastOpened: new Date().toISOString(),
      };

      const mockFeatures = opts?.features || [];

      const mockState = {
        state: {
          projects: [mockProject],
          currentProject: mockProject,
          theme: "dark",
          sidebarOpen: true,
          apiKeys: { anthropic: "", google: "" },
          chatSessions: [],
          chatHistoryOpen: false,
          maxConcurrency: opts?.maxConcurrency ?? 3,
          isAutoModeRunning: false,
          runningAutoTasks: opts?.runningTasks ?? [],
          autoModeActivityLog: [],
          features: mockFeatures,
        },
        version: 0,
      };

      localStorage.setItem("automaker-storage", JSON.stringify(mockState));
    },
    options
  );
}

/**
 * Set up a mock project with a feature context file
 * This simulates an agent having created context for a feature
 */
export async function setupMockProjectWithContextFile(
  page: Page,
  featureId: string,
  contextContent: string = "# Agent Context\n\nPrevious implementation work..."
): Promise<void> {
  await page.addInitScript(
    ({ featureId, contextContent }: { featureId: string; contextContent: string }) => {
      const mockProject = {
        id: "test-project-1",
        name: "Test Project",
        path: "/mock/test-project",
        lastOpened: new Date().toISOString(),
      };

      const mockState = {
        state: {
          projects: [mockProject],
          currentProject: mockProject,
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

      // Set up mock file system with a context file for the feature
      // This will be used by the mock electron API
      (window as any).__mockContextFile = {
        featureId,
        path: `/mock/test-project/.automaker/agents-context/${featureId}.md`,
        content: contextContent,
      };
    },
    { featureId, contextContent }
  );
}

/**
 * Get the category autocomplete input element
 */
export async function getCategoryAutocompleteInput(
  page: Page,
  testId: string = "feature-category-input"
): Promise<Locator> {
  return page.locator(`[data-testid="${testId}"]`);
}

/**
 * Get the category autocomplete dropdown list
 */
export async function getCategoryAutocompleteList(page: Page): Promise<Locator> {
  return page.locator('[data-testid="category-autocomplete-list"]');
}

/**
 * Check if the category autocomplete dropdown is visible
 */
export async function isCategoryAutocompleteListVisible(page: Page): Promise<boolean> {
  const list = page.locator('[data-testid="category-autocomplete-list"]');
  return await list.isVisible();
}

/**
 * Wait for the category autocomplete dropdown to be visible
 */
export async function waitForCategoryAutocompleteList(
  page: Page,
  options?: { timeout?: number }
): Promise<Locator> {
  return await waitForElement(page, "category-autocomplete-list", options);
}

/**
 * Wait for the category autocomplete dropdown to be hidden
 */
export async function waitForCategoryAutocompleteListHidden(
  page: Page,
  options?: { timeout?: number }
): Promise<void> {
  await waitForElementHidden(page, "category-autocomplete-list", options);
}

/**
 * Click a category option in the autocomplete dropdown
 */
export async function clickCategoryOption(
  page: Page,
  categoryName: string
): Promise<void> {
  const optionTestId = `category-option-${categoryName.toLowerCase().replace(/\s+/g, "-")}`;
  const option = page.locator(`[data-testid="${optionTestId}"]`);
  await option.click();
}

/**
 * Get a category option element by name
 */
export async function getCategoryOption(
  page: Page,
  categoryName: string
): Promise<Locator> {
  const optionTestId = `category-option-${categoryName.toLowerCase().replace(/\s+/g, "-")}`;
  return page.locator(`[data-testid="${optionTestId}"]`);
}

/**
 * Navigate to the agent view
 */
export async function navigateToAgent(page: Page): Promise<void> {
  await page.goto("/");

  // Wait for the page to load
  await page.waitForLoadState("networkidle");

  // Click on the Agent nav button
  const agentNav = page.locator('[data-testid="nav-agent"]');
  if (await agentNav.isVisible().catch(() => false)) {
    await agentNav.click();
  }

  // Wait for the agent view to be visible
  await waitForElement(page, "agent-view", { timeout: 10000 });
}

/**
 * Get the session list element
 */
export async function getSessionList(page: Page): Promise<Locator> {
  return page.locator('[data-testid="session-list"]');
}

/**
 * Get the new session button
 */
export async function getNewSessionButton(page: Page): Promise<Locator> {
  return page.locator('[data-testid="new-session-button"]');
}

/**
 * Click the new session button
 */
export async function clickNewSessionButton(page: Page): Promise<void> {
  const button = await getNewSessionButton(page);
  await button.click();
}

/**
 * Get a session item by its ID
 */
export async function getSessionItem(
  page: Page,
  sessionId: string
): Promise<Locator> {
  return page.locator(`[data-testid="session-item-${sessionId}"]`);
}

/**
 * Click the archive button for a session
 */
export async function clickArchiveSession(
  page: Page,
  sessionId: string
): Promise<void> {
  const button = page.locator(`[data-testid="archive-session-${sessionId}"]`);
  await button.click();
}

/**
 * Check if the no session placeholder is visible
 */
export async function isNoSessionPlaceholderVisible(page: Page): Promise<boolean> {
  const placeholder = page.locator('[data-testid="no-session-placeholder"]');
  return await placeholder.isVisible();
}

/**
 * Wait for the no session placeholder to be visible
 */
export async function waitForNoSessionPlaceholder(
  page: Page,
  options?: { timeout?: number }
): Promise<Locator> {
  return await waitForElement(page, "no-session-placeholder", options);
}

/**
 * Check if the message list is visible (indicates a session is selected)
 */
export async function isMessageListVisible(page: Page): Promise<boolean> {
  const messageList = page.locator('[data-testid="message-list"]');
  return await messageList.isVisible();
}
