/**
 * Token Types - Shared types for token usage tracking and rate limiting
 *
 * Provides unified type definitions for tracking AI model token usage
 * across different providers (Claude, Codex, etc.). These types are used
 * by usage services, UI components, and API endpoints.
 */

// ============================================================================
// Base Token Usage Types
// ============================================================================

/**
 * TokenUsage - Basic token usage statistics
 *
 * Represents the tokens used in a single operation (request/response).
 */
export interface TokenUsage {
  /** Number of input tokens (prompt) */
  inputTokens: number;
  /** Number of output tokens (completion) */
  outputTokens: number;
  /** Total tokens (input + output) */
  totalTokens: number;
  /** Thinking/reasoning tokens (for models with extended thinking) */
  thinkingTokens?: number;
  /** Cache read tokens (for models with prompt caching) */
  cacheReadTokens?: number;
  /** Cache write tokens (for models with prompt caching) */
  cacheWriteTokens?: number;
}

/**
 * TokenCost - Cost information for token usage
 */
export interface TokenCost {
  /** Cost in the provider's currency unit (e.g., USD cents) */
  amount: number;
  /** Currency code (e.g., 'USD') */
  currency: string;
}

/**
 * TokenUsageWithCost - Token usage with optional cost tracking
 */
export interface TokenUsageWithCost extends TokenUsage {
  /** Cost associated with this usage */
  cost?: TokenCost;
}

// ============================================================================
// Rate Limit Types
// ============================================================================

/**
 * RateLimitWindow - Rate limit information for a specific time window
 *
 * Tracks usage against rate limits for providers with usage quotas.
 */
export interface RateLimitWindow {
  /** Maximum allowed tokens/requests in this window */
  limit: number;
  /** Amount used in current window */
  used: number;
  /** Amount remaining in current window */
  remaining: number;
  /** Percentage of limit used (0-100) */
  usedPercent: number;
  /** Duration of the rate limit window in minutes */
  windowDurationMins: number;
  /** Unix timestamp when the window resets */
  resetsAt: number;
  /** ISO date string for reset time (derived from resetsAt) */
  resetTimeISO?: string;
  /** Human-readable reset time text */
  resetText?: string;
}

/**
 * UsageStats - Aggregate usage statistics
 *
 * Used for tracking usage over longer periods (session, daily, weekly).
 */
export interface UsageStats {
  /** Total tokens used */
  tokensUsed: number;
  /** Token limit for this period (0 if unlimited) */
  tokenLimit: number;
  /** Percentage of limit used (0-100) */
  percentage: number;
  /** ISO date string when this period resets */
  resetTime: string;
  /** Human-readable reset time (e.g., "Mon, Jan 24, 10am") */
  resetText: string;
}

// ============================================================================
// Provider-Specific Types
// ============================================================================

/**
 * ClaudeTokenUsage - Claude/Anthropic specific usage tracking
 *
 * Tracks session and weekly usage for Claude Max subscription.
 */
export interface ClaudeTokenUsage {
  /** Session-level usage stats */
  session: UsageStats;
  /** Weekly usage stats (all models) */
  weekly: UsageStats;
  /** Weekly usage stats for Sonnet/Opus models specifically */
  sonnetWeekly?: UsageStats;
  /** Cost tracking for API key users */
  cost?: {
    used: number;
    limit: number;
    currency: string;
  };
  /** ISO timestamp when data was last fetched */
  lastUpdated: string;
  /** User's timezone for display purposes */
  userTimezone: string;
}

/**
 * CodexPlanType - Subscription plan types for Codex/OpenAI
 */
export type CodexPlanType = 'free' | 'plus' | 'pro' | 'team' | 'enterprise' | 'edu' | 'unknown';

/**
 * CodexTokenUsage - Codex/OpenAI specific usage tracking
 *
 * Tracks rate limits and plan information for Codex CLI.
 */
