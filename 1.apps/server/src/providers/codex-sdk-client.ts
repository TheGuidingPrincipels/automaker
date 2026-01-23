/**
 * Codex SDK client - Executes Codex queries via official @openai/codex-sdk
 *
 * Used for programmatic control of Codex from within the application.
 * Provides cleaner integration than spawning CLI processes.
 *
 * Uses OpenAI-specific ThreadOptions for proper model and reasoning configuration.
 */

import { Codex, type ThreadOptions, type ModelReasoningEffort } from '@openai/codex-sdk';
import { formatHistoryAsText, classifyError, getUserFriendlyErrorMessage } from '@automaker/utils';
import { supportsReasoningEffort, type ReasoningEffort } from '@automaker/types';
import type { ExecuteOptions, ProviderMessage } from './types.js';

const OPENAI_API_KEY_ENV = 'OPENAI_API_KEY';
const SDK_HISTORY_HEADER = 'Current request:\n';
const DEFAULT_RESPONSE_TEXT = '';
const SDK_ERROR_DETAILS_LABEL = 'Details:';

/**
 * Map ReasoningEffort to SDK's ModelReasoningEffort type.
 * The SDK doesn't support 'none' - we handle that by not setting the option.
 */
function mapReasoningEffort(effort: ReasoningEffort): ModelReasoningEffort | null {
  if (effort === 'none') {
    return null; // SDK doesn't support 'none', omit the option
  }
  // SDK accepts: 'minimal' | 'low' | 'medium' | 'high' | 'xhigh'
  return effort as ModelReasoningEffort;
}

/**
 * Map CodexSandboxMode to SDK's SandboxMode type.
 */
function mapSandboxMode(
  mode?: 'read-only' | 'workspace-write' | 'danger-full-access'
): 'read-only' | 'workspace-write' | 'danger-full-access' | undefined {
  return mode;
}

type PromptBlock = {
  type: string;
  text?: string;
  source?: {
    type?: string;
    media_type?: string;
    data?: string;
  };
};

function resolveApiKey(): string {
  const apiKey = process.env[OPENAI_API_KEY_ENV];
  if (!apiKey) {
    throw new Error('OPENAI_API_KEY is not set.');
  }
  return apiKey;
}

function normalizePromptBlocks(prompt: ExecuteOptions['prompt']): PromptBlock[] {
  if (Array.isArray(prompt)) {
    return prompt as PromptBlock[];
  }
  return [{ type: 'text', text: prompt }];
}

function buildPromptText(options: ExecuteOptions, systemPrompt: string | null): string {
  const historyText =
    options.conversationHistory && options.conversationHistory.length > 0
      ? formatHistoryAsText(options.conversationHistory)
      : '';

  const promptBlocks = normalizePromptBlocks(options.prompt);
  const promptTexts: string[] = [];

  for (const block of promptBlocks) {
    if (block.type === 'text' && typeof block.text === 'string' && block.text.trim()) {
      promptTexts.push(block.text);
    }
  }

  const promptContent = promptTexts.join('\n\n');
  if (!promptContent.trim()) {
    throw new Error('Codex SDK prompt is empty.');
  }

  const parts: string[] = [];
  if (systemPrompt) {
    parts.push(`System: ${systemPrompt}`);
  }
  if (historyText) {
    parts.push(historyText);
  }
  parts.push(`${SDK_HISTORY_HEADER}${promptContent}`);

  return parts.join('\n\n');
}

function buildSdkErrorMessage(rawMessage: string, userMessage: string): string {
  if (!rawMessage) {
    return userMessage;
  }
  if (!userMessage || rawMessage === userMessage) {
    return rawMessage;
  }
  return `${userMessage}\n\n${SDK_ERROR_DETAILS_LABEL} ${rawMessage}`;
}

/**
 * Build OpenAI-specific ThreadOptions for the Codex SDK.
 * This properly configures the model, reasoning effort, sandbox mode, and other settings.
 *
 * @param options - Execute options containing model and codex-specific settings
 * @returns ThreadOptions configured for the Codex SDK
 */
