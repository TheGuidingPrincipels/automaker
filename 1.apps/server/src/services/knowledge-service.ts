/**
 * Knowledge Service - Business logic for Knowledge Hub management
 *
 * Handles CRUD operations for blueprints, knowledge entries, and learnings.
 */

import { createLogger } from '@automaker/utils';
import { TeamStorageService } from '../lib/team-storage.js';
import type {
  Blueprint,
  KnowledgeEntry,
  Learning,
  CreateBlueprintInput,
  UpdateBlueprintInput,
  CreateKnowledgeEntryInput,
  UpdateKnowledgeEntryInput,
  CreateLearningInput,
  UpdateLearningInput,
  KnowledgeSearchQuery,
  KnowledgeSearchResult,
} from '@automaker/types';

const logger = createLogger('KnowledgeService');

/**
 * Generate unique IDs
 */
function generateBlueprintId(): string {
  return `bp-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

function generateKnowledgeEntryId(): string {
  return `ke-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

function generateLearningId(): string {
  return `learn-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * KnowledgeService - Manages knowledge hub content
 */
export class KnowledgeService {
  constructor(private teamStorage: TeamStorageService) {}

  // ============================================================================
  // Blueprints
  // ============================================================================

  /**
   * List all blueprints
   */
  async listBlueprints(filters?: { category?: string; status?: string }): Promise<Blueprint[]> {
    const blueprints = await this.teamStorage.list<Blueprint>('blueprints', {
      filters: filters?.status ? { status: filters.status } : undefined,
      sortBy: 'priority',
      sortDirection: 'desc',
    });

    if (filters?.category) {
      return blueprints.filter((b) => b.category === filters.category);
    }

    return blueprints;
  }

  /**
   * Get a single blueprint by ID
   */
  async getBlueprint(blueprintId: string): Promise<Blueprint | null> {
    return this.teamStorage.get<Blueprint>('blueprints', blueprintId);
  }

  /**
   * Create a new blueprint
   */
  async createBlueprint(input: CreateBlueprintInput, createdBy?: string): Promise<Blueprint> {
    const blueprint: Blueprint = {
      id: generateBlueprintId(),
      name: input.name,
      description: input.description,
      content: input.content,
      category: input.category,
      status: 'draft',
      tags: input.tags,
      priority: input.priority || 5,
      autoLoadConditions: input.autoLoadConditions,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      createdBy,
    };

    const created = await this.teamStorage.create<Blueprint>('blueprints', blueprint);
    logger.info(`Created blueprint: ${created.id} (${created.name})`);
    return created;
  }

  /**
   * Update a blueprint
   */
  async updateBlueprint(
    blueprintId: string,
    input: UpdateBlueprintInput
  ): Promise<Blueprint | null> {
    const updates: Partial<Blueprint> = {
      ...input,
      updatedAt: new Date().toISOString(),
    };

    const updated = await this.teamStorage.update<Blueprint>('blueprints', blueprintId, updates);
    if (updated) {
      logger.info(`Updated blueprint: ${blueprintId}`);
    }
    return updated;
  }

  /**
   * Delete a blueprint
   */
  async deleteBlueprint(blueprintId: string): Promise<boolean> {
    const deleted = await this.teamStorage.delete('blueprints', blueprintId);
    if (deleted) {
      logger.info(`Deleted blueprint: ${blueprintId}`);
    }
    return deleted;
  }

  // ============================================================================
  // Knowledge Entries
  // ============================================================================

  /**
   * List all knowledge entries
   */
  async listKnowledgeEntries(filters?: { type?: string }): Promise<KnowledgeEntry[]> {
    const entries = await this.teamStorage.list<KnowledgeEntry>('knowledge-entries', {
      sortBy: 'updatedAt',
      sortDirection: 'desc',
    });

    if (filters?.type) {
      return entries.filter((e) => e.type === filters.type);
    }

    return entries;
  }

  /**
   * Get a single knowledge entry by ID
   */
  async getKnowledgeEntry(entryId: string): Promise<KnowledgeEntry | null> {
    return this.teamStorage.get<KnowledgeEntry>('knowledge-entries', entryId);
  }

  /**
   * Create a new knowledge entry
   */
  async createKnowledgeEntry(
    input: CreateKnowledgeEntryInput,
    createdBy?: string
  ): Promise<KnowledgeEntry> {
    const entry: KnowledgeEntry = {
      id: generateKnowledgeEntryId(),
      title: input.title,
      description: input.description,
      content: input.content,
      type: input.type,
      tags: input.tags,
      sourceUrl: input.sourceUrl,
      relatedEntries: input.relatedEntries,
      keywords: input.keywords,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      createdBy,
    };

    const created = await this.teamStorage.create<KnowledgeEntry>('knowledge-entries', entry);
    logger.info(`Created knowledge entry: ${created.id} (${created.title})`);
    return created;
  }

  /**
   * Update a knowledge entry
   */
  async updateKnowledgeEntry(
    entryId: string,
    input: UpdateKnowledgeEntryInput
  ): Promise<KnowledgeEntry | null> {
    const updates: Partial<KnowledgeEntry> = {
      ...input,
      updatedAt: new Date().toISOString(),
    };

    const updated = await this.teamStorage.update<KnowledgeEntry>(
      'knowledge-entries',
      entryId,
      updates
    );
    if (updated) {
      logger.info(`Updated knowledge entry: ${entryId}`);
    }
    return updated;
  }

  /**
   * Delete a knowledge entry
   */
  async deleteKnowledgeEntry(entryId: string): Promise<boolean> {
    const deleted = await this.teamStorage.delete('knowledge-entries', entryId);
    if (deleted) {
      logger.info(`Deleted knowledge entry: ${entryId}`);
    }
    return deleted;
  }

  // ============================================================================
  // Learnings
  // ============================================================================

  /**
   * List all learnings
   */
  async listLearnings(filters?: { type?: string; confidence?: string }): Promise<Learning[]> {
    const learnings = await this.teamStorage.list<Learning>('learnings', {
      sortBy: 'createdAt',
      sortDirection: 'desc',
    });

    let filtered = learnings;
    if (filters?.type) {
      filtered = filtered.filter((l) => l.type === filters.type);
    }
    if (filters?.confidence) {
      filtered = filtered.filter((l) => l.confidence === filters.confidence);
    }

    return filtered;
  }

  /**
   * Get a single learning by ID
   */
  async getLearning(learningId: string): Promise<Learning | null> {
    return this.teamStorage.get<Learning>('learnings', learningId);
  }

  /**
   * Create a new learning
   */
  async createLearning(input: CreateLearningInput, createdBy?: string): Promise<Learning> {
    const learning: Learning = {
      id: generateLearningId(),
      title: input.title,
      description: input.description,
      content: input.content,
      type: input.type,
      confidence: input.confidence || 'medium',
      sourceSessionId: input.sourceSessionId,
      sourceFeatureId: input.sourceFeatureId,
      problem: input.problem,
      solution: input.solution,
      prevention: input.prevention,
      context: input.context,
      tags: input.tags,
      applicationCount: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const created = await this.teamStorage.create<Learning>('learnings', learning);
    logger.info(`Created learning: ${created.id} (${created.title})`);
    return created;
  }

  /**
   * Update a learning
   */
  async updateLearning(learningId: string, input: UpdateLearningInput): Promise<Learning | null> {
    const updates: Partial<Learning> = {
      ...input,
      updatedAt: new Date().toISOString(),
    };

    const updated = await this.teamStorage.update<Learning>('learnings', learningId, updates);
    if (updated) {
      logger.info(`Updated learning: ${learningId}`);
    }
    return updated;
  }

  /**
   * Delete a learning
   */
  async deleteLearning(learningId: string): Promise<boolean> {
    const deleted = await this.teamStorage.delete('learnings', learningId);
    if (deleted) {
      logger.info(`Deleted learning: ${learningId}`);
    }
    return deleted;
  }

  /**
   * Increment the application count for a learning
   */
  async incrementLearningApplication(
    learningId: string,
    success: boolean
  ): Promise<Learning | null> {
    const learning = await this.getLearning(learningId);
    if (!learning) {
      return null;
    }

    const currentCount = learning.applicationCount || 0;
    const currentSuccessRate = learning.successRate || 0;
    const newCount = currentCount + 1;

    // Calculate new success rate
    const successCount = Math.round(currentSuccessRate * currentCount) + (success ? 1 : 0);
    const newSuccessRate = successCount / newCount;

    return this.updateLearning(learningId, {
      applicationCount: newCount,
      successRate: newSuccessRate,
    } as UpdateLearningInput & { applicationCount?: number; successRate?: number });
  }

  // ============================================================================
  // Search
  // ============================================================================

  /**
   * Search across all knowledge types
   */
  async search(query: KnowledgeSearchQuery): Promise<KnowledgeSearchResult[]> {
    const results: KnowledgeSearchResult[] = [];
    const searchText = query.query.toLowerCase();
    const limit = query.limit || 20;

    // Search blueprints
    if (!query.section || query.section === 'blueprints') {
      const blueprints = await this.listBlueprints();
      for (const bp of blueprints) {
        if (
          bp.name.toLowerCase().includes(searchText) ||
          bp.description.toLowerCase().includes(searchText) ||
          bp.content.toLowerCase().includes(searchText) ||
          bp.tags?.some((t) => t.toLowerCase().includes(searchText))
        ) {
          results.push({
            type: 'blueprint',
            id: bp.id,
            title: bp.name,
            description: bp.description,
            score: this.calculateScore(bp, searchText),
            tags: bp.tags,
          });
        }
      }
    }

    // Search knowledge entries
    if (!query.section || query.section === 'knowledge-server') {
      const entries = await this.listKnowledgeEntries();
      for (const entry of entries) {
        if (
          entry.title.toLowerCase().includes(searchText) ||
          entry.description.toLowerCase().includes(searchText) ||
          entry.content.toLowerCase().includes(searchText) ||
          entry.tags?.some((t) => t.toLowerCase().includes(searchText))
        ) {
          results.push({
            type: 'knowledge-entry',
            id: entry.id,
            title: entry.title,
            description: entry.description,
            score: this.calculateScore(entry, searchText),
            tags: entry.tags,
          });
        }
      }
    }

    // Search learnings
    if (!query.section || query.section === 'learning') {
      const learnings = await this.listLearnings();
      for (const learning of learnings) {
        if (
          learning.title.toLowerCase().includes(searchText) ||
          learning.description.toLowerCase().includes(searchText) ||
          learning.content.toLowerCase().includes(searchText) ||
          learning.tags?.some((t) => t.toLowerCase().includes(searchText))
        ) {
          results.push({
            type: 'learning',
            id: learning.id,
            title: learning.title,
            description: learning.description,
            score: this.calculateScore(learning, searchText),
            tags: learning.tags,
          });
        }
      }
    }

    // Sort by score and apply limit
    results.sort((a, b) => b.score - a.score);
    return results.slice(0, limit);
  }

  /**
   * Calculate a simple relevance score
   */
  private calculateScore(
    item: { title?: string; name?: string; description: string; tags?: string[] },
    searchText: string
  ): number {
    let score = 0;
    const title = (item.title || item.name || '').toLowerCase();
    const description = item.description.toLowerCase();

    // Title match is weighted higher
    if (title.includes(searchText)) {
      score += 0.5;
      if (title === searchText) {
        score += 0.3;
      }
    }

    // Description match
    if (description.includes(searchText)) {
      score += 0.2;
    }

    // Tag match
    if (item.tags?.some((t) => t.toLowerCase().includes(searchText))) {
      score += 0.1;
    }

    return score;
  }

  // ============================================================================
  // Stats
  // ============================================================================

  /**
   * Get counts for all knowledge types
   */
  async getCounts(): Promise<{
    blueprints: number;
    knowledgeEntries: number;
    learnings: number;
    total: number;
  }> {
    const [blueprints, entries, learnings] = await Promise.all([
      this.teamStorage.count('blueprints'),
      this.teamStorage.count('knowledge-entries'),
      this.teamStorage.count('learnings'),
    ]);

    return {
      blueprints,
      knowledgeEntries: entries,
      learnings,
      total: blueprints + entries + learnings,
    };
  }
}
