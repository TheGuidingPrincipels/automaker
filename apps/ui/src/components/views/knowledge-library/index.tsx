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
import { useKLHealth, isKLOfflineError } from '@/hooks/queries/use-knowledge-library';

export function KnowledgeLibrary() {
  const { activeView, setActiveView } = useKnowledgeLibraryStore();
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

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b shrink-0">
        <div className="flex items-center gap-2">
          <Library className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Knowledge Library</h1>
        </div>
        <KLConnectionStatus showRefresh data-testid="kl-connection-status" />
      </div>
      {isDisconnected && (
        <div className="mx-4 mt-2 rounded-md border border-amber-300/60 bg-amber-50/80 px-3 py-2 text-sm text-amber-700 shrink-0">
          Knowledge Library disconnected
        </div>
      )}

      {/* Tab Navigation */}
      <Tabs
        value={activeView}
        onValueChange={(v) => setActiveView(v as KLActiveView)}
        className="flex-1 flex flex-col min-h-0"
      >
        <TabsList className="mx-4 mt-4 shrink-0">
          <TabsTrigger value="input" className="gap-2">
            <Upload className="h-4 w-4" />
            Input
          </TabsTrigger>
          <TabsTrigger value="library" className="gap-2">
            <FolderOpen className="h-4 w-4" />
            Library
          </TabsTrigger>
          <TabsTrigger value="query" className="gap-2">
            <MessageSquare className="h-4 w-4" />
            Query
          </TabsTrigger>
        </TabsList>

        <div className="flex-1 min-h-0 overflow-hidden">
          <TabsContent value="input" className="h-full m-0">
            <InputMode />
          </TabsContent>
          <TabsContent value="library" className="h-full m-0">
            <LibraryBrowser />
          </TabsContent>
          <TabsContent value="query" className="h-full m-0">
            <QueryMode />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
