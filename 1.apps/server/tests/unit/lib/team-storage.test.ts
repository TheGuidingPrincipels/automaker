import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as path from 'path';
import * as os from 'os';
import { mkdtemp, rm } from 'fs/promises';
import { TeamStorageService } from '../../../src/lib/team-storage.js';

describe('TeamStorageService', () => {
  let tempDir: string;
  let teamDataDir: string;
  let storage: TeamStorageService;

  beforeEach(async () => {
    tempDir = await mkdtemp(path.join(os.tmpdir(), 'automaker-team-storage-'));
    teamDataDir = path.join(tempDir, 'team');
    storage = new TeamStorageService({ type: 'file', path: teamDataDir });
    await storage.initialize();
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it('rejects path traversal in entity IDs', async () => {
    await expect(
      storage.create('agents', {
        id: '../../outside',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      })
    ).rejects.toThrow();
  });

  it('rejects path traversal in filenames', async () => {
    await expect(
      storage.saveFile('agents', 'safe-id', '../../../pwned.txt', 'pwned')
    ).rejects.toThrow();
  });
});
