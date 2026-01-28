/**
 * Knowledge Library Store
 *
 * Zustand store for UI-only state related to the Knowledge Library feature.
 * Server state is managed by TanStack Query hooks.
 *
 * State managed here:
 * - Active view/tab selection
 * - Current session ID
 * - Staged file upload (before sending to server)
 * - Selected block for detail view
 * - Proposed new files metadata (for create-file validation)
 * - Session transcript (accumulated from WebSocket events)
 * - Draft user message (chat input)
 * - Active routing group (for grouping blocks by destination)
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ============================================================================
// Types
// ============================================================================

/** Active view/tab in the Knowledge Library UI */
export type KLActiveView = 'input' | 'library' | 'query';

/** Staged file for upload (File objects are NOT persisted) */
export interface KLStagedUpload {
  file: File;
  fileName: string;
}

/** Proposed new file metadata (for create-file validation) */
export interface KLProposedNewFile {
  title: string;
  overview: string;
  isValid: boolean;
  errors: string[];
}

/** Transcript entry for display */
export interface KLTranscriptEntry {
  id: string;
  role: 'system' | 'assistant' | 'user';
  content: string;
  timestamp?: string;
  level?: 'info' | 'error';
}

const normalizeWhitespace = (value: string): string => value.trim().replace(/\s+/g, ' ');

const validateProposedNewFile = (
  title: string,
  overview: string
): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];
  const trimmedTitle = title.trim();

  if (!trimmedTitle) {
    errors.push('Title is required.');
  }

  const normalizedOverview = normalizeWhitespace(overview);
  /* Regex explanation:
   * ^          - Start of string
   * ##         - Exactly two '#' characters
   * \s*        - Optional whitespace
   * Overview   - Literal "Overview"
   * /i         - Case insensitive
   */
  if (!/^##\s*Overview/i.test(normalizedOverview)) {
    errors.push('Overview must start with "## Overview".');
  }

  const overviewLength = normalizedOverview.length;
  if (overviewLength < 50 || overviewLength > 250) {
    errors.push('Overview must be 50-250 characters.');
  }

  return { isValid: errors.length === 0, errors };
};

// ============================================================================
// State Interface
// ============================================================================

interface KnowledgeLibraryState {
  // View state
  activeView: KLActiveView;

  // Session state
  currentSessionId: string | null;

  // Upload state (NOT persisted - File objects can't be serialized)
  stagedUpload: KLStagedUpload | null;

  // Selection state
  selectedBlockId: string | null;

  // Proposed new files (keyed by destination file path)
  proposedNewFiles: Record<string, KLProposedNewFile>;

  // Transcript state
  sessionTranscript: KLTranscriptEntry[];

  // Chat state
  draftUserMessage: string;

  // Routing group state
  activeRoutingGroupKey: string | null;

  // Library browser state
  selectedFilePath: string | null;
  expandedCategories: Set<string>;

  // Query state
  activeConversationId: string | null;

  // Transcript UI state
  isTranscriptExpanded: boolean;
}

// ============================================================================
// Actions Interface
// ============================================================================

interface KnowledgeLibraryActions {
  // View actions
  setActiveView: (view: KLActiveView) => void;

  // Session actions
  setCurrentSessionId: (sessionId: string | null) => void;

  // Upload actions
  stageUpload: (file: File) => void;
  clearStagedUpload: () => void;

  // Selection actions
  setSelectedBlockId: (blockId: string | null) => void;

  // Proposed files actions
  setProposedNewFile: (filePath: string, data: KLProposedNewFile) => void;
  updateProposedNewFile: (filePath: string, updates: Partial<KLProposedNewFile>) => void;
  removeProposedNewFile: (filePath: string) => void;
  clearProposedNewFiles: () => void;

  // Transcript actions
  addTranscriptEntry: (entry: KLTranscriptEntry) => void;
  addTranscriptEntries: (entries: KLTranscriptEntry[]) => void;
  clearTranscript: () => void;

  // Chat actions
  setDraftUserMessage: (message: string) => void;

  // Routing group actions
  setActiveRoutingGroupKey: (key: string | null) => void;

  // Library browser actions
  setSelectedFilePath: (path: string | null) => void;
  toggleCategory: (categoryPath: string) => void;
  expandCategory: (categoryPath: string) => void;
  collapseCategory: (categoryPath: string) => void;

  // Query actions
  setActiveConversationId: (id: string | null) => void;

  // Transcript UI actions
  setTranscriptExpanded: (expanded: boolean) => void;
  toggleTranscript: () => void;

  // Reset actions
  reset: () => void;
  resetSession: () => void;
}

// ============================================================================
// Initial State
// ============================================================================

const initialState: KnowledgeLibraryState = {
  activeView: 'input',
  currentSessionId: null,
  stagedUpload: null,
  selectedBlockId: null,
  proposedNewFiles: {},
  sessionTranscript: [],
  draftUserMessage: '',
  activeRoutingGroupKey: null,
  selectedFilePath: null,
  expandedCategories: new Set(),
  activeConversationId: null,
  isTranscriptExpanded: false,
};

