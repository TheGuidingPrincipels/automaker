/**
 * Document Types - Types for the Documents feature
 *
 * Documents are structured files (like PRDs, architecture docs, guides)
 * that provide context to AI agents. They can be synced from external
 * sources (Notion, Google Docs, Confluence) or created locally.
 */

// ============================================================================
// Enums / Type Unions
// ============================================================================

/**
 * DocumentStatus - Lifecycle status of a document
 */
export type DocumentStatus = 'draft' | 'active' | 'archived';

/**
 * DocumentType - Types of documents
 */
export type DocumentType =
  | 'prd' // Product Requirements Document
  | 'architecture' // Architecture documentation
  | 'api-spec' // API specification (OpenAPI, etc.)
  | 'guide' // How-to guides and tutorials
  | 'runbook' // Operational runbooks
  | 'decision' // Architecture Decision Records (ADRs)
  | 'reference' // Reference documentation
  | 'notes' // Meeting notes, scratch docs
  | 'custom'; // User-defined type

/**
 * DocumentSourceType - Source of the document content
 */
export type DocumentSourceType =
  | 'local' // Created/edited locally in AutoMaker
  | 'notion' // Synced from Notion
  | 'google-docs' // Synced from Google Docs
  | 'confluence' // Synced from Confluence
  | 'github' // Synced from GitHub (markdown files)
  | 'url' // Fetched from a URL
  | 'file'; // Imported from local file

/**
 * DocumentSyncStatus - Synchronization status for external documents
 */
export type DocumentSyncStatus =
  | 'synced' // Up to date with source
  | 'pending' // Sync in progress
  | 'stale' // Source has newer content
  | 'error' // Sync failed
  | 'local-only'; // No external source

// ============================================================================
// Document Entity
// ============================================================================

/**
 * DocumentSource - External source configuration for a document
 */
export interface DocumentSource {
  /** Type of external source */
  type: DocumentSourceType;
  /** External ID (e.g., Notion page ID, Google Doc ID) */
  externalId?: string;
  /** URL to the source document */
  url?: string;
  /** Local file path (for file imports) */
  filePath?: string;
  /** ISO timestamp of last successful sync */
  lastSyncedAt?: string;
  /** Sync status */
  syncStatus: DocumentSyncStatus;
  /** Error message if sync failed */
  syncError?: string;
  /** ETag or version for change detection */
  version?: string;
}

/**
 * DocumentMetadata - Extracted or computed metadata
 */
export interface DocumentMetadata {
  /** Word count of content */
  wordCount?: number;
  /** Estimated reading time in minutes */
  readingTime?: number;
  /** Detected language (ISO 639-1 code) */
  language?: string;
  /** Table of contents (extracted headings) */
  tableOfContents?: Array<{
    level: number;
    text: string;
    anchor?: string;
  }>;
  /** Referenced files in the codebase */
  referencedFiles?: string[];
  /** External links found in content */
  externalLinks?: string[];
  /** Custom metadata fields */
  [key: string]: unknown;
}

/**
 * DocumentSection - A section within a document
 * Used for granular context injection
 */
export interface DocumentSection {
  /** Section identifier */
  id: string;
  /** Section heading */
  heading: string;
  /** Section content (markdown) */
  content: string;
  /** Heading level (1-6) */
  level: number;
  /** Start line in the original document */
  startLine?: number;
  /** End line in the original document */
  endLine?: number;
}

/**
 * Document - A document that provides context to AI agents
 */
export interface Document {
  /** Unique identifier */
  id: string;
  /** Display title */
  title: string;
  /** Brief description/summary */
  description: string;
  /** Full content (Markdown) */
  content: string;
  /** Document type */
  type: DocumentType;
  /** Current status */
  status: DocumentStatus;
  /** Source information (for external documents) */
  source?: DocumentSource;
  /** Extracted metadata */
  metadata?: DocumentMetadata;
  /** Parsed sections (for granular context) */
  sections?: DocumentSection[];
  /** Tags for categorization and filtering */
  tags?: string[];
  /** Project path this document belongs to (undefined = global/shared) */
  projectPath?: string;
  /** Related document IDs */
  relatedDocuments?: string[];
  /** Related feature IDs */
  relatedFeatures?: string[];
  /** Search keywords (for improved retrieval) */
  keywords?: string[];
  /** Embedding vector (for semantic search) */
  embedding?: number[];
  /** Priority for context injection (higher = more important) */
  priority?: number;
  /** Conditions for automatic context loading */
  autoLoadConditions?: {
    /** File patterns to match (glob) */
    filePatterns?: string[];
    /** Task types (e.g., 'feature', 'bugfix', 'refactor') */
    taskTypes?: string[];
    /** Feature categories */
    categories?: string[];
    /** Always include in context */
    always?: boolean;
  };
  /** ISO timestamp of creation */
  createdAt: string;
  /** ISO timestamp of last update */
  updatedAt: string;
  /** User ID of creator */
  createdBy?: string;
  /** User ID of last updater */
  updatedBy?: string;
}

// ============================================================================
// Input DTOs
// ============================================================================

/**
 * CreateDocumentInput - Input for creating a new document
 */
export interface CreateDocumentInput {
  title: string;
  description?: string;
  content: string;
  type: DocumentType;
  status?: DocumentStatus;
  tags?: string[];
  projectPath?: string;
  relatedDocuments?: string[];
  relatedFeatures?: string[];
  keywords?: string[];
  priority?: number;
  autoLoadConditions?: Document['autoLoadConditions'];
}

