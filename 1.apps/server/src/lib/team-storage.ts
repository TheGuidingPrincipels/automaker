/**
 * Team Storage - Abstraction layer for shared team data storage
 *
 * Provides a unified interface for storing team-shared data like custom agents,
 * systems, and knowledge. Supports file-based storage with a structure designed
 * for future database migration.
 *
 * Storage structure (file-based):
 * TEAM_DATA_DIR/
 * ├── agents/{agentId}/agent.json
 * ├── systems/{systemId}/system.json
 * └── knowledge/
 *     ├── blueprints/{blueprintId}/blueprint.json
 *     ├── entries/{entryId}/entry.json
 *     └── learnings/{learningId}/learning.json
 */

import * as path from 'path';
import { createLogger, atomicWriteJson, DEFAULT_BACKUP_COUNT } from '@automaker/utils';
import * as secureFs from './secure-fs.js';

const logger = createLogger('TeamStorage');

export class InvalidTeamStoragePathError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'InvalidTeamStoragePathError';
  }
}

function assertSafePathSegment(value: string, label: string): void {
  if (value.length === 0) {
    throw new InvalidTeamStoragePathError(`TeamStorage: ${label} is required`);
  }

  if (value.includes('\0')) {
    throw new InvalidTeamStoragePathError(`TeamStorage: ${label} contains a null byte`);
  }

  if (value === '.' || value === '..') {
    throw new InvalidTeamStoragePathError(`TeamStorage: ${label} must be a single path segment`);
  }

  if (value.includes('/') || value.includes('\\')) {
    throw new InvalidTeamStoragePathError(`TeamStorage: ${label} must be a single path segment`);
  }
}

/**
 * Storage type configuration
 */
export interface TeamStorageConfig {
  /** Storage backend type */
  type: 'file' | 'database';
  /** Path for file storage (required for 'file' type) */
  path?: string;
  /** Database connection URL (required for 'database' type) */
  connectionUrl?: string;
}

/**
 * Storage collection types
 */
export type StorageCollection =
  | 'agents'
  | 'systems'
  | 'blueprints'
  | 'knowledge-entries'
  | 'learnings';

/**
 * Base interface for storable entities
 */
export interface StorableEntity {
  id: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * List options for querying collections
 */
export interface ListOptions {
  /** Filter by field values */
  filters?: Record<string, unknown>;
  /** Sort by field */
  sortBy?: string;
  /** Sort direction */
  sortDirection?: 'asc' | 'desc';
  /** Pagination limit */
  limit?: number;
  /** Pagination offset */
  offset?: number;
}

/**
 * Read JSON file with default value fallback
 */
async function readJsonFile<T>(filePath: string, defaultValue: T): Promise<T> {
  try {
    const content = (await secureFs.readFile(filePath, 'utf-8')) as string;
    return JSON.parse(content) as T;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return defaultValue;
    }
    logger.error(`Error reading ${filePath}:`, error);
    return defaultValue;
  }
}

/**
 * Write JSON file atomically
 */
async function writeJsonFile(filePath: string, data: unknown): Promise<void> {
  await atomicWriteJson(filePath, data, { backupCount: DEFAULT_BACKUP_COUNT });
}

/**
 * TeamStorageService - Manages shared team data storage
 *
 * Provides CRUD operations for team-shared resources with a consistent
 * interface that abstracts the underlying storage mechanism.
 */
export class TeamStorageService {
  private config: TeamStorageConfig;
  private basePath: string;
  private resolvedBasePath: string;

  /**
   * Create a new TeamStorageService
   *
   * @param config - Storage configuration
   */
  constructor(config: TeamStorageConfig) {
    this.config = config;

    if (config.type === 'file') {
      if (!config.path) {
        throw new Error('TeamStorage: path is required for file storage');
      }
      this.basePath = config.path;
      this.resolvedBasePath = path.resolve(this.basePath);
    } else {
      // Database support will be added in future
      throw new Error('TeamStorage: database storage not yet implemented');
    }
  }

  private resolveWithinBase(targetPath: string): string {
    const resolvedTargetPath = path.resolve(targetPath);
    const relativePath = path.relative(this.resolvedBasePath, resolvedTargetPath);

    if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
      throw new InvalidTeamStoragePathError('TeamStorage: resolved path escapes base directory');
    }

