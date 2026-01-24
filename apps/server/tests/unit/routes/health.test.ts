/**
 * Tests for health check endpoints
 *
 * Tests the basic health check (/api/health), environment check (/api/health/environment),
 * and detailed health check (/api/health/detailed) endpoints.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { Request, Response } from 'express';
import { createMockExpressContext } from '../../utils/mocks.js';

// Mock the version module
vi.mock('@/lib/version.js', () => ({
  getVersion: vi.fn(() => '1.2.3'),
}));

// Mock the auth module
vi.mock('@/lib/auth.js', () => ({
  getAuthStatus: vi.fn(() => ({ enabled: true, method: 'api_key_or_session' })),
}));

describe('health routes', () => {
  let req: Request;
  let res: Response;
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    vi.clearAllMocks();
    const context = createMockExpressContext();
    req = context.req;
    res = context.res;

    // Store original environment
    originalEnv = { ...process.env };
  });

  afterEach(() => {
    // Restore original environment
    process.env = originalEnv;
  });

  describe('GET / (basic health check)', () => {
    it('should return ok status with timestamp and version', async () => {
      // Dynamic import to get the mocked version
      const { createIndexHandler } = await import('@/routes/health/routes/index.js');

      const handler = createIndexHandler();
      handler(req, res);

      expect(res.json).toHaveBeenCalledWith({
        status: 'ok',
        timestamp: expect.any(String),
        version: '1.2.3',
      });
    });

    it('should return valid ISO timestamp', async () => {
      const { createIndexHandler } = await import('@/routes/health/routes/index.js');

      const handler = createIndexHandler();
      handler(req, res);

      const response = vi.mocked(res.json).mock.calls[0][0];
      const timestamp = new Date(response.timestamp);
      expect(timestamp.toISOString()).toBe(response.timestamp);
    });

    it('should always return status ok', async () => {
      const { createIndexHandler } = await import('@/routes/health/routes/index.js');

      const handler = createIndexHandler();
      handler(req, res);

      const response = vi.mocked(res.json).mock.calls[0][0];
      expect(response.status).toBe('ok');
    });
  });

  describe('GET /environment', () => {
    it('should return isContainerized as false when not set', async () => {
      delete process.env.IS_CONTAINERIZED;
      delete process.env.AUTOMAKER_SKIP_SANDBOX_WARNING;

      const { createEnvironmentHandler } = await import('@/routes/health/routes/environment.js');

      const handler = createEnvironmentHandler();
      handler(req, res);

      expect(res.json).toHaveBeenCalledWith({
        isContainerized: false,
        skipSandboxWarning: false,
      });
    });

    it('should return isContainerized as true when set', async () => {
      process.env.IS_CONTAINERIZED = 'true';
      delete process.env.AUTOMAKER_SKIP_SANDBOX_WARNING;

      const { createEnvironmentHandler } = await import('@/routes/health/routes/environment.js');

      const handler = createEnvironmentHandler();
      handler(req, res);

      expect(res.json).toHaveBeenCalledWith({
        isContainerized: true,
        skipSandboxWarning: false,
      });
    });

    it('should return skipSandboxWarning as true when set', async () => {
      delete process.env.IS_CONTAINERIZED;
      process.env.AUTOMAKER_SKIP_SANDBOX_WARNING = 'true';

      const { createEnvironmentHandler } = await import('@/routes/health/routes/environment.js');

      const handler = createEnvironmentHandler();
      handler(req, res);

      expect(res.json).toHaveBeenCalledWith({
        isContainerized: false,
        skipSandboxWarning: true,
      });
    });

    it('should return both flags when both are set', async () => {
      process.env.IS_CONTAINERIZED = 'true';
      process.env.AUTOMAKER_SKIP_SANDBOX_WARNING = 'true';

      const { createEnvironmentHandler } = await import('@/routes/health/routes/environment.js');

      const handler = createEnvironmentHandler();
      handler(req, res);

      expect(res.json).toHaveBeenCalledWith({
        isContainerized: true,
        skipSandboxWarning: true,
      });
    });

    it('should treat non-true values as false', async () => {
      process.env.IS_CONTAINERIZED = 'false';
      process.env.AUTOMAKER_SKIP_SANDBOX_WARNING = 'yes';

      const { createEnvironmentHandler } = await import('@/routes/health/routes/environment.js');

      const handler = createEnvironmentHandler();
      handler(req, res);

      expect(res.json).toHaveBeenCalledWith({
        isContainerized: false,
        skipSandboxWarning: false,
      });
    });
  });

  describe('GET /detailed (detailed health check)', () => {
    it('should return detailed health information', async () => {
      process.env.DATA_DIR = '/test/data';

      const { createDetailedHandler } = await import('@/routes/health/routes/detailed.js');

      const handler = createDetailedHandler();
      handler(req, res);

      expect(res.json).toHaveBeenCalledWith({
        status: 'ok',
        timestamp: expect.any(String),
        version: '1.2.3',
        uptime: expect.any(Number),
        memory: expect.objectContaining({
          heapUsed: expect.any(Number),
          heapTotal: expect.any(Number),
          rss: expect.any(Number),
        }),
        dataDir: '/test/data',
        auth: { enabled: true, method: 'api_key_or_session' },
        env: {
          nodeVersion: process.version,
          platform: process.platform,
          arch: process.arch,
        },
      });
    });

    it('should use default data dir when not set', async () => {
      delete process.env.DATA_DIR;

      const { createDetailedHandler } = await import('@/routes/health/routes/detailed.js');

      const handler = createDetailedHandler();
      handler(req, res);

      const response = vi.mocked(res.json).mock.calls[0][0];
      expect(response.dataDir).toBe('./data');
    });

    it('should return valid uptime value', async () => {
      const { createDetailedHandler } = await import('@/routes/health/routes/detailed.js');

      const handler = createDetailedHandler();
      handler(req, res);

      const response = vi.mocked(res.json).mock.calls[0][0];
      expect(response.uptime).toBeGreaterThan(0);
    });

    it('should return memory usage object', async () => {
      const { createDetailedHandler } = await import('@/routes/health/routes/detailed.js');

      const handler = createDetailedHandler();
      handler(req, res);

      const response = vi.mocked(res.json).mock.calls[0][0];
      expect(response.memory).toHaveProperty('rss');
      expect(response.memory).toHaveProperty('heapTotal');
      expect(response.memory).toHaveProperty('heapUsed');
      expect(response.memory).toHaveProperty('external');
      expect(response.memory.rss).toBeGreaterThan(0);
    });

    it('should return correct environment information', async () => {
      const { createDetailedHandler } = await import('@/routes/health/routes/detailed.js');

      const handler = createDetailedHandler();
      handler(req, res);

      const response = vi.mocked(res.json).mock.calls[0][0];
      expect(response.env.nodeVersion).toBe(process.version);
      expect(response.env.platform).toBe(process.platform);
      expect(response.env.arch).toBe(process.arch);
    });

    it('should return auth status from getAuthStatus', async () => {
      const { getAuthStatus } = await import('@/lib/auth.js');
      vi.mocked(getAuthStatus).mockReturnValue({
        enabled: false,
        method: 'disabled',
      });

      const { createDetailedHandler } = await import('@/routes/health/routes/detailed.js');

      const handler = createDetailedHandler();
      handler(req, res);

      const response = vi.mocked(res.json).mock.calls[0][0];
      expect(response.auth).toEqual({ enabled: false, method: 'disabled' });
    });
  });
});
