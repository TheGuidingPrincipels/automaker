/**
 * Systems routes - HTTP API for multi-agent system management
 */

import { Router } from 'express';
import { createLogger } from '@automaker/utils';
import { SystemsService } from '../../services/systems-service.js';
import { TeamStorageService, InvalidTeamStoragePathError } from '../../lib/team-storage.js';
import type { Request, Response } from 'express';
import type { CreateSystemInput, UpdateSystemInput, RunSystemInput } from '@automaker/types';

const logger = createLogger('SystemsRoutes');

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

export function createSystemsRoutes(teamStorage: TeamStorageService): Router {
  const router = Router();
  const service = new SystemsService(teamStorage);

  /**
   * GET /api/systems
   * List all systems (built-in + custom)
   */
  router.get('/', async (req: Request, res: Response) => {
    try {
      const status = req.query.status as string | undefined;
      const category = req.query.category as string | undefined;
      const systems = await service.list({ status, category });
      res.json({ success: true, systems });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to list systems:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * GET /api/systems/categories
   * Get list of unique categories
   * NOTE: This route MUST be defined before /:systemId to avoid matching "categories" as a systemId
   */
  router.get('/categories', async (_req: Request, res: Response) => {
    try {
      const categories = await service.getCategories();
      res.json({ success: true, categories });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to get categories:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * GET /api/systems/executions/:executionId
   * Get execution status
   * NOTE: This route MUST be defined before /:systemId to avoid matching "executions" as a systemId
   */
  router.get('/executions/:executionId', async (req: Request, res: Response) => {
    try {
      const { executionId } = req.params;
      const execution = await service.getExecution(executionId);

      if (!execution) {
        return res.status(404).json({
          success: false,
          error: 'Execution not found',
        });
      }

      res.json({ success: true, execution });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to get execution:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * GET /api/systems/:systemId
   * Get a single system
   */
  router.get('/:systemId', async (req: Request, res: Response) => {
    try {
      const { systemId } = req.params;
      const system = await service.get(systemId);

      if (!system) {
        return res.status(404).json({
          success: false,
          error: 'System not found',
        });
      }

      res.json({ success: true, system });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to get system:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * POST /api/systems
   * Create a new system
   */
  router.post('/', async (req: Request, res: Response) => {
    try {
      const input: CreateSystemInput = req.body;

      if (!input.name || !input.description) {
        return res.status(400).json({
          success: false,
          error: 'Missing required fields: name, description',
        });
      }

      const system = await service.create(input);
      res.status(201).json({ success: true, system });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to create system:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * PUT /api/systems/:systemId
   * Update a system
   */
  router.put('/:systemId', async (req: Request, res: Response) => {
    try {
      const { systemId } = req.params;
      const input: UpdateSystemInput = req.body;

      const system = await service.update(systemId, input);

      if (!system) {
        return res.status(404).json({
          success: false,
          error: 'System not found or is a built-in system',
        });
      }

      res.json({ success: true, system });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to update system:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * DELETE /api/systems/:systemId
   * Delete a system
   */
  router.delete('/:systemId', async (req: Request, res: Response) => {
    try {
      const { systemId } = req.params;
      const deleted = await service.delete(systemId);

      if (!deleted) {
        return res.status(404).json({
          success: false,
          error: 'System not found or is a built-in system',
        });
      }

      res.json({ success: true });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to delete system:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  /**
   * POST /api/systems/:systemId/run
   * Run a system with given input
   */
  router.post('/:systemId/run', async (req: Request, res: Response) => {
    try {
      const { systemId } = req.params;
      const { input, variables, projectPath } = req.body as Omit<RunSystemInput, 'systemId'>;

      if (!input) {
        return res.status(400).json({
          success: false,
          error: 'Missing required field: input',
        });
      }

      const execution = await service.run({
        systemId,
        input,
        variables,
        projectPath,
      });

      res.json({ success: true, execution });
    } catch (error) {
      if (handleInvalidTeamStoragePath(error, res)) return;
      logger.error('Failed to run system:', error);
      res.status(500).json({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  });

  return router;
}
