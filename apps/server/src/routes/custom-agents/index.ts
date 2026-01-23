/**
 * Custom Agents routes - HTTP API for custom agent management
 */

import { Router } from 'express';
import { createLogger } from '@automaker/utils';
import { CustomAgentsService } from '../../services/custom-agents-service.js';
import { TeamStorageService, InvalidTeamStoragePathError } from '../../lib/team-storage.js';
import type { Request, Response } from 'express';
import type { CreateCustomAgentInput, UpdateCustomAgentInput } from '@automaker/types';

const logger = createLogger('CustomAgentsRoutes');

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

export function createCustomAgentsRoutes(teamStorage: TeamStorageService): Router {
  const router = Router();
  const service = new CustomAgentsService(teamStorage);

  /**
   * GET /api/custom-agents/stats/counts
   * Get agent counts by status
   * NOTE: This route MUST be defined before /:agentId to avoid matching "stats" as an agentId
   */
  router.get('/stats/counts', async (_req: Request, res: Response) => {
    try {
      const counts = await service.countByStatus();
      res.json({ success: true, counts });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to get agent counts:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * GET /api/custom-agents
   * List all custom agents
   */
  router.get('/', async (req: Request, res: Response) => {
    try {
      const status = req.query.status as string | undefined;
      const agents = await service.list({ status });
      res.json({ success: true, agents });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to list agents:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * GET /api/custom-agents/:agentId
   * Get a single agent
   */
  router.get('/:agentId', async (req: Request, res: Response) => {
    try {
      const { agentId } = req.params;
      const agent = await service.get(agentId);

      if (!agent) {
        return res.status(404).json({
          success: false,
          error: 'Agent not found',
        });
      }

      res.json({ success: true, agent });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to get agent:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * POST /api/custom-agents
   * Create a new agent
   */
  router.post('/', async (req: Request, res: Response) => {
    try {
      const input: CreateCustomAgentInput = req.body;

      if (!input.name || !input.description || !input.systemPrompt || !input.modelConfig) {
        return res.status(400).json({
          success: false,
          error: 'Missing required fields: name, description, systemPrompt, modelConfig',
        });
      }

      const agent = await service.create(input);
      res.status(201).json({ success: true, agent });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to create agent:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * PUT /api/custom-agents/:agentId
   * Update an agent
   */
  router.put('/:agentId', async (req: Request, res: Response) => {
    try {
      const { agentId } = req.params;
      const input: UpdateCustomAgentInput = req.body;

      const agent = await service.update(agentId, input);

      if (!agent) {
        return res.status(404).json({
          success: false,
          error: 'Agent not found',
        });
      }

      res.json({ success: true, agent });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to update agent:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * DELETE /api/custom-agents/:agentId
   * Delete an agent
   */
  router.delete('/:agentId', async (req: Request, res: Response) => {
    try {
      const { agentId } = req.params;
      const deleted = await service.delete(agentId);

      if (!deleted) {
        return res.status(404).json({
          success: false,
          error: 'Agent not found',
        });
      }

      res.json({ success: true });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to delete agent:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * POST /api/custom-agents/:agentId/duplicate
   * Duplicate an agent
   */
  router.post('/:agentId/duplicate', async (req: Request, res: Response) => {
    try {
      const { agentId } = req.params;
      const agent = await service.duplicate(agentId);

      if (!agent) {
        return res.status(404).json({
          success: false,
          error: 'Agent not found',
        });
      }

      res.status(201).json({ success: true, agent });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to duplicate agent:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * POST /api/custom-agents/:agentId/toggle-archive
   * Archive or restore an agent
   */
  router.post('/:agentId/toggle-archive', async (req: Request, res: Response) => {
    try {
      const { agentId } = req.params;
      const agent = await service.toggleArchive(agentId);

      if (!agent) {
        return res.status(404).json({
          success: false,
          error: 'Agent not found',
        });
      }

      res.json({ success: true, agent });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to toggle archive:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * POST /api/custom-agents/:agentId/activate
   * Activate a draft agent
   */
  router.post('/:agentId/activate', async (req: Request, res: Response) => {
    try {
      const { agentId } = req.params;
      const agent = await service.activate(agentId);

      if (!agent) {
        return res.status(404).json({
          success: false,
          error: 'Agent not found or not in draft status',
        });
      }

      res.json({ success: true, agent });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to activate agent:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  return router;
}
