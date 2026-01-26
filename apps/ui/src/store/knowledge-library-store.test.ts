import { beforeEach, describe, expect, it } from 'vitest';

import {
  useKnowledgeLibraryStore,
  selectHasStagedUpload,
  selectInvalidProposedFilesCount,
  selectAllProposedFilesValid,
} from './knowledge-library-store';

// ============================================================================
// Helpers
// ============================================================================

const createValidOverview = (): string => `## Overview ${'a'.repeat(60)}`;

const createInvalidOverview = (): string => 'Overview only';

const createMockFile = (name = 'test.pdf'): File =>
  new File(['test content'], name, { type: 'application/pdf' });

const readPersistedState = (): Record<string, unknown> => {
  const raw = localStorage.getItem('automaker-knowledge-library-store');
  if (!raw) {
    return {};
  }
  const parsed = JSON.parse(raw) as { state?: Record<string, unknown> };
  return parsed.state ?? {};
};

// ============================================================================
// Tests
// ============================================================================

describe('knowledge-library-store', () => {
  beforeEach(() => {
    localStorage.clear();
    // reset() preserves expandedCategories, so use setState for full reset
    useKnowledgeLibraryStore.setState({
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
    });
  });

  // ==========================================================================
  // Persistence
  // ==========================================================================

  describe('persistence', () => {
    it('persists only activeView and currentSessionId', async () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setActiveView('library');
      state.setCurrentSessionId('session-123');
      state.setSelectedFilePath('/notes/overview.md');
      state.setActiveConversationId('conversation-1');
      state.toggleCategory('docs');

      await Promise.resolve();

      expect(readPersistedState()).toEqual({
        activeView: 'library',
        currentSessionId: 'session-123',
      });
    });
  });

  // ==========================================================================
  // View Actions
  // ==========================================================================

  describe('setActiveView', () => {
    it('sets activeView to input', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setActiveView('input');
      expect(useKnowledgeLibraryStore.getState().activeView).toBe('input');
    });

    it('sets activeView to library', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setActiveView('library');
      expect(useKnowledgeLibraryStore.getState().activeView).toBe('library');
    });

    it('sets activeView to query', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setActiveView('query');
      expect(useKnowledgeLibraryStore.getState().activeView).toBe('query');
    });
  });

  // ==========================================================================
  // Session Actions
  // ==========================================================================

  describe('setCurrentSessionId', () => {
    it('sets a session ID', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setCurrentSessionId('session-abc');
      expect(useKnowledgeLibraryStore.getState().currentSessionId).toBe('session-abc');
    });

    it('clears session ID with null', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setCurrentSessionId('session-abc');
      state.setCurrentSessionId(null);
      expect(useKnowledgeLibraryStore.getState().currentSessionId).toBeNull();
    });
  });

  // ==========================================================================
  // Upload Actions
  // ==========================================================================

  describe('stageUpload / clearStagedUpload', () => {
    it('stages a file upload', () => {
      const state = useKnowledgeLibraryStore.getState();
      const file = createMockFile('document.pdf');

      state.stageUpload(file);

      const staged = useKnowledgeLibraryStore.getState().stagedUpload;
      expect(staged).not.toBeNull();
      expect(staged?.file).toBe(file);
      expect(staged?.fileName).toBe('document.pdf');
    });

    it('clears staged upload', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.stageUpload(createMockFile());
      state.clearStagedUpload();
      expect(useKnowledgeLibraryStore.getState().stagedUpload).toBeNull();
    });
  });

  // ==========================================================================
  // Selection Actions
  // ==========================================================================

  describe('setSelectedBlockId', () => {
    it('sets a block ID', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setSelectedBlockId('block-123');
      expect(useKnowledgeLibraryStore.getState().selectedBlockId).toBe('block-123');
    });

    it('clears block ID with null', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setSelectedBlockId('block-123');
      state.setSelectedBlockId(null);
      expect(useKnowledgeLibraryStore.getState().selectedBlockId).toBeNull();
    });
  });

  // ==========================================================================
  // Proposed Files Actions
  // ==========================================================================

  describe('setProposedNewFile', () => {
    it('validates proposed new file metadata on set', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setProposedNewFile('docs/new-file.md', {
        title: '',
        overview: createInvalidOverview(),
        isValid: true,
        errors: [],
      });

      const entry = useKnowledgeLibraryStore.getState().proposedNewFiles['docs/new-file.md'];

      expect(entry.isValid).toBe(false);
      expect(entry.errors).toContain('Title is required.');
      expect(entry.errors).toContain('Overview must start with "## Overview".');
    });

    it('marks valid metadata as valid', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setProposedNewFile('docs/valid-file.md', {
        title: 'Valid Title',
        overview: createValidOverview(),
        isValid: false,
        errors: ['old error'],
      });

      const entry = useKnowledgeLibraryStore.getState().proposedNewFiles['docs/valid-file.md'];
      expect(entry.isValid).toBe(true);
      expect(entry.errors).toEqual([]);
    });

    it('validates overview length - too short', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setProposedNewFile('docs/short.md', {
        title: 'Title',
        overview: '## Overview short', // Less than 50 chars
        isValid: true,
        errors: [],
      });

      const entry = useKnowledgeLibraryStore.getState().proposedNewFiles['docs/short.md'];
      expect(entry.isValid).toBe(false);
      expect(entry.errors).toContain('Overview must be 50-250 characters.');
    });

    it('validates overview length - too long', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setProposedNewFile('docs/long.md', {
        title: 'Title',
        overview: `## Overview ${'a'.repeat(300)}`, // More than 250 chars
        isValid: true,
        errors: [],
      });

      const entry = useKnowledgeLibraryStore.getState().proposedNewFiles['docs/long.md'];
      expect(entry.isValid).toBe(false);
      expect(entry.errors).toContain('Overview must be 50-250 characters.');
    });
  });

  describe('updateProposedNewFile', () => {
    it('recomputes validity when proposed metadata updates', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setProposedNewFile('docs/new-file.md', {
        title: '',
        overview: createInvalidOverview(),
        isValid: true,
        errors: [],
      });

      state.updateProposedNewFile('docs/new-file.md', {
        title: 'Valid Title',
        overview: createValidOverview(),
      });

      const entry = useKnowledgeLibraryStore.getState().proposedNewFiles['docs/new-file.md'];

      expect(entry.isValid).toBe(true);
      expect(entry.errors).toEqual([]);
    });

    it('does nothing for non-existent file', () => {
      const state = useKnowledgeLibraryStore.getState();
      const before = { ...useKnowledgeLibraryStore.getState().proposedNewFiles };

      state.updateProposedNewFile('non-existent.md', { title: 'New Title' });

      expect(useKnowledgeLibraryStore.getState().proposedNewFiles).toEqual(before);
    });
  });

  describe('removeProposedNewFile', () => {
    it('removes an existing proposed file', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setProposedNewFile('docs/file1.md', {
        title: 'File 1',
        overview: createValidOverview(),
        isValid: true,
        errors: [],
      });

      state.setProposedNewFile('docs/file2.md', {
        title: 'File 2',
        overview: createValidOverview(),
        isValid: true,
        errors: [],
      });

      state.removeProposedNewFile('docs/file1.md');

      const files = useKnowledgeLibraryStore.getState().proposedNewFiles;
      expect(files['docs/file1.md']).toBeUndefined();
      expect(files['docs/file2.md']).toBeDefined();
    });
  });

  describe('clearProposedNewFiles', () => {
    it('clears all proposed files', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setProposedNewFile('docs/file1.md', {
        title: 'File 1',
        overview: createValidOverview(),
        isValid: true,
        errors: [],
      });

      state.setProposedNewFile('docs/file2.md', {
        title: 'File 2',
        overview: createValidOverview(),
        isValid: true,
        errors: [],
      });

      state.clearProposedNewFiles();

      expect(useKnowledgeLibraryStore.getState().proposedNewFiles).toEqual({});
    });
  });

  // ==========================================================================
  // Transcript Actions
  // ==========================================================================

  describe('addTranscriptEntry', () => {
    it('adds a single entry to transcript', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.addTranscriptEntry({
        id: 'entry-1',
        role: 'user',
        content: 'Hello',
        timestamp: '2024-01-01T00:00:00Z',
      });

      const transcript = useKnowledgeLibraryStore.getState().sessionTranscript;
      expect(transcript).toHaveLength(1);
      expect(transcript[0]).toEqual({
        id: 'entry-1',
        role: 'user',
        content: 'Hello',
        timestamp: '2024-01-01T00:00:00Z',
      });
    });
  });

  describe('addTranscriptEntries', () => {
    it('adds multiple entries to transcript', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.addTranscriptEntries([
        { id: 'entry-1', role: 'user', content: 'Hello' },
        { id: 'entry-2', role: 'assistant', content: 'Hi there!' },
      ]);

      const transcript = useKnowledgeLibraryStore.getState().sessionTranscript;
      expect(transcript).toHaveLength(2);
      expect(transcript[0].content).toBe('Hello');
      expect(transcript[1].content).toBe('Hi there!');
    });

    it('appends to existing transcript', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.addTranscriptEntry({ id: 'entry-0', role: 'system', content: 'System start' });
      state.addTranscriptEntries([
        { id: 'entry-1', role: 'user', content: 'Hello' },
        { id: 'entry-2', role: 'assistant', content: 'Hi!' },
      ]);

      expect(useKnowledgeLibraryStore.getState().sessionTranscript).toHaveLength(3);
    });
  });

  describe('clearTranscript', () => {
    it('clears all transcript entries', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.addTranscriptEntries([
        { id: 'entry-1', role: 'user', content: 'Hello' },
        { id: 'entry-2', role: 'assistant', content: 'Hi!' },
      ]);

      state.clearTranscript();

      expect(useKnowledgeLibraryStore.getState().sessionTranscript).toEqual([]);
    });
  });

  // ==========================================================================
  // Chat Actions
  // ==========================================================================

  describe('setDraftUserMessage', () => {
    it('sets draft message', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setDraftUserMessage('My draft message');
      expect(useKnowledgeLibraryStore.getState().draftUserMessage).toBe('My draft message');
    });

    it('clears draft message with empty string', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setDraftUserMessage('My draft');
      state.setDraftUserMessage('');
      expect(useKnowledgeLibraryStore.getState().draftUserMessage).toBe('');
    });
  });

  // ==========================================================================
  // Routing Group Actions
  // ==========================================================================

  describe('setActiveRoutingGroupKey', () => {
    it('sets routing group key', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setActiveRoutingGroupKey('group-1');
      expect(useKnowledgeLibraryStore.getState().activeRoutingGroupKey).toBe('group-1');
    });

    it('clears routing group key with null', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setActiveRoutingGroupKey('group-1');
      state.setActiveRoutingGroupKey(null);
      expect(useKnowledgeLibraryStore.getState().activeRoutingGroupKey).toBeNull();
    });
  });

  // ==========================================================================
  // Library Browser Actions
  // ==========================================================================

  describe('setSelectedFilePath', () => {
    it('sets selected file path', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setSelectedFilePath('/docs/readme.md');
      expect(useKnowledgeLibraryStore.getState().selectedFilePath).toBe('/docs/readme.md');
    });

    it('clears with null', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setSelectedFilePath('/docs/readme.md');
      state.setSelectedFilePath(null);
      expect(useKnowledgeLibraryStore.getState().selectedFilePath).toBeNull();
    });
  });

  describe('toggleCategory', () => {
    it('expands a collapsed category', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.toggleCategory('docs');
      expect(useKnowledgeLibraryStore.getState().expandedCategories.has('docs')).toBe(true);
    });

    it('collapses an expanded category', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.toggleCategory('docs');
      state.toggleCategory('docs');
      expect(useKnowledgeLibraryStore.getState().expandedCategories.has('docs')).toBe(false);
    });
  });

  describe('expandCategory', () => {
    it('expands a category', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.expandCategory('tutorials');
      expect(useKnowledgeLibraryStore.getState().expandedCategories.has('tutorials')).toBe(true);
    });

    it('is idempotent', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.expandCategory('tutorials');
      state.expandCategory('tutorials');
      expect(useKnowledgeLibraryStore.getState().expandedCategories.has('tutorials')).toBe(true);
    });
  });

  describe('collapseCategory', () => {
    it('collapses a category', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.expandCategory('tutorials');
      state.collapseCategory('tutorials');
      expect(useKnowledgeLibraryStore.getState().expandedCategories.has('tutorials')).toBe(false);
    });

    it('is idempotent', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.collapseCategory('tutorials');
      expect(useKnowledgeLibraryStore.getState().expandedCategories.has('tutorials')).toBe(false);
    });
  });

  // ==========================================================================
  // Query Actions
  // ==========================================================================

  describe('setActiveConversationId', () => {
    it('sets conversation ID', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setActiveConversationId('conv-123');
      expect(useKnowledgeLibraryStore.getState().activeConversationId).toBe('conv-123');
    });

    it('clears with null', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.setActiveConversationId('conv-123');
      state.setActiveConversationId(null);
      expect(useKnowledgeLibraryStore.getState().activeConversationId).toBeNull();
    });
  });

  // ==========================================================================
  // Reset Actions
  // ==========================================================================

  describe('reset', () => {
    it('resets to initial state', () => {
      const state = useKnowledgeLibraryStore.getState();

      // Set various state
      state.setActiveView('library');
      state.setCurrentSessionId('session-1');
      state.setSelectedBlockId('block-1');
      state.setDraftUserMessage('draft');
      state.addTranscriptEntry({ id: '1', role: 'user', content: 'hello' });

      state.reset();

      const resetState = useKnowledgeLibraryStore.getState();
      expect(resetState.activeView).toBe('input');
      expect(resetState.currentSessionId).toBeNull();
      expect(resetState.selectedBlockId).toBeNull();
      expect(resetState.draftUserMessage).toBe('');
      expect(resetState.sessionTranscript).toEqual([]);
    });

    it('preserves expandedCategories', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.expandCategory('docs');
      state.expandCategory('tutorials');

      state.reset();

      const resetState = useKnowledgeLibraryStore.getState();
      expect(resetState.expandedCategories.has('docs')).toBe(true);
      expect(resetState.expandedCategories.has('tutorials')).toBe(true);
    });
  });

  describe('resetSession', () => {
    it('clears session-specific state only', () => {
      const state = useKnowledgeLibraryStore.getState();

      // Set view state (should be preserved)
      state.setActiveView('library');
      state.expandCategory('docs');
      state.setSelectedFilePath('/docs/readme.md');

      // Set session state (should be cleared)
      state.setCurrentSessionId('session-1');
      state.setSelectedBlockId('block-1');
      state.stageUpload(createMockFile());
      state.setProposedNewFile('file.md', {
        title: 'Title',
        overview: createValidOverview(),
        isValid: true,
        errors: [],
      });
      state.addTranscriptEntry({ id: '1', role: 'user', content: 'hello' });
      state.setDraftUserMessage('draft');
      state.setActiveRoutingGroupKey('group-1');

      state.resetSession();

      const resetState = useKnowledgeLibraryStore.getState();

      // Preserved
      expect(resetState.activeView).toBe('library');
      expect(resetState.expandedCategories.has('docs')).toBe(true);
      expect(resetState.selectedFilePath).toBe('/docs/readme.md');

      // Cleared
      expect(resetState.currentSessionId).toBeNull();
      expect(resetState.selectedBlockId).toBeNull();
      expect(resetState.stagedUpload).toBeNull();
      expect(resetState.proposedNewFiles).toEqual({});
      expect(resetState.sessionTranscript).toEqual([]);
      expect(resetState.draftUserMessage).toBe('');
      expect(resetState.activeRoutingGroupKey).toBeNull();
    });
  });

  // ==========================================================================
  // Selectors
  // ==========================================================================

  describe('selectHasStagedUpload', () => {
    it('returns false when no staged upload', () => {
      const state = useKnowledgeLibraryStore.getState();
      expect(selectHasStagedUpload(state)).toBe(false);
    });

    it('returns true when file is staged', () => {
      const state = useKnowledgeLibraryStore.getState();
      state.stageUpload(createMockFile());
      expect(selectHasStagedUpload(useKnowledgeLibraryStore.getState())).toBe(true);
    });
  });

  describe('selectInvalidProposedFilesCount', () => {
    it('returns 0 when no proposed files', () => {
      const state = useKnowledgeLibraryStore.getState();
      expect(selectInvalidProposedFilesCount(state)).toBe(0);
    });

    it('counts invalid files correctly', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setProposedNewFile('valid.md', {
        title: 'Valid',
        overview: createValidOverview(),
        isValid: true,
        errors: [],
      });

      state.setProposedNewFile('invalid1.md', {
        title: '',
        overview: 'short',
        isValid: true,
        errors: [],
      });

      state.setProposedNewFile('invalid2.md', {
        title: 'Title',
        overview: 'no heading',
        isValid: true,
        errors: [],
      });

      expect(selectInvalidProposedFilesCount(useKnowledgeLibraryStore.getState())).toBe(2);
    });
  });

  describe('selectAllProposedFilesValid', () => {
    it('returns true when no proposed files', () => {
      const state = useKnowledgeLibraryStore.getState();
      expect(selectAllProposedFilesValid(state)).toBe(true);
    });

    it('returns true when all files are valid', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setProposedNewFile('valid1.md', {
        title: 'Valid 1',
        overview: createValidOverview(),
        isValid: true,
        errors: [],
      });

      state.setProposedNewFile('valid2.md', {
        title: 'Valid 2',
        overview: createValidOverview(),
        isValid: true,
        errors: [],
      });

      expect(selectAllProposedFilesValid(useKnowledgeLibraryStore.getState())).toBe(true);
    });

    it('returns false when any file is invalid', () => {
      const state = useKnowledgeLibraryStore.getState();

      state.setProposedNewFile('valid.md', {
        title: 'Valid',
        overview: createValidOverview(),
        isValid: true,
        errors: [],
      });

      state.setProposedNewFile('invalid.md', {
        title: '',
        overview: 'invalid',
        isValid: true,
        errors: [],
      });

      expect(selectAllProposedFilesValid(useKnowledgeLibraryStore.getState())).toBe(false);
    });
  });
});
