import { createFileRoute } from '@tanstack/react-router';
import { KnowledgeSectionPage } from '@/components/views/knowledge-section-page';

export const Route = createFileRoute('/knowledge-hub/$section')({
  component: KnowledgeSectionPage,
});