export interface CodexTokenUsage {
  /** Primary rate limit window (usually shorter term) */
  primary?: RateLimitWindow;
  /** Secondary rate limit window (usually longer term) */
  secondary?: RateLimitWindow;
  /** User's subscription plan type */
  planType: CodexPlanType;
  /** ISO timestamp when data was last fetched */
  lastUpdated: string;
}

// ============================================================================
// Unified Usage Types
// ============================================================================

/**
 * ProviderType - Supported AI providers for usage tracking
 */
export type UsageProviderType = 'claude' | 'codex' | 'cursor' | 'opencode' | 'gemini';

/**
 * UnifiedTokenUsage - Normalized usage data across providers
 *
 * Provides a consistent interface for displaying usage information
 * regardless of the underlying provider.
 */
export interface UnifiedTokenUsage {
  /** Provider this usage is from */
  provider: UsageProviderType;
  /** Primary usage percentage (0-100, main display value) */
  usagePercent: number;
  /** Time until reset (ISO string) */
  resetTime: string;
  /** Human-readable reset description */
  resetText: string;
  /** Status indicator color based on usage level */
  statusColor: 'green' | 'yellow' | 'orange' | 'red' | 'gray';
  /** Status description text */
  statusDescription: string;
  /** ISO timestamp when data was last fetched */
  lastUpdated: string;
  /** Provider-specific raw data */
  raw?: ClaudeTokenUsage | CodexTokenUsage;
}

// ============================================================================
// Session Token Tracking
// ============================================================================

/**
 * SessionTokenMetrics - Token metrics for an agent session
 *
 * Tracks cumulative token usage across all messages in a session.
 */
export interface SessionTokenMetrics {
  /** Session identifier */
  sessionId: string;
  /** Total input tokens across all messages */
  totalInputTokens: number;
  /** Total output tokens across all messages */
  totalOutputTokens: number;
  /** Total thinking tokens across all messages */
  totalThinkingTokens: number;
  /** Total cache read tokens */
  totalCacheReadTokens: number;
  /** Total cache write tokens */
  totalCacheWriteTokens: number;
  /** Total cost if tracked */
  totalCost?: TokenCost;
  /** Number of messages/turns in session */
  messageCount: number;
  /** Session start time (ISO string) */
  startedAt: string;
  /** Last activity time (ISO string) */
  lastActivityAt: string;
}

/**
 * MessageTokenMetrics - Token metrics for a single message
 *
 * Tracks tokens used for a specific message exchange.
 */
export interface MessageTokenMetrics {
  /** Message identifier */
  messageId: string;
  /** Token usage for this message */
  usage: TokenUsage;
  /** Model used for this message */
  model: string;
  /** Cost for this message if tracked */
  cost?: TokenCost;
  /** Timestamp (ISO string) */
  timestamp: string;
}

// ============================================================================
// JSON Schema for Token Usage (for structured output)
// ============================================================================

/**
 * JSON Schema for TokenUsage
 * Used with Claude's structured output feature for reliable parsing
 */
export const tokenUsageSchema = {
  type: 'object',
  properties: {
    inputTokens: {
      type: 'number',
      description: 'Number of input tokens (prompt)',
    },
    outputTokens: {
      type: 'number',
      description: 'Number of output tokens (completion)',
    },
    totalTokens: {
      type: 'number',
      description: 'Total tokens (input + output)',
    },
    thinkingTokens: {
      type: 'number',
      description: 'Thinking/reasoning tokens for models with extended thinking',
    },
    cacheReadTokens: {
      type: 'number',
      description: 'Cache read tokens for models with prompt caching',
    },
    cacheWriteTokens: {
      type: 'number',
      description: 'Cache write tokens for models with prompt caching',
    },
  },
  required: ['inputTokens', 'outputTokens', 'totalTokens'],
  additionalProperties: false,
} as const;

/**
 * JSON Schema for SessionTokenMetrics
 * Used for structured output when summarizing session usage
 */
