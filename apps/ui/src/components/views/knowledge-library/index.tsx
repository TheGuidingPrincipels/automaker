/**
 * Knowledge Library - Main container with tab navigation
 *
 * Provides three views:
 * - Input Mode: Extract content from documents
 * - Library Browser: Browse and search the library
 * - Query Mode: Ask questions with RAG
 */

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useKnowledgeLibraryStore, type KLActiveView } from '@/store/knowledge-library-store';
import { Upload, FolderOpen, MessageSquare, Library } from 'lucide-react';
import { InputMode } from './components/input-mode';
import { LibraryBrowser } from './components/library-browser';
import { QueryMode } from './components/query-mode';
import { KLConnectionStatus } from './components/kl-connection-status';
import { PhaseStepper } from './components/input-mode/components/phase-stepper';
import { SessionsDropdown } from './components/input-mode/components/sessions-dropdown';
import { useKLHealth, isKLOfflineError } from '@/hooks/queries/use-knowledge-library';
import { useSessionWorkflow } from './hooks/use-session-workflow';

export function KnowledgeLibrary() {
  const { activeView, setActiveView } = useKnowledgeLibraryStore();
  const workflow = useSessionWorkflow();
  const { workflowState, sessionId: currentSessionId, actions } = workflow;
  const {
    data: klHealth,
    isError: isKLError,
    error: klError,
    isLoading: isKLLoading,
  } = useKLHealth();
  const isDisconnected =
    !isKLLoading &&
    (isKLError ||
      isKLOfflineError(klError) ||
      (klHealth?.status && klHealth.status !== 'healthy' && klHealth.status !== 'ok'));

  // Show stepper when there's an active session in input mode
  const showStepper =
    activeView === 'input' &&
    currentSessionId &&
    workflowState !== 'idle' &&
    workflowState !== 'completed' &&
    workflowState !== 'error';

  // Handle session selection from dropdown
  const handleSelectSession = (sessionId: string) => {
    actions.selectSession(sessionId);
  };

  return (
    <Tabs
      value={activeView}
      onValueChange={(v) => setActiveView(v as KLActiveView)}
      className="h-full flex flex-col"
    >
      {/* Header with integrated tabs, stepper, and controls */}
      <div className="flex items-center gap-4 px-4 py-2 border-b shrink-0">
        {/* Title */}
        <div className="flex items-center gap-2 shrink-0">
          <Library className="h-5 w-5" />
          <h1 className="text-lg font-bold">Knowledge Library</h1>
        </div>

        {/* Divider */}
        <div className="h-5 w-px bg-border" />

        {/* Tab Navigation - inline */}
        <TabsList className="shrink-0 h-8">
          <TabsTrigger value="input" className="gap-1.5 text-sm h-7 px-3">
            <Upload className="h-3.5 w-3.5" />
            Input
          </TabsTrigger>
          <TabsTrigger value="library" className="gap-1.5 text-sm h-7 px-3">
            <FolderOpen className="h-3.5 w-3.5" />
            Library
          </TabsTrigger>
          <TabsTrigger value="query" className="gap-1.5 text-sm h-7 px-3">
            <MessageSquare className="h-3.5 w-3.5" />
            Query
          </TabsTrigger>
        </TabsList>

        {/* Phase Stepper - shown during active session */}
        {showStepper && (
          <>
            <div className="h-4 w-px bg-border" />
            <PhaseStepper workflowState={workflowState} compact />
          </>
        )}

        <div className="flex-1" />

        {/* Sessions Dropdown - shown in Input mode */}
        {activeView === 'input' && (
          <SessionsDropdown
            activeSessionId={currentSessionId}
            onSelectSession={handleSelectSession}
          />
        )}

        {/* Connection Status */}
        <KLConnectionStatus showRefresh data-testid="kl-connection-status" />
      </div>

      {/* Disconnection warning */}
      {isDisconnected && (
        <div className="mx-4 mt-2 rounded-md border border-amber-300/60 bg-amber-50/80 px-3 py-2 text-sm text-amber-700 shrink-0">
          Knowledge Library disconnected
        </div>
      )}

      {/* Tab Content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <TabsContent value="input" className="h-full m-0">
          <InputMode workflow={workflow} />
        </TabsContent>
        <TabsContent value="library" className="h-full m-0">
          <LibraryBrowser />
        </TabsContent>
        <TabsContent value="query" className="h-full m-0">
          <QueryMode />
        </TabsContent>
      </div>
    </Tabs>
  );
}
