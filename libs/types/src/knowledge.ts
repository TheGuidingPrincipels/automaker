/**
 * Knowledge Types - Types for the Knowledge Hub feature
 *
 * The Knowledge Hub consists of three main sections:
 * 1. Blueprints - Guidelines, behaviors, and processes for agents
 * 2. Knowledge Server - Company knowledge storage and retrieval
 * 3. Learning MCP - Agent learnings from issue resolution
 */

/**
 * KnowledgeSection - Identifiers for Knowledge Hub sections
 */
export type KnowledgeSection = 'blueprints' | 'knowledge-server' | 'learning';

/**
 * BlueprintCategory - Categories for organizing blueprints
 */
export type BlueprintCategory =
  | 'coding-standards' // Code style, patterns, practices
  | 'architecture' // System design, structure
  | 'testing' // Testing strategies, requirements
  | 'security' // Security guidelines, practices
  | 'documentation' // Doc standards, templates
  | 'workflow' // Development workflows, processes
  | 'review' // Code review guidelines
  | 'deployment' // Deployment procedures
  | 'custom'; // User-defined category

/**
 * BlueprintStatus - Lifecycle status of a blueprint
 */
export type BlueprintStatus = 'draft' | 'active' | 'deprecated';

/**
 * Blueprint - A guideline or process document for agents
 *
 * Blueprints define how agents should behave in specific contexts.
 * They can be automatically loaded into agent prompts based on tags.
 */
export interface Blueprint {
  /** Unique identifier */
  id: string;
  /** Display name */
  name: string;
  /** Brief description */
  description: string;
  /** Full content (Markdown) */
  content: string;
  /** Category for organization */
  category: BlueprintCategory;
  /** Current status */
  status: BlueprintStatus;
  /** Tags for filtering and auto-loading */
  tags?: string[];
  /** Priority (higher = loaded first when multiple match) */
  priority?: number;
  /** Conditions for automatic loading */
  autoLoadConditions?: {
    /** File patterns to match (glob) */
    filePatterns?: string[];
    /** Language contexts (e.g., 'typescript', 'python') */
    languages?: string[];
    /** Task types (e.g., 'refactor', 'bugfix', 'feature') */
    taskTypes?: string[];
  };
  /** ISO timestamp of creation */
  createdAt: string;
  /** ISO timestamp of last update */
  updatedAt: string;
  /** User ID of creator */
  createdBy?: string;
}

/**
 * KnowledgeEntryType - Types of knowledge entries
 */
export type KnowledgeEntryType =
  | 'documentation' // General documentation
  | 'api-reference' // API documentation
  | 'tutorial' // How-to guides
  | 'faq' // Frequently asked questions
  | 'decision' // Architecture decisions (ADRs)
  | 'runbook' // Operational procedures
  | 'glossary' // Term definitions
  | 'custom'; // User-defined type

/**
 * KnowledgeEntry - A piece of company/project knowledge
 *
 * Knowledge entries are stored in the Knowledge Server and can be
 * searched and retrieved by agents during task execution.
 */
export interface KnowledgeEntry {
  /** Unique identifier */
  id: string;
  /** Display title */
  title: string;
  /** Brief description/summary */
  description: string;
  /** Full content (Markdown) */
  content: string;
  /** Entry type */
  type: KnowledgeEntryType;
  /** Tags for categorization and search */
  tags?: string[];
  /** Source URL (if external) */
  sourceUrl?: string;
  /** Related entry IDs */
  relatedEntries?: string[];
  /** Search keywords (for improved retrieval) */
  keywords?: string[];
  /** Embedding vector (for semantic search) */
  embedding?: number[];
  /** ISO timestamp of creation */
  createdAt: string;
  /** ISO timestamp of last update */
  updatedAt: string;
  /** User ID of creator */
  createdBy?: string;
}

/**
 * LearningType - Types of agent learnings
 */
export type LearningType =
  | 'bug-fix' // Learned from fixing a bug
  | 'pattern' // Recognized code pattern
  | 'optimization' // Performance improvement
  | 'best-practice' // Identified best practice
  | 'anti-pattern' // Identified anti-pattern to avoid
  | 'tool-usage' // Effective tool usage
  | 'context-specific' // Project-specific knowledge
  | 'custom'; // User-defined type

/**
 * LearningConfidence - Confidence level in a learning
 */
export type LearningConfidence = 'low' | 'medium' | 'high' | 'verified';

/**
 * Learning - An insight extracted from agent task execution
 *
 * Learnings are automatically extracted from successful agent sessions
 * and can be used to improve future agent performance.
 */
