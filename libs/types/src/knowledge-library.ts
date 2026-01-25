/**
 * Knowledge Library API Types
 *
 * TypeScript types mirroring the AI-Library Python backend schemas.
 * Used by the Automaker frontend to communicate with the standalone
 * Knowledge Library service.
 *
 * @see 2.ai-library/src/api/schemas.py
 */

// ============================================================================
// Core Types
// ============================================================================

/** Content processing mode */
export type KLContentMode = 'strict' | 'refinement';

/** Cleanup disposition for a block */
export type KLCleanupDisposition = 'keep' | 'discard';

/** Status of a routing block decision */
export type KLBlockStatus = 'pending' | 'selected' | 'rejected';

/** Session processing phase */
export type KLSessionPhase =
  | 'initialized'
  | 'parsing'
  | 'cleanup_plan_ready'
  | 'routing_plan_ready'
  | 'awaiting_approval'
  | 'ready_to_execute'
  | 'executing'
  | 'verifying'
  | 'completed'
  | 'error';

/** Standard success response */
export interface KLSuccessResponse {
  success: boolean;
  message?: string | null;
}

/** Standard error response */
export interface KLErrorResponse {
  error: string;
  detail?: string | null;
}

// ============================================================================
// Health Check
// ============================================================================

export interface KLHealthResponse {
  status: string;
  database: string;
  version: string;
}

// ============================================================================
// Sessions
// ============================================================================

/** Request to create a new session (upload-first flow) */
export interface KLCreateSessionRequest {
  library_path?: string | null;
  content_mode?: KLContentMode | null;
  /** Optional server-local path (kept for backwards compatibility) */
  source_path?: string | null;
}

/** Session details response */
export interface KLSessionResponse {
  id: string;
  phase: KLSessionPhase;
  created_at: string;
  updated_at: string;
  content_mode: KLContentMode;
  library_path: string;
  source_file: string | null;

  total_blocks: number;
  kept_blocks: number;
  discarded_blocks: number;

  has_cleanup_plan: boolean;
  has_routing_plan: boolean;
  cleanup_approved: boolean;
  routing_approved: boolean;
  can_execute: boolean;

  errors: string[];
}

/** List of sessions */
export interface KLSessionListResponse {
  sessions: KLSessionResponse[];
  total: number;
}

// ============================================================================
// Blocks
// ============================================================================

/** Content block details */
export interface KLBlockResponse {
  id: string;
  block_type: string;
  content: string;
  content_preview: string;
  heading_path: string[];
  source_file: string;
  source_line_start: number;
  source_line_end: number;
  checksum_exact: string;
  checksum_canonical: string;
  is_executed: boolean;
  integrity_verified: boolean;
}

/** List of blocks */
export interface KLBlockListResponse {
  blocks: KLBlockResponse[];
  total: number;
}

// ============================================================================
// Cleanup Plan
// ============================================================================

/** Single cleanup item */
export interface KLCleanupItemResponse {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  suggested_disposition: KLCleanupDisposition;
  suggestion_reason: string;
  final_disposition: KLCleanupDisposition | null;
}

/** Cleanup plan for a session */
export interface KLCleanupPlanResponse {
  session_id: string;
  source_file: string;
  created_at: string;
  items: KLCleanupItemResponse[];
  all_decided: boolean;
  approved: boolean;
  approved_at: string | null;
  pending_count: number;
  total_count: number;
}

/** Request to set cleanup decision */
export interface KLCleanupDecisionRequest {
  disposition: KLCleanupDisposition;
}

// ============================================================================
// Routing Plan
// ============================================================================

/** Destination option for a block */
export interface KLDestinationOptionResponse {
  destination_file: string;
  destination_section: string | null;
  action: string;
  confidence: number;
  reasoning: string;

  /** For create-section action */
  proposed_section_title?: string | null;

  /** For create_file action (REQUIRED when action === "create_file") */
  proposed_file_title?: string | null;
  /** 50-250 chars (trim+normalize) */
  proposed_file_overview?: string | null;
}

/** Routing item for a single block */
export interface KLBlockRoutingItemResponse {
  block_id: string;
  heading_path: string[];
  content_preview: string;
  options: KLDestinationOptionResponse[];
  selected_option_index: number | null;
  custom_destination_file: string | null;
  custom_destination_section: string | null;
  custom_action: string | null;
  /** For custom create-file */
  custom_proposed_file_title?: string | null;
  custom_proposed_file_overview?: string | null;
  status: KLBlockStatus;

  /** If a create-file option was selected, allow UI to override metadata */
  override_file_title?: string | null;
  override_file_overview?: string | null;

  /** If user chose custom create-file */
  custom_file_title?: string | null;
  custom_file_overview?: string | null;
}

/** Preview of a merge operation */
export interface KLMergePreviewResponse {
  merge_id: string;
  block_id: string;
  existing_content: string;
  existing_location: string;
  new_content: string;
  proposed_merge: string;
  merge_reasoning: string;
}

/** Summary of the routing plan */
export interface KLPlanSummaryResponse {
  total_blocks: number;
  blocks_to_new_files: number;
  blocks_to_existing_files: number;
  blocks_requiring_merge: number;
  estimated_actions: number;
}

/** Complete routing plan */
export interface KLRoutingPlanResponse {
  session_id: string;
  source_file: string;
  content_mode: KLContentMode;
  created_at: string;
  blocks: KLBlockRoutingItemResponse[];
  merge_previews: KLMergePreviewResponse[];
  summary: KLPlanSummaryResponse | null;
  all_blocks_resolved: boolean;
  approved: boolean;
  approved_at: string | null;
  pending_count: number;
  accepted_count: number;
}

