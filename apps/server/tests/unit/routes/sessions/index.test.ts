/**
 * Tests for /api/sessions endpoint
 *
 * Tests the session management REST API endpoints:
 * - GET /api/sessions - List all sessions
 * - POST /api/sessions - Create a new session
 * - PUT /api/sessions/:sessionId - Update a session
 * - POST /api/sessions/:sessionId/archive - Archive a session
 * - POST /api/sessions/:sessionId/unarchive - Unarchive a session
 * - DELETE /api/sessions/:sessionId - Delete a session
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Request, Response } from 'express';
import { createMockExpressContext } from '../../../utils/mocks.js';

// Mock the agent service
const mockAgentService = {
  listSessions: vi.fn(),
  loadSession: vi.fn(),
  createSession: vi.fn(),
  updateSession: vi.fn(),
  archiveSession: vi.fn(),
  unarchiveSession: vi.fn(),
  deleteSession: vi.fn(),
};

// Mock the common module
vi.mock('@/routes/sessions/common.js', () => ({
  getErrorMessage: (error: unknown) => (error instanceof Error ? error.message : 'Unknown error'),
  logError: vi.fn(),
}));

describe('sessions routes', () => {
  let req: Request;
  let res: Response;

  beforeEach(() => {
    vi.clearAllMocks();
    const context = createMockExpressContext();
    req = context.req as unknown as Request;
    res = context.res as unknown as Response;
  });

  describe('GET / (list sessions)', () => {
    it('should return all non-archived sessions by default', async () => {
      const mockSessions = [
        {
          id: 'session-1',
          name: 'Session 1',
          projectPath: '/test/project',
          workingDirectory: '/test/project',
          createdAt: '2024-01-01T00:00:00.000Z',
          updatedAt: '2024-01-02T00:00:00.000Z',
          archived: false,
          tags: ['tag1'],
        },
      ];

      mockAgentService.listSessions.mockResolvedValue(mockSessions);
      mockAgentService.loadSession.mockResolvedValue([{ content: 'Test message content' }]);

      const { createIndexHandler } = await import('@/routes/sessions/routes/index.js');
      const handler = createIndexHandler(mockAgentService as any);
      await handler(req, res);

      expect(mockAgentService.listSessions).toHaveBeenCalledWith(false);
      expect(res.json).toHaveBeenCalledWith({
        success: true,
        sessions: expect.arrayContaining([
          expect.objectContaining({
            id: 'session-1',
            name: 'Session 1',
            isArchived: false,
            tags: ['tag1'],
            messageCount: 1,
            preview: 'Test message content',
          }),
        ]),
      });
    });

    it('should include archived sessions when includeArchived=true', async () => {
      req.query = { includeArchived: 'true' } as any;

      const mockSessions = [
        {
          id: 'session-1',
          name: 'Session 1',
          archived: false,
        },
        {
          id: 'session-2',
          name: 'Archived Session',
          archived: true,
        },
      ];

      mockAgentService.listSessions.mockResolvedValue(mockSessions);
      mockAgentService.loadSession.mockResolvedValue([]);

      const { createIndexHandler } = await import('@/routes/sessions/routes/index.js');
      const handler = createIndexHandler(mockAgentService as any);
      await handler(req, res);

      expect(mockAgentService.listSessions).toHaveBeenCalledWith(true);
    });

    it('should handle errors gracefully', async () => {
      mockAgentService.listSessions.mockRejectedValue(new Error('Database error'));

      const { createIndexHandler } = await import('@/routes/sessions/routes/index.js');
      const handler = createIndexHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Database error',
      });
    });
  });

  describe('POST / (create session)', () => {
    it('should create a new session with required name', async () => {
      req.body = { name: 'New Session', projectPath: '/test/project' };

      const mockSession = {
        id: 'new-session-id',
        name: 'New Session',
        projectPath: '/test/project',
        workingDirectory: '/test/project',
        createdAt: '2024-01-01T00:00:00.000Z',
        updatedAt: '2024-01-01T00:00:00.000Z',
      };

      mockAgentService.createSession.mockResolvedValue(mockSession);

      const { createCreateHandler } = await import('@/routes/sessions/routes/create.js');
      const handler = createCreateHandler(mockAgentService as any);
      await handler(req, res);

      expect(mockAgentService.createSession).toHaveBeenCalledWith(
        'New Session',
        '/test/project',
        undefined,
        undefined
      );
      expect(res.json).toHaveBeenCalledWith({
        success: true,
        session: mockSession,
      });
    });

    it('should return 400 if name is missing', async () => {
      req.body = { projectPath: '/test/project' };

      const { createCreateHandler } = await import('@/routes/sessions/routes/create.js');
      const handler = createCreateHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(400);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'name is required',
      });
    });

    it('should pass workingDirectory and model if provided', async () => {
      req.body = {
        name: 'New Session',
        projectPath: '/test/project',
        workingDirectory: '/test/work',
        model: 'claude-sonnet-4-20250514',
      };

      mockAgentService.createSession.mockResolvedValue({ id: 'session-id' });

      const { createCreateHandler } = await import('@/routes/sessions/routes/create.js');
      const handler = createCreateHandler(mockAgentService as any);
      await handler(req, res);

      expect(mockAgentService.createSession).toHaveBeenCalledWith(
        'New Session',
        '/test/project',
        '/test/work',
        'claude-sonnet-4-20250514'
      );
    });

    it('should handle creation errors', async () => {
      req.body = { name: 'New Session' };
      mockAgentService.createSession.mockRejectedValue(new Error('Creation failed'));

      const { createCreateHandler } = await import('@/routes/sessions/routes/create.js');
      const handler = createCreateHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Creation failed',
      });
    });
  });

  describe('PUT /:sessionId (update session)', () => {
    it('should update session name and tags', async () => {
      req.params = { sessionId: 'session-1' };
      req.body = { name: 'Updated Name', tags: ['tag1', 'tag2'] };

      const mockSession = {
        id: 'session-1',
        name: 'Updated Name',
        tags: ['tag1', 'tag2'],
      };

      mockAgentService.updateSession.mockResolvedValue(mockSession);

      const { createUpdateHandler } = await import('@/routes/sessions/routes/update.js');
      const handler = createUpdateHandler(mockAgentService as any);
      await handler(req, res);

      expect(mockAgentService.updateSession).toHaveBeenCalledWith('session-1', {
        name: 'Updated Name',
        tags: ['tag1', 'tag2'],
        model: undefined,
      });
      expect(res.json).toHaveBeenCalledWith({
        success: true,
        session: mockSession,
      });
    });

    it('should return 404 if session not found', async () => {
      req.params = { sessionId: 'nonexistent' };
      req.body = { name: 'New Name' };

      mockAgentService.updateSession.mockResolvedValue(null);

      const { createUpdateHandler } = await import('@/routes/sessions/routes/update.js');
      const handler = createUpdateHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(404);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Session not found',
      });
    });

    it('should handle update errors', async () => {
      req.params = { sessionId: 'session-1' };
      req.body = { name: 'New Name' };
      mockAgentService.updateSession.mockRejectedValue(new Error('Update failed'));

      const { createUpdateHandler } = await import('@/routes/sessions/routes/update.js');
      const handler = createUpdateHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Update failed',
      });
    });
  });

  describe('POST /:sessionId/archive', () => {
    it('should archive a session', async () => {
      req.params = { sessionId: 'session-1' };
      mockAgentService.archiveSession.mockResolvedValue(true);

      const { createArchiveHandler } = await import('@/routes/sessions/routes/archive.js');
      const handler = createArchiveHandler(mockAgentService as any);
      await handler(req, res);

      expect(mockAgentService.archiveSession).toHaveBeenCalledWith('session-1');
      expect(res.json).toHaveBeenCalledWith({ success: true });
    });

    it('should return 404 if session not found', async () => {
      req.params = { sessionId: 'nonexistent' };
      mockAgentService.archiveSession.mockResolvedValue(false);

      const { createArchiveHandler } = await import('@/routes/sessions/routes/archive.js');
      const handler = createArchiveHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(404);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Session not found',
      });
    });

    it('should handle archive errors', async () => {
      req.params = { sessionId: 'session-1' };
      mockAgentService.archiveSession.mockRejectedValue(new Error('Archive failed'));

      const { createArchiveHandler } = await import('@/routes/sessions/routes/archive.js');
      const handler = createArchiveHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Archive failed',
      });
    });
  });

  describe('POST /:sessionId/unarchive', () => {
    it('should unarchive a session', async () => {
      req.params = { sessionId: 'session-1' };
      mockAgentService.unarchiveSession.mockResolvedValue(true);

      const { createUnarchiveHandler } = await import('@/routes/sessions/routes/unarchive.js');
      const handler = createUnarchiveHandler(mockAgentService as any);
      await handler(req, res);

      expect(mockAgentService.unarchiveSession).toHaveBeenCalledWith('session-1');
      expect(res.json).toHaveBeenCalledWith({ success: true });
    });

    it('should return 404 if session not found', async () => {
      req.params = { sessionId: 'nonexistent' };
      mockAgentService.unarchiveSession.mockResolvedValue(false);

      const { createUnarchiveHandler } = await import('@/routes/sessions/routes/unarchive.js');
      const handler = createUnarchiveHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(404);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Session not found',
      });
    });

    it('should handle unarchive errors', async () => {
      req.params = { sessionId: 'session-1' };
      mockAgentService.unarchiveSession.mockRejectedValue(new Error('Unarchive failed'));

      const { createUnarchiveHandler } = await import('@/routes/sessions/routes/unarchive.js');
      const handler = createUnarchiveHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Unarchive failed',
      });
    });
  });

  describe('DELETE /:sessionId', () => {
    it('should delete a session', async () => {
      req.params = { sessionId: 'session-1' };
      mockAgentService.deleteSession.mockResolvedValue(true);

      const { createDeleteHandler } = await import('@/routes/sessions/routes/delete.js');
      const handler = createDeleteHandler(mockAgentService as any);
      await handler(req, res);

      expect(mockAgentService.deleteSession).toHaveBeenCalledWith('session-1');
      expect(res.json).toHaveBeenCalledWith({ success: true });
    });

    it('should return 404 if session not found', async () => {
      req.params = { sessionId: 'nonexistent' };
      mockAgentService.deleteSession.mockResolvedValue(false);

      const { createDeleteHandler } = await import('@/routes/sessions/routes/delete.js');
      const handler = createDeleteHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(404);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Session not found',
      });
    });

    it('should handle delete errors', async () => {
      req.params = { sessionId: 'session-1' };
      mockAgentService.deleteSession.mockRejectedValue(new Error('Delete failed'));

      const { createDeleteHandler } = await import('@/routes/sessions/routes/delete.js');
      const handler = createDeleteHandler(mockAgentService as any);
      await handler(req, res);

      expect(res.status).toHaveBeenCalledWith(500);
      expect(res.json).toHaveBeenCalledWith({
        success: false,
        error: 'Delete failed',
      });
    });
  });
});
