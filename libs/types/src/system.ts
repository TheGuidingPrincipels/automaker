/**
 * System Types - Types for multi-agent system orchestration
 *
 * Systems are composed workflows that coordinate multiple agents to accomplish
 * complex tasks. They define the agents involved, the workflow steps, and how
 * data flows between agents.
 */

import type { CustomAgentModelConfig } from './custom-agent.js';

/**
 * SystemStatus - Lifecycle status of a system
 */
export type SystemStatus = 'draft' | 'active' | 'archived';

/**
 * SystemExecutionStatus - Status of a system execution
 */
export type SystemExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

/**
 * SystemAgentRole - Role an agent plays within a system
 */
export type SystemAgentRole =
  | 'orchestrator' // Coordinates other agents
  | 'researcher' // Gathers information
  | 'analyzer' // Analyzes data/code
  | 'implementer' // Writes/modifies code
  | 'reviewer' // Reviews work
  | 'validator' // Validates outputs
  | 'custom'; // Custom role

/**
 * SystemAgent - An agent within a system with role-specific configuration
 */
export interface SystemAgent {
  /** Unique identifier within the system */
  id: string;
  /** Reference to a CustomAgent (or null for inline definition) */
  customAgentId?: string;
  /** Display name for this agent in the system */
  name: string;
  /** Role this agent plays */
  role: SystemAgentRole;
  /** Description of what this agent does in this system */
  description?: string;
  /** System prompt override (if different from base agent) */
  systemPromptOverride?: string;
  /** Model config override (if different from base agent) */
  modelConfigOverride?: CustomAgentModelConfig;
  /** Order in which this agent typically acts (for visualization) */
  order?: number;
}

/**
 * WorkflowStepType - Types of workflow steps
 */
export type WorkflowStepType =
  | 'agent' // Execute an agent
  | 'conditional' // Branch based on condition
  | 'parallel' // Execute multiple steps in parallel
  | 'sequential' // Execute steps in sequence
  | 'loop' // Loop until condition met
  | 'human_review' // Wait for human approval
  | 'transform'; // Transform data between steps

/**
 * WorkflowStepCondition - Condition for conditional steps
 */
export interface WorkflowStepCondition {
  /** Field to evaluate from previous step output */
  field: string;
  /** Operator for comparison */
  operator:
    | 'equals'
    | 'notEquals'
    | 'contains'
    | 'notContains'
    | 'greaterThan'
    | 'lessThan'
    | 'exists'
    | 'notExists';
  /** Value to compare against */
  value?: string | number | boolean;
}

/**
 * SystemWorkflowStep - A step in a system's workflow
 */
export interface SystemWorkflowStep {
  /** Unique identifier */
  id: string;
  /** Step type */
  type: WorkflowStepType;
  /** Display name */
  name: string;
  /** Description of what this step does */
  description?: string;
  /** Agent ID to execute (for 'agent' type) */
  agentId?: string;
  /** Input template (supports variable interpolation) */
  inputTemplate?: string;
  /** Output variable name for downstream steps */
  outputVariable?: string;
  /** Condition for execution (for 'conditional' type) */
  condition?: WorkflowStepCondition;
  /** Child steps (for 'parallel', 'sequential', 'loop' types) */
  children?: SystemWorkflowStep[];
  /** True branch (for 'conditional' type) */
  trueBranch?: SystemWorkflowStep[];
  /** False branch (for 'conditional' type) */
  falseBranch?: SystemWorkflowStep[];
  /** Maximum iterations (for 'loop' type) */
  maxIterations?: number;
  /** Timeout in milliseconds */
  timeout?: number;
  /** Whether this step can be skipped on error */
  optional?: boolean;
  /** Retry configuration */
  retry?: {
    maxAttempts: number;
    delayMs: number;
    backoffMultiplier?: number;
  };
  /** Position for visualization */
  position?: { x: number; y: number };
}

/**
 * System - A multi-agent system configuration
 *
 * Systems are stored in team storage and define how multiple agents
 * work together to accomplish complex tasks.
 */
export interface System {
  /** Unique identifier */
  id: string;
  /** Display name */
  name: string;
  /** Description of what this system does */
  description: string;
  /** Current status */
  status: SystemStatus;
  /** Agents involved in this system */
  agents: SystemAgent[];
  /** Workflow definition */
  workflow: SystemWorkflowStep[];
  /** Default input schema (JSON Schema) */
  inputSchema?: Record<string, unknown>;
  /** Default output schema (JSON Schema) */
  outputSchema?: Record<string, unknown>;
  /** System-level variables and configuration */
  variables?: Record<string, unknown>;
  /** Category for organization */
  category?: string;
  /** Tags for categorization */
  tags?: string[];
  /** Icon identifier (Lucide icon name) */
  icon?: string;
  /** Cover image path for gallery display */
  coverImage?: string;
  /** Whether this is a built-in system */
  isBuiltIn?: boolean;
  /** ISO timestamp of creation */
  createdAt: string;
  /** ISO timestamp of last update */
  updatedAt: string;
  /** User ID of creator (for multi-user support) */
  createdBy?: string;
}

/**
 * SystemStepExecution - Execution record for a single workflow step
 */
export interface SystemStepExecution {
  /** Step ID */
  stepId: string;
  /** Step name */
  stepName: string;
  /** Execution status */
  status: SystemExecutionStatus;
  /** Input provided to this step */
  input?: string;
  /** Output from this step */
  output?: string;
  /** Error message (if failed) */
  error?: string;
  /** ISO timestamp of start */
  startedAt: string;
  /** ISO timestamp of completion */
  completedAt?: string;
  /** Token usage for this step */
  tokenUsage?: {
    inputTokens: number;
    outputTokens: number;
  };
}

/**
 * SystemExecution - Record of a system execution
 */
export interface SystemExecution {
  /** Unique execution ID */
  id: string;
  /** ID of the system that was executed */
  systemId: string;
  /** Overall execution status */
  status: SystemExecutionStatus;
  /** Input provided to the system */
  input: string;
  /** Final output from the system */
  output?: string;
  /** Error message (if failed) */
  error?: string;
  /** Execution records for each step */
  steps: SystemStepExecution[];
  /** Total token usage */
  totalTokenUsage?: {
    inputTokens: number;
    outputTokens: number;
  };
  /** ISO timestamp of start */
  startedAt: string;
  /** ISO timestamp of completion */
  completedAt?: string;
}

/**
 * CreateSystemInput - Input for creating a new system
 */
export interface CreateSystemInput {
  name: string;
  description: string;
  agents?: SystemAgent[];
  workflow?: SystemWorkflowStep[];
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  variables?: Record<string, unknown>;
  category?: string;
  tags?: string[];
  icon?: string;
  coverImage?: string;
}

/**
 * UpdateSystemInput - Input for updating an existing system
 */
export interface UpdateSystemInput {
  name?: string;
  description?: string;
  status?: SystemStatus;
  agents?: SystemAgent[];
  workflow?: SystemWorkflowStep[];
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  variables?: Record<string, unknown>;
  category?: string;
  tags?: string[];
  icon?: string;
  coverImage?: string;
}

/**
 * RunSystemInput - Input for running a system
 */
export interface RunSystemInput {
  /** System ID to run */
  systemId: string;
  /** Input for the system */
  input: string;
  /** Variable overrides */
  variables?: Record<string, unknown>;
  /** Project path context (optional) */
  projectPath?: string;
}

/**
 * BuiltInSystemId - Identifiers for built-in systems
 */
export type BuiltInSystemId =
  | 'research-system'
  | 'code-review-system'
  | 'feature-planning-system'
  | 'bug-investigation-system';
