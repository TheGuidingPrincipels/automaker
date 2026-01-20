/**
 * Custom Agents Service - Business logic for custom agent management
 *
 * Handles CRUD operations for custom agents stored in team storage.
 */

import { createLogger } from '@automaker/utils';
import { TeamStorageService } from '../lib/team-storage.js';
import type { CustomAgent, CreateCustomAgentInput, UpdateCustomAgentInput } from '@automaker/types';

const logger = createLogger('CustomAgentsService');

/**
 * Generate a unique agent ID
 */
function generateAgentId(): string {
  return `agent-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * CustomAgentsService - Manages custom agent configurations
 */
export class CustomAgentsService {
  constructor(private teamStorage: TeamStorageService) {}

  /**
   * List all custom agents
   */
  async list(filters?: { status?: string }): Promise<CustomAgent[]> {
    const agents = await this.teamStorage.list<CustomAgent>('agents', {
      filters: filters?.status ? { status: filters.status } : undefined,
      sortBy: 'updatedAt',
      sortDirection: 'desc',
    });
    return agents;
  }

  /**
   * Get a single agent by ID
   */
  async get(agentId: string): Promise<CustomAgent | null> {
    return this.teamStorage.get<CustomAgent>('agents', agentId);
  }

  /**
   * Create a new custom agent
   */
  async create(input: CreateCustomAgentInput, createdBy?: string): Promise<CustomAgent> {
    const agent: CustomAgent = {
      id: generateAgentId(),
      name: input.name,
      description: input.description,
      systemPrompt: input.systemPrompt,
      status: 'draft',
      modelConfig: input.modelConfig,
      tools: input.tools || [],
      mcpServers: input.mcpServers || [],
      customMcpServers: input.customMcpServers,
      icon: input.icon,
      tags: input.tags,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      createdBy,
    };

    const created = await this.teamStorage.create<CustomAgent>('agents', agent);
    logger.info(`Created custom agent: ${created.id} (${created.name})`);
    return created;
  }

  /**
   * Update an existing agent
   */
  async update(agentId: string, input: UpdateCustomAgentInput): Promise<CustomAgent | null> {
    const existing = await this.get(agentId);
    if (!existing) {
      return null;
    }

    const updates: Partial<CustomAgent> = {
      ...input,
      updatedAt: new Date().toISOString(),
    };

    const updated = await this.teamStorage.update<CustomAgent>('agents', agentId, updates);
    if (updated) {
      logger.info(`Updated custom agent: ${agentId}`);
    }
    return updated;
  }

  /**
   * Delete an agent
   */
  async delete(agentId: string): Promise<boolean> {
    const deleted = await this.teamStorage.delete('agents', agentId);
    if (deleted) {
      logger.info(`Deleted custom agent: ${agentId}`);
    }
    return deleted;
  }

  /**
   * Duplicate an agent
   */
  async duplicate(agentId: string): Promise<CustomAgent | null> {
    const existing = await this.get(agentId);
    if (!existing) {
      return null;
    }

    const duplicateInput: CreateCustomAgentInput = {
      name: `${existing.name} (Copy)`,
      description: existing.description,
      systemPrompt: existing.systemPrompt,
      modelConfig: existing.modelConfig,
      tools: existing.tools,
      mcpServers: existing.mcpServers,
      customMcpServers: existing.customMcpServers,
      icon: existing.icon,
      tags: existing.tags,
    };

    return this.create(duplicateInput, existing.createdBy);
  }

  /**
   * Archive or restore an agent
   */
  async toggleArchive(agentId: string): Promise<CustomAgent | null> {
    const existing = await this.get(agentId);
    if (!existing) {
      return null;
    }

    const newStatus = existing.status === 'archived' ? 'active' : 'archived';
    return this.update(agentId, { status: newStatus });
  }

  /**
   * Activate a draft agent
   */
  async activate(agentId: string): Promise<CustomAgent | null> {
    const existing = await this.get(agentId);
    if (!existing || existing.status !== 'draft') {
      return null;
    }

    return this.update(agentId, { status: 'active' });
  }

  /**
   * Count agents by status
   */
  async countByStatus(): Promise<Record<string, number>> {
    const agents = await this.list();
    const counts: Record<string, number> = {
      draft: 0,
      active: 0,
      archived: 0,
      total: agents.length,
    };

    for (const agent of agents) {
      counts[agent.status] = (counts[agent.status] || 0) + 1;
    }

    return counts;
  }
}
