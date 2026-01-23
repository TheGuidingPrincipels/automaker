/**
 * Systems Service - Business logic for multi-agent system management
 *
 * Handles CRUD operations for systems and system execution.
 */

import { createLogger } from '@automaker/utils';
import { TeamStorageService } from '../lib/team-storage.js';
import type {
  System,
  CreateSystemInput,
  UpdateSystemInput,
  SystemExecution,
  RunSystemInput,
} from '@automaker/types';

const logger = createLogger('SystemsService');

/**
 * Generate a unique system ID
 */
function generateSystemId(): string {
  return `system-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Generate a unique execution ID
 */
function generateExecutionId(): string {
  return `exec-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

// Built-in systems that come with the application
const BUILT_IN_SYSTEMS: System[] = [
  {
    id: 'research-system',
    name: 'Research System',
    description:
      'Multi-agent research and analysis workflow. Coordinates researcher, analyzer, and summarizer agents to investigate topics and produce comprehensive reports.',
    status: 'active',
    agents: [
      {
        id: 'researcher',
        name: 'Researcher',
        role: 'researcher',
        description: 'Gathers information from various sources',
        order: 1,
      },
      {
        id: 'analyzer',
        name: 'Analyzer',
        role: 'analyzer',
        description: 'Analyzes gathered information for insights',
        order: 2,
      },
      {
        id: 'summarizer',
        name: 'Summarizer',
        role: 'custom',
        description: 'Creates comprehensive summary reports',
        order: 3,
      },
    ],
    workflow: [],
    icon: 'FileSearch',
    category: 'Research',
    tags: ['research', 'analysis', 'documentation'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'code-review-system',
    name: 'Code Review System',
    description:
      'Comprehensive code review pipeline. Multiple specialized agents review security, performance, and code quality before generating a unified report.',
    status: 'active',
    agents: [
      {
        id: 'security',
        name: 'Security Reviewer',
        role: 'reviewer',
        description: 'Reviews code for security vulnerabilities',
        order: 1,
      },
      {
        id: 'performance',
        name: 'Performance Analyst',
        role: 'analyzer',
        description: 'Analyzes code for performance issues',
        order: 2,
      },
      {
        id: 'quality',
        name: 'Quality Checker',
        role: 'validator',
        description: 'Validates code quality and standards',
        order: 3,
      },
    ],
    workflow: [],
    icon: 'FileSearch',
    category: 'Development',
    tags: ['review', 'security', 'quality'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'feature-planning-system',
    name: 'Feature Planning System',
    description:
      'End-to-end feature planning workflow. Takes requirements and produces technical specifications, task breakdowns, and implementation plans.',
    status: 'active',
    agents: [
      {
        id: 'requirements',
        name: 'Requirements Analyzer',
        role: 'analyzer',
        description: 'Analyzes and clarifies requirements',
        order: 1,
      },
      {
        id: 'architect',
        name: 'Technical Architect',
        role: 'custom',
        description: 'Designs technical architecture',
        order: 2,
      },
      {
        id: 'planner',
        name: 'Task Planner',
        role: 'orchestrator',
        description: 'Breaks down into actionable tasks',
        order: 3,
      },
    ],
    workflow: [],
    icon: 'LayoutList',
    category: 'Planning',
    tags: ['planning', 'architecture', 'requirements'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    id: 'bug-investigation-system',
    name: 'Bug Investigation System',
    description:
      'Automated bug investigation and diagnosis. Reproduces issues, traces root causes, and proposes fixes with test cases.',
    status: 'active',
    agents: [
      {
        id: 'reproducer',
        name: 'Bug Reproducer',
        role: 'custom',
        description: 'Attempts to reproduce the reported bug',
        order: 1,
      },
      {
        id: 'investigator',
        name: 'Root Cause Analyst',
        role: 'analyzer',
        description: 'Investigates the root cause',
        order: 2,
      },
      {
        id: 'fixer',
        name: 'Fix Proposer',
        role: 'implementer',
        description: 'Proposes and implements fixes',
        order: 3,
      },
    ],
    workflow: [],
    icon: 'Bug',
    category: 'Development',
    tags: ['debugging', 'bugfix', 'testing'],
    isBuiltIn: true,
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

/**
 * SystemsService - Manages multi-agent systems
 */
export class SystemsService {
  constructor(private teamStorage: TeamStorageService) {}

  /**
   * List all systems (built-in + custom)
   */
  async list(filters?: { status?: string; category?: string }): Promise<System[]> {
    // Get custom systems from storage
    const customSystems = await this.teamStorage.list<System>('systems', {
      filters: filters?.status ? { status: filters.status } : undefined,
      sortBy: 'updatedAt',
      sortDirection: 'desc',
    });

    // Combine with built-in systems
    let allSystems = [...BUILT_IN_SYSTEMS, ...customSystems];

    // Apply filters
    if (filters?.status) {
      allSystems = allSystems.filter((s) => s.status === filters.status);
    }
    if (filters?.category) {
      allSystems = allSystems.filter((s) => s.category === filters.category);
    }

    return allSystems;
  }

  /**
   * Get a single system by ID
   */
  async get(systemId: string): Promise<System | null> {
    // Check built-in systems first
    const builtIn = BUILT_IN_SYSTEMS.find((s) => s.id === systemId);
    if (builtIn) {
      return builtIn;
    }

    // Then check custom systems
    return this.teamStorage.get<System>('systems', systemId);
  }

  /**
   * Create a new custom system
   */
  async create(input: CreateSystemInput, createdBy?: string): Promise<System> {
    const system: System = {
      id: generateSystemId(),
      name: input.name,
      description: input.description,
      status: 'draft',
      agents: input.agents || [],
      workflow: input.workflow || [],
      inputSchema: input.inputSchema,
      outputSchema: input.outputSchema,
      variables: input.variables,
      category: input.category,
      tags: input.tags,
      icon: input.icon,
      coverImage: input.coverImage,
      isBuiltIn: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      createdBy,
    };

    const created = await this.teamStorage.create<System>('systems', system);
    logger.info(`Created system: ${created.id} (${created.name})`);
    return created;
  }

  /**
   * Update an existing system
   */
  async update(systemId: string, input: UpdateSystemInput): Promise<System | null> {
    // Cannot update built-in systems
    const builtIn = BUILT_IN_SYSTEMS.find((s) => s.id === systemId);
    if (builtIn) {
      logger.warn(`Cannot update built-in system: ${systemId}`);
      return null;
    }

    const existing = await this.teamStorage.get<System>('systems', systemId);
    if (!existing) {
      return null;
    }

    const updates: Partial<System> = {
      ...input,
      updatedAt: new Date().toISOString(),
    };

    const updated = await this.teamStorage.update<System>('systems', systemId, updates);
    if (updated) {
      logger.info(`Updated system: ${systemId}`);
    }
    return updated;
  }

  /**
   * Delete a system
   */
  async delete(systemId: string): Promise<boolean> {
    // Cannot delete built-in systems
    const builtIn = BUILT_IN_SYSTEMS.find((s) => s.id === systemId);
    if (builtIn) {
      logger.warn(`Cannot delete built-in system: ${systemId}`);
      return false;
    }

    const deleted = await this.teamStorage.delete('systems', systemId);
    if (deleted) {
      logger.info(`Deleted system: ${systemId}`);
    }
    return deleted;
  }

  /**
   * Run a system with given input
   */
  async run(input: RunSystemInput): Promise<SystemExecution> {
    const system = await this.get(input.systemId);
    if (!system) {
      throw new Error(`System not found: ${input.systemId}`);
    }

    const execution: SystemExecution = {
      id: generateExecutionId(),
      systemId: input.systemId,
      status: 'running',
      input: input.input,
      steps: [],
      startedAt: new Date().toISOString(),
    };

    logger.info(`Starting system execution: ${execution.id} for system ${input.systemId}`);

    // TODO: Implement actual system execution with agent coordination
    // For now, return a mock execution
    execution.status = 'completed';
    execution.output = `# ${system.name} Output\n\nThis is a placeholder output. Real system execution coming soon.`;
    execution.completedAt = new Date().toISOString();

    return execution;
  }

  /**
   * Get execution status
   */
  async getExecution(executionId: string): Promise<SystemExecution | null> {
    // TODO: Store and retrieve executions from storage
    logger.warn(`Execution lookup not implemented: ${executionId}`);
    return null;
  }

  /**
   * Get unique categories from all systems
   */
  async getCategories(): Promise<string[]> {
    const systems = await this.list();
    const categories = new Set<string>();
    for (const system of systems) {
      if (system.category) {
        categories.add(system.category);
      }
    }
    return Array.from(categories).sort();
  }
}