// ============================================================================
// Store
// ============================================================================

export const useKnowledgeLibraryStore = create<KnowledgeLibraryState & KnowledgeLibraryActions>()(
  persist(
    (set, get) => ({
      ...initialState,

      // View actions
      setActiveView: (view) => set({ activeView: view }),

      // Session actions
      setCurrentSessionId: (sessionId) => set({ currentSessionId: sessionId }),

      // Upload actions
      stageUpload: (file) =>
        set({
          stagedUpload: {
            file,
            fileName: file.name,
          },
        }),

      clearStagedUpload: () => set({ stagedUpload: null }),

      // Selection actions
      setSelectedBlockId: (blockId) => set({ selectedBlockId: blockId }),

      // Proposed files actions
      setProposedNewFile: (filePath, data) =>
        set((state) => {
          const validation = validateProposedNewFile(data.title, data.overview);
          return {
            proposedNewFiles: {
              ...state.proposedNewFiles,
              [filePath]: {
                ...data,
                ...validation,
              },
            },
          };
        }),

      updateProposedNewFile: (filePath, updates) =>
        set((state) => {
          const existing = state.proposedNewFiles[filePath];
          if (!existing) return state;
          const next = { ...existing, ...updates };
          const validation = validateProposedNewFile(next.title, next.overview);
          return {
            proposedNewFiles: {
              ...state.proposedNewFiles,
              [filePath]: {
                ...next,
                ...validation,
              },
            },
          };
        }),

      removeProposedNewFile: (filePath) =>
        set((state) => {
          const { [filePath]: _, ...rest } = state.proposedNewFiles;
          return { proposedNewFiles: rest };
        }),

      clearProposedNewFiles: () => set({ proposedNewFiles: {} }),

      // Transcript actions
      addTranscriptEntry: (entry) =>
        set((state) => ({
          sessionTranscript: [...state.sessionTranscript, entry],
        })),

      addTranscriptEntries: (entries) =>
        set((state) => ({
          sessionTranscript: [...state.sessionTranscript, ...entries],
        })),

      clearTranscript: () => set({ sessionTranscript: [] }),

      // Chat actions
      setDraftUserMessage: (message) => set({ draftUserMessage: message }),

      // Routing group actions
      setActiveRoutingGroupKey: (key) => set({ activeRoutingGroupKey: key }),

      // Library browser actions
      setSelectedFilePath: (path) => set({ selectedFilePath: path }),

      toggleCategory: (categoryPath) =>
        set((state) => {
          const newSet = new Set(state.expandedCategories);
          if (newSet.has(categoryPath)) {
            newSet.delete(categoryPath);
          } else {
            newSet.add(categoryPath);
          }
          return { expandedCategories: newSet };
        }),

      expandCategory: (categoryPath) =>
        set((state) => {
          const newSet = new Set(state.expandedCategories);
          newSet.add(categoryPath);
          return { expandedCategories: newSet };
        }),

      collapseCategory: (categoryPath) =>
        set((state) => {
          const newSet = new Set(state.expandedCategories);
          newSet.delete(categoryPath);
          return { expandedCategories: newSet };
        }),

      // Query actions
      setActiveConversationId: (id) => set({ activeConversationId: id }),

      // Transcript UI actions
      setTranscriptExpanded: (expanded) => set({ isTranscriptExpanded: expanded }),
      toggleTranscript: () =>
        set((state) => ({ isTranscriptExpanded: !state.isTranscriptExpanded })),

      // Reset actions
      reset: () =>
        set({
          ...initialState,
          // Preserve expanded categories across resets
          expandedCategories: get().expandedCategories,
        }),

      resetSession: () =>
        set({
          currentSessionId: null,
          stagedUpload: null,
          selectedBlockId: null,
          proposedNewFiles: {},
          sessionTranscript: [],
          draftUserMessage: '',
          activeRoutingGroupKey: null,
        }),
    }),
    {
      name: 'automaker-knowledge-library-store',
      version: 1,
      partialize: (state) => ({
        // Only persist stable primitives
        activeView: state.activeView,
        currentSessionId: state.currentSessionId,
      }),
    }
  )
);

// ============================================================================
// Selectors (for common derived state)
// ============================================================================

/**
 * Check if there's a valid staged upload
 */
export const selectHasStagedUpload = (state: KnowledgeLibraryState): boolean =>
  state.stagedUpload !== null;

/**
 * Get count of invalid proposed new files
 */
export const selectInvalidProposedFilesCount = (state: KnowledgeLibraryState): number =>
  Object.values(state.proposedNewFiles).filter((f) => !f.isValid).length;

/**
 * Check if all proposed new files are valid
 */
export const selectAllProposedFilesValid = (state: KnowledgeLibraryState): boolean =>
  Object.values(state.proposedNewFiles).every((f) => f.isValid);