export const sessionTokenMetricsSchema = {
  type: 'object',
  properties: {
    sessionId: {
      type: 'string',
      description: 'Session identifier',
    },
    totalInputTokens: {
      type: 'number',
      description: 'Total input tokens across all messages',
    },
    totalOutputTokens: {
      type: 'number',
      description: 'Total output tokens across all messages',
    },
    totalThinkingTokens: {
      type: 'number',
      description: 'Total thinking tokens across all messages',
    },
    totalCacheReadTokens: {
      type: 'number',
      description: 'Total cache read tokens',
    },
    totalCacheWriteTokens: {
      type: 'number',
      description: 'Total cache write tokens',
    },
    messageCount: {
      type: 'number',
      description: 'Number of messages/turns in session',
    },
    startedAt: {
      type: 'string',
      description: 'Session start time (ISO string)',
    },
    lastActivityAt: {
      type: 'string',
      description: 'Last activity time (ISO string)',
    },
  },
  required: [
    'sessionId',
    'totalInputTokens',
    'totalOutputTokens',
    'totalThinkingTokens',
    'totalCacheReadTokens',
    'totalCacheWriteTokens',
    'messageCount',
    'startedAt',
    'lastActivityAt',
  ],
  additionalProperties: false,
} as const;

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Calculate status color based on usage percentage
 *
 * @param usagePercent - Usage percentage (0-100)
 * @returns Status color for UI display
 */
export function getUsageStatusColor(
  usagePercent: number
): 'green' | 'yellow' | 'orange' | 'red' | 'gray' {
  if (usagePercent < 0 || isNaN(usagePercent)) return 'gray';
  if (usagePercent < 50) return 'green';
  if (usagePercent < 75) return 'yellow';
  if (usagePercent < 90) return 'orange';
  return 'red';
}

/**
 * Get status description based on usage percentage
 *
 * @param usagePercent - Usage percentage (0-100)
 * @returns Human-readable status description
 */
export function getUsageStatusDescription(usagePercent: number): string {
  if (usagePercent < 0 || isNaN(usagePercent)) return 'Usage data unavailable';
  if (usagePercent < 50) return 'Plenty of capacity remaining';
  if (usagePercent < 75) return 'Moderate usage';
  if (usagePercent < 90) return 'Approaching limit';
  if (usagePercent < 100) return 'Near limit';
  return 'Limit reached';
}

/**
 * Create an empty TokenUsage object
 *
 * @returns TokenUsage with all values set to 0
 */
export function createEmptyTokenUsage(): TokenUsage {
  return {
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
    thinkingTokens: 0,
    cacheReadTokens: 0,
    cacheWriteTokens: 0,
  };
}

/**
 * Sum multiple TokenUsage objects
 *
 * @param usages - Array of TokenUsage objects to sum
 * @returns Combined TokenUsage
 */
export function sumTokenUsage(usages: TokenUsage[]): TokenUsage {
  return usages.reduce(
    (acc, usage) => ({
      inputTokens: acc.inputTokens + usage.inputTokens,
      outputTokens: acc.outputTokens + usage.outputTokens,
      totalTokens: acc.totalTokens + usage.totalTokens,
      thinkingTokens: (acc.thinkingTokens ?? 0) + (usage.thinkingTokens ?? 0),
      cacheReadTokens: (acc.cacheReadTokens ?? 0) + (usage.cacheReadTokens ?? 0),
      cacheWriteTokens: (acc.cacheWriteTokens ?? 0) + (usage.cacheWriteTokens ?? 0),
    }),
    createEmptyTokenUsage()
  );
}

/**
 * Format token count for display
 *
 * @param tokens - Number of tokens
 * @returns Formatted string (e.g., "1.2K", "3.5M")
 */
export function formatTokenCount(tokens: number): string {
  if (tokens < 1000) return tokens.toString();
  if (tokens < 1_000_000) return `${(tokens / 1000).toFixed(1)}K`;
  return `${(tokens / 1_000_000).toFixed(2)}M`;
}
