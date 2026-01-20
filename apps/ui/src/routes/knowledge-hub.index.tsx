import { createFileRoute } from '@tanstack/react-router';
import { KnowledgeHubPage } from '@/components/views/knowledge-hub-page';

export const Route = createFileRoute('/knowledge-hub/')({
  component: KnowledgeHubPage,
});
