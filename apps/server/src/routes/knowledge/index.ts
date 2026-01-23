/**
 * Knowledge routes - HTTP API for Knowledge Hub management
 */

import { Router } from 'express';
import { createLogger } from '@automaker/utils';
import { KnowledgeService } from '../../services/knowledge-service.js';
import { TeamStorageService, InvalidTeamStoragePathError } from '../../lib/team-storage.js';
import type { Request, Response } from 'express';
import type {
  CreateBlueprintInput,
  UpdateBlueprintInput,
  CreateKnowledgeEntryInput,
  UpdateKnowledgeEntryInput,
  CreateLearningInput,
  UpdateLearningInput,
  KnowledgeSearchQuery,
} from '@automaker/types';

const logger = createLogger('KnowledgeRoutes');

function handleInvalidTeamStoragePath(error: unknown, res: Response): boolean {
  if (error instanceof InvalidTeamStoragePathError) {
    res.status(400).json({
      success: false,
      error: error.message,
    });
    return true;
  }
  return false;
}

export function createKnowledgeRoutes(teamStorage: TeamStorageService): Router {
  const router = Router();
  const service = new KnowledgeService(teamStorage);

  // ============================================================================
  // Stats
  // ============================================================================

  /**
   * GET /api/knowledge/stats
   * Get counts for all knowledge types
   */
  router.get('/stats', async (_req: Request, res: Response) => {
    try {
      const counts = await service.getCounts();
      res.json({ success: true, counts });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to get knowledge stats:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  // ============================================================================
  // Search
  // ============================================================================

  /**
   * POST /api/knowledge/search
   * Search across all knowledge types
   */
  router.post('/search', async (req: Request, res: Response) => {
    try {
      const query: KnowledgeSearchQuery = req.body;

      if (!query.query) {
        return res.status(400).json({
          success: false,
          error: 'Missing required field: query',
        });
      }

      const results = await service.search(query);
      res.json({ success: true, results });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to search knowledge:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  // ============================================================================
  // Blueprints
  // ============================================================================

  /**
   * GET /api/knowledge/blueprints
   * List all blueprints
   */
  router.get('/blueprints', async (req: Request, res: Response) => {
    try {
      const category = req.query.category as string | undefined;
      const status = req.query.status as string | undefined;
      const blueprints = await service.listBlueprints({ category, status });
      res.json({ success: true, blueprints });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to list blueprints:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * GET /api/knowledge/blueprints/:blueprintId
   * Get a single blueprint
   */
  router.get('/blueprints/:blueprintId', async (req: Request, res: Response) => {
    try {
      const { blueprintId } = req.params;
      const blueprint = await service.getBlueprint(blueprintId);

      if (!blueprint) {
        return res.status(404).json({
          success: false,
          error: 'Blueprint not found',
        });
      }

      res.json({ success: true, blueprint });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to get blueprint:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * POST /api/knowledge/blueprints
   * Create a new blueprint
   */
  router.post('/blueprints', async (req: Request, res: Response) => {
    try {
      const input: CreateBlueprintInput = req.body;

      if (!input.name || !input.description || !input.content || !input.category) {
        return res.status(400).json({
          success: false,
          error: 'Missing required fields: name, description, content, category',
        });
      }

      const blueprint = await service.createBlueprint(input);
      res.status(201).json({ success: true, blueprint });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to create blueprint:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * PUT /api/knowledge/blueprints/:blueprintId
   * Update a blueprint
   */
  router.put('/blueprints/:blueprintId', async (req: Request, res: Response) => {
    try {
      const { blueprintId } = req.params;
      const input: UpdateBlueprintInput = req.body;

      const blueprint = await service.updateBlueprint(blueprintId, input);

      if (!blueprint) {
        return res.status(404).json({
          success: false,
          error: 'Blueprint not found',
        });
      }

      res.json({ success: true, blueprint });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to update blueprint:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * DELETE /api/knowledge/blueprints/:blueprintId
   * Delete a blueprint
   */
  router.delete('/blueprints/:blueprintId', async (req: Request, res: Response) => {
    try {
      const { blueprintId } = req.params;
      const deleted = await service.deleteBlueprint(blueprintId);

      if (!deleted) {
        return res.status(404).json({
          success: false,
          error: 'Blueprint not found',
        });
      }

      res.json({ success: true });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to delete blueprint:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  // ============================================================================
  // Knowledge Entries
  // ============================================================================

  /**
   * GET /api/knowledge/entries
   * List all knowledge entries
   */
  router.get('/entries', async (req: Request, res: Response) => {
    try {
      const type = req.query.type as string | undefined;
      const entries = await service.listKnowledgeEntries({ type });
      res.json({ success: true, entries });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to list knowledge entries:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * GET /api/knowledge/entries/:entryId
   * Get a single knowledge entry
   */
  router.get('/entries/:entryId', async (req: Request, res: Response) => {
    try {
      const { entryId } = req.params;
      const entry = await service.getKnowledgeEntry(entryId);

      if (!entry) {
        return res.status(404).json({
          success: false,
          error: 'Knowledge entry not found',
        });
      }

      res.json({ success: true, entry });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to get knowledge entry:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * POST /api/knowledge/entries
   * Create a new knowledge entry
   */
  router.post('/entries', async (req: Request, res: Response) => {
    try {
      const input: CreateKnowledgeEntryInput = req.body;

      if (!input.title || !input.description || !input.content || !input.type) {
        return res.status(400).json({
          success: false,
          error: 'Missing required fields: title, description, content, type',
        });
      }

      const entry = await service.createKnowledgeEntry(input);
      res.status(201).json({ success: true, entry });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to create knowledge entry:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * PUT /api/knowledge/entries/:entryId
   * Update a knowledge entry
   */
  router.put('/entries/:entryId', async (req: Request, res: Response) => {
    try {
      const { entryId } = req.params;
      const input: UpdateKnowledgeEntryInput = req.body;

      const entry = await service.updateKnowledgeEntry(entryId, input);

      if (!entry) {
        return res.status(404).json({
          success: false,
          error: 'Knowledge entry not found',
        });
      }

      res.json({ success: true, entry });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to update knowledge entry:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * DELETE /api/knowledge/entries/:entryId
   * Delete a knowledge entry
   */
  router.delete('/entries/:entryId', async (req: Request, res: Response) => {
    try {
      const { entryId } = req.params;
      const deleted = await service.deleteKnowledgeEntry(entryId);

      if (!deleted) {
        return res.status(404).json({
          success: false,
          error: 'Knowledge entry not found',
        });
      }

      res.json({ success: true });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to delete knowledge entry:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  // ============================================================================
  // Learnings
  // ============================================================================

  /**
   * GET /api/knowledge/learnings
   * List all learnings
   */
  router.get('/learnings', async (req: Request, res: Response) => {
    try {
      const type = req.query.type as string | undefined;
      const confidence = req.query.confidence as string | undefined;
      const learnings = await service.listLearnings({ type, confidence });
      res.json({ success: true, learnings });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to list learnings:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * GET /api/knowledge/learnings/:learningId
   * Get a single learning
   */
  router.get('/learnings/:learningId', async (req: Request, res: Response) => {
    try {
      const { learningId } = req.params;
      const learning = await service.getLearning(learningId);

      if (!learning) {
        return res.status(404).json({
          success: false,
          error: 'Learning not found',
        });
      }

      res.json({ success: true, learning });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to get learning:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * POST /api/knowledge/learnings
   * Create a new learning
   */
  router.post('/learnings', async (req: Request, res: Response) => {
    try {
      const input: CreateLearningInput = req.body;

      if (!input.title || !input.description || !input.content || !input.type) {
        return res.status(400).json({
          success: false,
          error: 'Missing required fields: title, description, content, type',
        });
      }

      const learning = await service.createLearning(input);
      res.status(201).json({ success: true, learning });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to create learning:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * PUT /api/knowledge/learnings/:learningId
   * Update a learning
   */
  router.put('/learnings/:learningId', async (req: Request, res: Response) => {
    try {
      const { learningId } = req.params;
      const input: UpdateLearningInput = req.body;

      const learning = await service.updateLearning(learningId, input);

      if (!learning) {
        return res.status(404).json({
          success: false,
          error: 'Learning not found',
        });
      }

      res.json({ success: true, learning });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to update learning:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * DELETE /api/knowledge/learnings/:learningId
   * Delete a learning
   */
  router.delete('/learnings/:learningId', async (req: Request, res: Response) => {
    try {
      const { learningId } = req.params;
      const deleted = await service.deleteLearning(learningId);

      if (!deleted) {
        return res.status(404).json({
          success: false,
          error: 'Learning not found',
        });
      }

      res.json({ success: true });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to delete learning:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * POST /api/knowledge/learnings/:learningId/apply
   * Record that a learning was applied
   */
  router.post('/learnings/:learningId/apply', async (req: Request, res: Response) => {
    try {
      const { learningId } = req.params;
      const { success } = req.body as { success: boolean };

      const learning = await service.incrementLearningApplication(learningId, success);

      if (!learning) {
        return res.status(404).json({
          success: false,
          error: 'Learning not found',
        });
      }

      res.json({ success: true, learning });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to apply learning:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  return router;
}
