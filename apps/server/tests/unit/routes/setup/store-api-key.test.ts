import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { Request, Response } from 'express';
import fs from 'fs/promises';
import os from 'os';
import path from 'path';
import { createStoreApiKeyHandler } from '@/routes/setup/routes/store-api-key.js';
import { createMockExpressContext } from '../../../utils/mocks.js';
import { getApiKey, setApiKey } from '@/routes/setup/common.js';

let dataDir: string | null = '';
let previousDataDir: string | undefined;

vi.mock('@automaker/platform', async () => {
  const actual = await vi.importActual<typeof import('@automaker/platform')>('@automaker/platform');
  return {
    ...actual,
    getDataDirectory: vi.fn(() => dataDir),
  };
});

describe('store-api-key route', () => {
  let req: Request;
  let res: Response;

  beforeEach(async () => {
    const context = createMockExpressContext();
    req = context.req;
    res = context.res;

    previousDataDir = process.env.DATA_DIR;
    dataDir = await fs.mkdtemp(path.join(os.tmpdir(), 'automaker-store-api-key-'));

    setApiKey('google', '');
    setApiKey('anthropic_oauth_token', '');
    setApiKey('anthropic', '');
    delete process.env.GOOGLE_API_KEY;
    delete process.env.ANTHROPIC_AUTH_TOKEN;
    delete process.env.ANTHROPIC_API_KEY;
  });

  afterEach(async () => {
    if (dataDir) {
      await fs.rm(dataDir, { recursive: true, force: true });
    }
    dataDir = '';
    if (previousDataDir === undefined) {
      delete process.env.DATA_DIR;
    } else {
      process.env.DATA_DIR = previousDataDir;
    }
  });

  it('persists google api key to credentials.json and env', async () => {
    req.body = { provider: 'google', apiKey: 'google-key' };

    const handler = createStoreApiKeyHandler();
    await handler(req, res);

    expect(res.json).toHaveBeenCalledWith({ success: true, active: true });

    const saved = JSON.parse(await fs.readFile(path.join(dataDir!, 'credentials.json'), 'utf-8'));
    expect(saved.apiKeys.google).toBe('google-key');
    expect(getApiKey('google')).toBe('google-key');
    expect(process.env.GOOGLE_API_KEY).toBe('google-key');
  });

  it('persists anthropic oauth token to credentials.json and env', async () => {
    req.body = { provider: 'anthropic_oauth_token', apiKey: 'oauth-token' };

    const handler = createStoreApiKeyHandler();
    await handler(req, res);

    expect(res.json).toHaveBeenCalledWith({ success: true, active: true });

    const saved = JSON.parse(await fs.readFile(path.join(dataDir!, 'credentials.json'), 'utf-8'));
    expect(saved.apiKeys.anthropic_oauth_token).toBe('oauth-token');
    expect(getApiKey('anthropic_oauth_token')).toBe('oauth-token');
    expect(process.env.ANTHROPIC_AUTH_TOKEN).toBe('oauth-token');
  });

  it('persists api key when getDataDirectory is unset but DATA_DIR env is set', async () => {
    const fallbackDir = await fs.mkdtemp(path.join(os.tmpdir(), 'automaker-store-api-key-env-'));
    dataDir = null;
    process.env.DATA_DIR = fallbackDir;

    req.body = { provider: 'google', apiKey: 'google-env-key' };

    const handler = createStoreApiKeyHandler();
    await handler(req, res);

    expect(res.json).toHaveBeenCalledWith({ success: true, active: true });

    const saved = JSON.parse(
      await fs.readFile(path.join(fallbackDir, 'credentials.json'), 'utf-8')
    );
    expect(saved.apiKeys.google).toBe('google-env-key');

    await fs.rm(fallbackDir, { recursive: true, force: true });
  });

  it('returns 400 for unsupported provider', async () => {
    req.body = { provider: 'unknown-provider', apiKey: 'test-key' };

    const handler = createStoreApiKeyHandler();
    await handler(req, res);

    expect(res.status).toHaveBeenCalledWith(400);
    expect(res.json).toHaveBeenCalledWith({
      success: false,
      error: expect.stringContaining('Unsupported provider'),
    });
  });

  it('returns 400 when provider is missing', async () => {
    req.body = { apiKey: 'test-key' };

    const handler = createStoreApiKeyHandler();
    await handler(req, res);

    expect(res.status).toHaveBeenCalledWith(400);
    expect(res.json).toHaveBeenCalledWith({
      success: false,
      error: 'provider and apiKey required',
    });
  });

  it('returns 400 when apiKey is missing', async () => {
    req.body = { provider: 'anthropic' };

    const handler = createStoreApiKeyHandler();
    await handler(req, res);

    expect(res.status).toHaveBeenCalledWith(400);
    expect(res.json).toHaveBeenCalledWith({
      success: false,
      error: 'provider and apiKey required',
    });
  });

  it('stores key in memory only after persistence succeeds', async () => {
    // Clear any existing key
    setApiKey('google', '');

    req.body = { provider: 'google', apiKey: 'test-key' };

    const handler = createStoreApiKeyHandler();
    await handler(req, res);

    // Verify key was stored in memory after successful persistence
    expect(res.json).toHaveBeenCalledWith({ success: true, active: true });
    expect(getApiKey('google')).toBe('test-key');
  });

  it('stores key inactive when makeActive is false', async () => {
    req.body = { provider: 'google', apiKey: 'inactive-key', makeActive: false };

    const handler = createStoreApiKeyHandler();
    await handler(req, res);

    expect(res.json).toHaveBeenCalledWith({ success: true, active: false });

    // Key should be in memory cache
    expect(getApiKey('google')).toBe('inactive-key');

    // Key should NOT be in process.env
    expect(process.env.GOOGLE_API_KEY).toBeUndefined();
  });
});