function buildThreadOptions(options: ExecuteOptions): ThreadOptions {
  const threadOptions: ThreadOptions = {
    // Set the model - this is the key OpenAI-specific setting
    model: options.model,
    // Set working directory for file operations
    workingDirectory: options.cwd,
  };

  // Configure reasoning effort if model supports it (OpenAI-specific feature)
  // We validate both that the option is set AND the model supports it
  if (options.reasoningEffort && supportsReasoningEffort(options.model)) {
    const sdkReasoningEffort = mapReasoningEffort(options.reasoningEffort);
    if (sdkReasoningEffort !== null) {
      // Type assertion is safe here because mapReasoningEffort returns
      // a valid ModelReasoningEffort when not returning null
      threadOptions.modelReasoningEffort = sdkReasoningEffort;
    }
  }

  // Apply codex-specific settings if provided
  if (options.codexSettings) {
    // Map sandbox mode (OpenAI Codex feature)
    if (options.codexSettings.sandboxMode) {
      threadOptions.sandboxMode = mapSandboxMode(options.codexSettings.sandboxMode);
    }

    // Enable web search if configured (OpenAI Codex feature)
    if (options.codexSettings.enableWebSearch) {
      threadOptions.webSearchEnabled = true;
    }

    // Map approval policy to SDK format
    if (options.codexSettings.approvalPolicy) {
      threadOptions.approvalPolicy = options.codexSettings.approvalPolicy;
    }

    // Add additional directories for file access
    if (options.codexSettings.additionalDirs && options.codexSettings.additionalDirs.length > 0) {
      threadOptions.additionalDirectories = options.codexSettings.additionalDirs;
    }
  }

  return threadOptions;
}

/**
 * Execute a query using the official Codex SDK with OpenAI-specific mode.
 *
 * The SDK provides a cleaner interface than spawning CLI processes:
 * - Handles authentication automatically
 * - Provides TypeScript types
 * - Supports thread management and resumption
 * - Better error handling
 *
 * OpenAI-specific features configured via ThreadOptions:
 * - Model selection (gpt-5.1-codex-max, gpt-5.2-codex, etc.)
 * - Reasoning effort (minimal, low, medium, high, xhigh)
 * - Sandbox mode (read-only, workspace-write, danger-full-access)
 * - Web search capability
 * - Approval policies
 */
export async function* executeCodexSdkQuery(
  options: ExecuteOptions,
  systemPrompt: string | null
): AsyncGenerator<ProviderMessage> {
  try {
    const apiKey = resolveApiKey();
    const codex = new Codex({ apiKey });

    // Build OpenAI-specific thread options
    const threadOptions = buildThreadOptions(options);

    // Resume existing thread or start new one with OpenAI-specific options
    let thread;
    if (options.sdkSessionId) {
      try {
        thread = codex.resumeThread(options.sdkSessionId, threadOptions);
      } catch {
        // If resume fails, start a new thread with options
        thread = codex.startThread(threadOptions);
      }
    } else {
      thread = codex.startThread(threadOptions);
    }

    const promptText = buildPromptText(options, systemPrompt);

    // Build run options (turn-level options, separate from thread options)
    const runOptions: {
      signal?: AbortSignal;
    } = {
      signal: options.abortController?.signal,
    };

    // Run the query
    const result = await thread.run(promptText, runOptions);

    // Extract response text (from finalResponse property)
    const outputText = result.finalResponse ?? DEFAULT_RESPONSE_TEXT;

    // Get thread ID (may be null if not populated yet)
    const threadId = thread.id ?? undefined;

    // Yield assistant message
    yield {
      type: 'assistant',
      session_id: threadId,
      message: {
        role: 'assistant',
        content: [{ type: 'text', text: outputText }],
      },
    };

    // Yield result
    yield {
      type: 'result',
      subtype: 'success',
      session_id: threadId,
      result: outputText,
    };
  } catch (error) {
    const errorInfo = classifyError(error);
    const userMessage = getUserFriendlyErrorMessage(error);
    const combinedMessage = buildSdkErrorMessage(errorInfo.message, userMessage);
    console.error('[CodexSDK] executeQuery() error during execution:', {
      type: errorInfo.type,
      message: errorInfo.message,
      isRateLimit: errorInfo.isRateLimit,
      retryAfter: errorInfo.retryAfter,
      stack: error instanceof Error ? error.stack : undefined,
    });
    yield { type: 'error', error: combinedMessage };
  }
}