/**
 * UpdateDocumentInput - Input for updating an existing document
 */
export interface UpdateDocumentInput {
  title?: string;
  description?: string;
  content?: string;
  type?: DocumentType;
  status?: DocumentStatus;
  tags?: string[];
  relatedDocuments?: string[];
  relatedFeatures?: string[];
  keywords?: string[];
  priority?: number;
  autoLoadConditions?: Document['autoLoadConditions'];
}

/**
 * ImportDocumentInput - Input for importing a document from external source
 */
export interface ImportDocumentInput {
  /** Source type */
  sourceType: DocumentSourceType;
  /** URL to import from (for notion, google-docs, confluence, url) */
  url?: string;
  /** File path to import from (for file source) */
  filePath?: string;
  /** External ID (for notion, google-docs, confluence) */
  externalId?: string;
  /** Document title (optional, will be extracted if not provided) */
  title?: string;
  /** Document type */
  type?: DocumentType;
  /** Tags to apply */
  tags?: string[];
  /** Project path to associate with */
  projectPath?: string;
  /** Whether to enable auto-sync */
  enableSync?: boolean;
}

/**
 * SyncDocumentInput - Input for syncing a document with its source
 */
export interface SyncDocumentInput {
  /** Document ID to sync */
  documentId: string;
  /** Force sync even if content appears unchanged */
  force?: boolean;
}

// ============================================================================
// Response DTOs
// ============================================================================

/**
 * DocumentListItem - Lightweight document info for list views
 */
export interface DocumentListItem {
  id: string;
  title: string;
  description: string;
  type: DocumentType;
  status: DocumentStatus;
  tags?: string[];
  projectPath?: string;
  source?: {
    type: DocumentSourceType;
    syncStatus: DocumentSyncStatus;
  };
  metadata?: {
    wordCount?: number;
    readingTime?: number;
  };
  createdAt: string;
  updatedAt: string;
}

/**
 * DocumentSearchResult - Result from document search
 */
export interface DocumentSearchResult {
  /** Document ID */
  id: string;
  /** Document title */
  title: string;
  /** Document type */
  type: DocumentType;
  /** Relevance score (0-1) */
  score: number;
  /** Matched content snippet */
  snippet?: string;
  /** Matched section (if granular match) */
  matchedSection?: {
    id: string;
    heading: string;
  };
  /** Tags */
  tags?: string[];
}

/**
 * DocumentSyncResult - Result from sync operation
 */
export interface DocumentSyncResult {
  /** Whether sync was successful */
  success: boolean;
  /** Document ID */
  documentId: string;
  /** Whether content was updated */
  contentUpdated: boolean;
  /** New sync status */
  syncStatus: DocumentSyncStatus;
  /** Error message if failed */
  error?: string;
  /** ISO timestamp of sync */
  syncedAt: string;
}

// ============================================================================
// Query Types
// ============================================================================

/**
 * DocumentSearchQuery - Query for searching documents
 */
export interface DocumentSearchQuery {
  /** Search text */
  query: string;
  /** Filter by document types */
  types?: DocumentType[];
  /** Filter by status */
  status?: DocumentStatus[];
  /** Filter by tags */
  tags?: string[];
  /** Filter by project path */
  projectPath?: string;
  /** Include global/shared documents */
  includeGlobal?: boolean;
  /** Maximum results */
  limit?: number;
  /** Use semantic search (requires embeddings) */
  semantic?: boolean;
}

/**
 * DocumentListQuery - Query for listing documents
 */
export interface DocumentListQuery {
  /** Filter by document types */
  types?: DocumentType[];
  /** Filter by status */
  status?: DocumentStatus[];
  /** Filter by tags */
  tags?: string[];
  /** Filter by project path */
  projectPath?: string;
  /** Include global/shared documents */
  includeGlobal?: boolean;
  /** Sort field */
  sortBy?: 'title' | 'createdAt' | 'updatedAt' | 'priority';
  /** Sort direction */
  sortOrder?: 'asc' | 'desc';
  /** Pagination offset */
  offset?: number;
  /** Pagination limit */
  limit?: number;
}

/**
 * DocumentContextQuery - Query for retrieving documents as context
 * Used by AI agents to get relevant documentation
 */
export interface DocumentContextQuery {
  /** Task description to match against */
  taskDescription?: string;
  /** Feature ID to get related documents */
  featureId?: string;
  /** File paths being worked on (for auto-load matching) */
  filePaths?: string[];
  /** Task type (for auto-load matching) */
  taskType?: string;
  /** Category (for auto-load matching) */
  category?: string;
  /** Specific document IDs to include */
  documentIds?: string[];
  /** Maximum total content length (characters) */
  maxContentLength?: number;
  /** Whether to include full content or just summaries */
  fullContent?: boolean;
}

/**
 * DocumentContextResult - Result from context query
 */
export interface DocumentContextResult {
  /** Documents matched by query */
  documents: Array<{
    id: string;
    title: string;
    type: DocumentType;
    content: string;
    relevanceScore?: number;
    matchReason?: 'explicit' | 'auto-load' | 'related' | 'semantic';
  }>;
  /** Total content length returned */
  totalContentLength: number;
  /** Whether content was truncated */
  truncated: boolean;
}