    return resolvedTargetPath;
  }

  /**
   * Get the storage path for a collection
   */
  private getCollectionPath(collection: StorageCollection): string {
    const collectionMap: Record<StorageCollection, string> = {
      agents: 'agents',
      systems: 'systems',
      blueprints: 'knowledge/blueprints',
      'knowledge-entries': 'knowledge/entries',
      learnings: 'knowledge/learnings',
    };
    return this.resolveWithinBase(path.join(this.basePath, collectionMap[collection]));
  }

  /**
   * Get the file path for an entity
   */
  private getEntityPath(collection: StorageCollection, id: string): string {
    assertSafePathSegment(id, 'id');

    const fileNameMap: Record<StorageCollection, string> = {
      agents: 'agent.json',
      systems: 'system.json',
      blueprints: 'blueprint.json',
      'knowledge-entries': 'entry.json',
      learnings: 'learning.json',
    };
    const entityPath = path.join(this.getCollectionPath(collection), id, fileNameMap[collection]);
    return this.resolveWithinBase(entityPath);
  }

  /**
   * Ensure the storage directory structure exists
   */
  async initialize(): Promise<void> {
    const directories = [
      this.basePath,
      path.join(this.basePath, 'agents'),
      path.join(this.basePath, 'systems'),
      path.join(this.basePath, 'knowledge'),
      path.join(this.basePath, 'knowledge/blueprints'),
      path.join(this.basePath, 'knowledge/entries'),
      path.join(this.basePath, 'knowledge/learnings'),
    ];

    for (const dir of directories) {
      await secureFs.mkdir(dir, { recursive: true });
    }

    logger.info(`TeamStorage initialized at ${this.basePath}`);
  }

  /**
   * List all entities in a collection
   */
  async list<T extends StorableEntity>(
    collection: StorageCollection,
    options?: ListOptions
  ): Promise<T[]> {
    const collectionPath = this.getCollectionPath(collection);

    try {
      const entries = await secureFs.readdir(collectionPath);
      const entities: T[] = [];

      for (const entry of entries) {
        const entityDir = path.join(collectionPath, entry);
        const stat = await secureFs.stat(entityDir);

        if (stat.isDirectory()) {
          try {
            const entity = await this.get<T>(collection, entry);
            if (entity) {
              // Apply filters
              if (options?.filters) {
                let matches = true;
                for (const [key, value] of Object.entries(options.filters)) {
                  if ((entity as Record<string, unknown>)[key] !== value) {
                    matches = false;
                    break;
                  }
                }
                if (!matches) continue;
              }
              entities.push(entity);
            }
          } catch (error) {
            if (error instanceof InvalidTeamStoragePathError) {
              logger.warn(`Skipping invalid team storage entry "${entry}" in ${collection}`);
              continue;
            }
            throw error;
          }
        }
      }

      // Apply sorting
      if (options?.sortBy) {
        const sortKey = options.sortBy;
        const direction = options.sortDirection === 'desc' ? -1 : 1;
        entities.sort((a, b) => {
          const aVal = (a as Record<string, unknown>)[sortKey];
          const bVal = (b as Record<string, unknown>)[sortKey];
          if (aVal === bVal) return 0;
          if (aVal === undefined || aVal === null) return 1;
          if (bVal === undefined || bVal === null) return -1;
          return (aVal as string | number) < (bVal as string | number) ? -direction : direction;
        });
      }

      // Apply pagination
      let result = entities;
      if (options?.offset !== undefined) {
        result = result.slice(options.offset);
      }
      if (options?.limit !== undefined) {
        result = result.slice(0, options.limit);
      }

      return result;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        return [];
      }
      logger.error(`Error listing ${collection}:`, error);
      throw error;
    }
  }

  /**
   * Get a single entity by ID
   */
  async get<T extends StorableEntity>(
    collection: StorageCollection,
    id: string
  ): Promise<T | null> {
    const entityPath = this.getEntityPath(collection, id);

    try {
      const entity = await readJsonFile<T | null>(entityPath, null);
      return entity;
    } catch (error) {
      logger.error(`Error getting ${collection}/${id}:`, error);
      return null;
    }
  }

  /**
   * Create a new entity
   */
  async create<T extends StorableEntity>(collection: StorageCollection, entity: T): Promise<T> {
    const entityPath = this.getEntityPath(collection, entity.id);
    const entityDir = path.dirname(entityPath);

    // Ensure the entity directory exists
    await secureFs.mkdir(entityDir, { recursive: true });

    // Set timestamps
    const now = new Date().toISOString();
    const newEntity = {
      ...entity,
      createdAt: now,
      updatedAt: now,
    };

    await writeJsonFile(entityPath, newEntity);
    logger.debug(`Created ${collection}/${entity.id}`);

    return newEntity;
  }

  /**
   * Update an existing entity
   */
  async update<T extends StorableEntity>(
    collection: StorageCollection,
    id: string,
    updates: Partial<T>
  ): Promise<T | null> {
    const existing = await this.get<T>(collection, id);
    if (!existing) {
      return null;
    }

    const updatedEntity = {
      ...existing,
      ...updates,
      id, // Preserve original ID
      createdAt: existing.createdAt, // Preserve creation timestamp
      updatedAt: new Date().toISOString(),
    };

    const entityPath = this.getEntityPath(collection, id);
    await writeJsonFile(entityPath, updatedEntity);
    logger.debug(`Updated ${collection}/${id}`);

    return updatedEntity;
  }

  /**
   * Delete an entity
   */
  async delete(collection: StorageCollection, id: string): Promise<boolean> {
    const entityDir = path.dirname(this.getEntityPath(collection, id));

    try {
      await secureFs.rm(entityDir, { recursive: true });
      logger.debug(`Deleted ${collection}/${id}`);
      return true;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        return false;
      }
      logger.error(`Error deleting ${collection}/${id}:`, error);
      throw error;
    }
  }

  /**
   * Check if an entity exists
   */
  async exists(collection: StorageCollection, id: string): Promise<boolean> {
    const entityPath = this.getEntityPath(collection, id);
    try {
      await secureFs.access(entityPath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Count entities in a collection
   */
  async count(collection: StorageCollection, filters?: Record<string, unknown>): Promise<number> {
    const entities = await this.list(collection, { filters });
    return entities.length;
  }

  /**
   * Save additional files for an entity (e.g., images, attachments)
   */
  async saveFile(
    collection: StorageCollection,
    id: string,
    fileName: string,
    content: Buffer | string
  ): Promise<string> {
    assertSafePathSegment(fileName, 'fileName');
    const entityDir = path.dirname(this.getEntityPath(collection, id));
    const filePath = this.resolveWithinBase(path.join(entityDir, fileName));

    await secureFs.mkdir(entityDir, { recursive: true });
    await secureFs.writeFile(filePath, content);

    return filePath;
  }

  /**
   * Read an additional file for an entity
   */
  async readFile(
    collection: StorageCollection,
    id: string,
    fileName: string
  ): Promise<Buffer | null> {
    assertSafePathSegment(fileName, 'fileName');
    const entityDir = path.dirname(this.getEntityPath(collection, id));
    const filePath = this.resolveWithinBase(path.join(entityDir, fileName));

    try {
      const content = await secureFs.readFile(filePath);
      return content as Buffer;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        return null;
      }
      throw error;
    }
  }

  /**
   * Delete an additional file for an entity
   */
  async deleteFile(collection: StorageCollection, id: string, fileName: string): Promise<boolean> {
    assertSafePathSegment(fileName, 'fileName');
    const entityDir = path.dirname(this.getEntityPath(collection, id));
    const filePath = this.resolveWithinBase(path.join(entityDir, fileName));

    try {
      await secureFs.unlink(filePath);
      return true;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        return false;
      }
      throw error;
    }
  }

  /**
   * Get the base path for team storage
   */
  getBasePath(): string {
    return this.basePath;
  }
}

/**
 * Create a TeamStorageService from environment variables
 *
 * Uses TEAM_DATA_DIR environment variable for file storage path.
 * Falls back to DATA_DIR/team if TEAM_DATA_DIR is not set.
 */
export function createTeamStorage(dataDir: string): TeamStorageService {
  const teamDataDir = process.env.TEAM_DATA_DIR || path.join(dataDir, 'team');

  return new TeamStorageService({
    type: 'file',
    path: teamDataDir,
  });
}