/** Request to select a destination for a block */
export interface KLSelectDestinationRequest {
  option_index?: number | null;
  custom_file?: string | null;
  custom_section?: string | null;
  custom_action?: string | null;

  /** REQUIRED when selecting a create_file option (UI editable fields) */
  proposed_file_title?: string | null;
  proposed_file_overview?: string | null;

  /** REQUIRED when custom_action === "create_file" */
  custom_file_title?: string | null;
  custom_file_overview?: string | null;
}

/** Request to decide on a merge */
export interface KLMergeDecisionRequest {
  accept: boolean;
  edited_content?: string | null;
}

/** Request to set content mode */
export interface KLSetModeRequest {
  mode: KLContentMode;
}

// ============================================================================
// Execution
// ============================================================================

/** Result of writing a single block */
export interface KLWriteResultResponse {
  block_id: string;
  destination_file: string;
  success: boolean;
  checksum_verified: boolean;
  error?: string | null;
}

/** Execution result */
export interface KLExecuteResponse {
  session_id: string;
  success: boolean;
  total_blocks: number;
  blocks_written: number;
  blocks_failed: number;
  all_verified: boolean;
  results: KLWriteResultResponse[];
  errors: string[];
}

// ============================================================================
// Library
// ============================================================================

/** Library file metadata */
export interface KLLibraryFileResponse {
  path: string;
  category: string;
  title: string;
  sections: string[];
  last_modified: string;
  block_count: number;

  /** Overview metadata */
  overview: string | null;
  is_valid: boolean;
  validation_errors: string[];
}

/** Library category */
export interface KLLibraryCategoryResponse {
  name: string;
  path: string;
  description: string;
  files: KLLibraryFileResponse[];
  subcategories: KLLibraryCategoryResponse[];
}

/** Library structure */
export interface KLLibraryStructureResponse {
  categories: KLLibraryCategoryResponse[];
  total_files: number;
  total_sections: number;
}

/** File content response */
export interface KLLibraryFileContentResponse {
  content: string;
  path: string;
}

/** Keyword search result */
export interface KLLibrarySearchResult {
  file_path: string;
  file_title: string;
  section: string;
  category: string;
}

/** Keyword search response */
export interface KLLibrarySearchResponse {
  results: KLLibrarySearchResult[];
  query: string;
  total: number;
}

/** Index operation response */
export interface KLIndexResponse {
  status: string;
  files_indexed: number;
  details?: string[] | null;
}

// ============================================================================
// Query (RAG + Semantic Search)
// ============================================================================

/** Request for semantic search */
export interface KLSemanticSearchRequest {
  query: string;
  n_results?: number;
  min_similarity?: number;
  filter_taxonomy?: string | null;
  filter_content_type?: string | null;
}

/** Semantic search result */
export interface KLSemanticSearchResult {
  content: string;
  file_path: string;
  section: string;
  similarity: number;
  chunk_id: string;
  taxonomy_path?: string | null;
  content_type?: string | null;
}

/** Semantic search response */
export interface KLSemanticSearchResponse {
  results: KLSemanticSearchResult[];
  query: string;
  total: number;
}

/** Request to ask the library (RAG) */
export interface KLAskRequest {
  question: string;
  max_sources?: number;
  conversation_id?: string | null;
}

/** Source information in an answer */
export interface KLAskSourceInfo {
  file_path: string;
  section?: string | null;
  similarity?: number | null;
}

/** Answer from the library */
export interface KLAskResponse {
  answer: string;
  sources: KLAskSourceInfo[];
  confidence: number;
  conversation_id?: string | null;
  related_topics: string[];
}

/** Single turn in a conversation */
export interface KLConversationTurn {
  role: string;
  content: string;
  timestamp: string;
  sources: string[];
}

/** Conversation with history */
export interface KLConversation {
  id: string;
  title?: string | null;
  created_at: string;
  updated_at: string;
  turns: KLConversationTurn[];
}

/** List of conversations */
export interface KLConversationListResponse {
  conversations: KLConversation[];
  total: number;
}

/** Find similar content result */
export interface KLFindSimilarResult {
  content: string;
  file_path: string;
  section: string;
  similarity: number;
  chunk_id: string;
}

/** Find similar content response */
export interface KLFindSimilarResponse {
  results: KLFindSimilarResult[];
  total: number;
}

// ============================================================================
// WebSocket Streaming
// ============================================================================

/** Event types for WebSocket stream */
export type KLStreamEventType =
  | 'connected'
  | 'pong'
  | 'progress'
  | 'cleanup_started'
  | 'cleanup_ready'
  | 'routing_started'
  | 'routing_ready'
  | 'candidate_search'
  | 'user_message'
  | 'question'
  | 'error'
  | string; // forward-compatible

/** WebSocket stream event */
export interface KLStreamEvent {
  event_type: KLStreamEventType;
  session_id: string;
  data: {
    /** Human-readable text suitable for the Input Mode "chat transcript" */
    message?: string;

    /** Pending question payload */
    id?: string;
    question?: string;
    created_at?: string;

    /** Optional progress indicator */
    progress?: number | null;

    /** Event payload (e.g., cleanup_plan / routing_plan model_dump) */
    data?: unknown;

    /** Optional initial connect info */
    phase?: string;

    /** Optional question flow */
    question_id?: string;
  };

  /** ISO timestamp (optional) */
  timestamp?: string;
}

/** Commands that can be sent over WebSocket */
export type KLStreamCommand =
  | 'generate_cleanup'
  | 'generate_routing'
  | 'ping'
  | 'user_message'
  | 'answer';

/** WebSocket command request */
export interface KLStreamCommandRequest {
  command: KLStreamCommand;

  /** For user_message command */
  message?: string;

  /** For answer command */
  question_id?: string;
  answer?: string;
}