export interface Learning {
  /** Unique identifier */
  id: string;
  /** Display title */
  title: string;
  /** Brief description of the learning */
  description: string;
  /** Detailed explanation */
  content: string;
  /** Learning type */
  type: LearningType;
  /** Confidence level */
  confidence: LearningConfidence;
  /** Source session ID (where learning was extracted from) */
  sourceSessionId?: string;
  /** Source feature ID (if from feature execution) */
  sourceFeatureId?: string;
  /** Problem that was solved */
  problem?: string;
  /** Solution that worked */
  solution?: string;
  /** Prevention strategy for future */
  prevention?: string;
  /** Context in which this learning applies */
  context?: {
    /** Languages involved */
    languages?: string[];
    /** Frameworks involved */
    frameworks?: string[];
    /** File patterns where applicable */
    filePatterns?: string[];
  };
  /** Tags for categorization */
  tags?: string[];
  /** Number of times this learning has been applied */
  applicationCount?: number;
  /** Success rate when applied (0-1) */
  successRate?: number;
  /** Embedding vector (for semantic search) */
  embedding?: number[];
  /** ISO timestamp of creation */
  createdAt: string;
  /** ISO timestamp of last update */
  updatedAt: string;
  /** User ID who verified (if verified) */
  verifiedBy?: string;
}

/**
 * CreateBlueprintInput - Input for creating a new blueprint
 */
export interface CreateBlueprintInput {
  name: string;
  description: string;
  content: string;
  category: BlueprintCategory;
  tags?: string[];
  priority?: number;
  autoLoadConditions?: Blueprint['autoLoadConditions'];
}

/**
 * UpdateBlueprintInput - Input for updating a blueprint
 */
export interface UpdateBlueprintInput {
  name?: string;
  description?: string;
  content?: string;
  category?: BlueprintCategory;
  status?: BlueprintStatus;
  tags?: string[];
  priority?: number;
  autoLoadConditions?: Blueprint['autoLoadConditions'];
}

/**
 * CreateKnowledgeEntryInput - Input for creating a knowledge entry
 */
export interface CreateKnowledgeEntryInput {
  title: string;
  description: string;
  content: string;
  type: KnowledgeEntryType;
  tags?: string[];
  sourceUrl?: string;
  relatedEntries?: string[];
  keywords?: string[];
}

/**
 * UpdateKnowledgeEntryInput - Input for updating a knowledge entry
 */
export interface UpdateKnowledgeEntryInput {
  title?: string;
  description?: string;
  content?: string;
  type?: KnowledgeEntryType;
  tags?: string[];
  sourceUrl?: string;
  relatedEntries?: string[];
  keywords?: string[];
}

/**
 * CreateLearningInput - Input for creating a learning
 */
export interface CreateLearningInput {
  title: string;
  description: string;
  content: string;
  type: LearningType;
  confidence?: LearningConfidence;
  sourceSessionId?: string;
  sourceFeatureId?: string;
  problem?: string;
  solution?: string;
  prevention?: string;
  context?: Learning['context'];
  tags?: string[];
}

/**
 * UpdateLearningInput - Input for updating a learning
 */
export interface UpdateLearningInput {
  title?: string;
  description?: string;
  content?: string;
  type?: LearningType;
  confidence?: LearningConfidence;
  problem?: string;
  solution?: string;
  prevention?: string;
  context?: Learning['context'];
  tags?: string[];
}

/**
 * ExtractLearningsInput - Input for extracting learnings from a session
 */
export interface ExtractLearningsInput {
  /** Session ID to extract from */
  sessionId: string;
  /** Feature ID (optional) */
  featureId?: string;
  /** Whether to auto-verify high-confidence learnings */
  autoVerify?: boolean;
}

/**
 * KnowledgeSearchQuery - Query for searching knowledge
 */
export interface KnowledgeSearchQuery {
  /** Search text */
  query: string;
  /** Filter by section */
  section?: KnowledgeSection;
  /** Filter by types */
  types?: string[];
  /** Filter by tags */
  tags?: string[];
  /** Maximum results */
  limit?: number;
  /** Use semantic search (requires embeddings) */
  semantic?: boolean;
}

/**
 * KnowledgeSearchResult - Result from knowledge search
 */
export interface KnowledgeSearchResult {
  /** Result type */
  type: 'blueprint' | 'knowledge-entry' | 'learning';
  /** Result ID */
  id: string;
  /** Display title */
  title: string;
  /** Description/summary */
  description: string;
  /** Relevance score (0-1) */
  score: number;
  /** Matched content snippet */
  snippet?: string;
  /** Tags */
  tags?: string[];
}
