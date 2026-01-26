import { createFileRoute, useParams } from '@tanstack/react-router';
import { KnowledgeSectionPage } from '@/components/views/knowledge-section-page';
import { KnowledgeLibrary } from '@/components/views/knowledge-library';

export const Route = createFileRoute('/knowledge-hub/$section')({
  component: KnowledgeHubSection,
});

function KnowledgeHubSection() {
  const { section } = useParams({ from: '/knowledge-hub/$section' });

  // Route to Knowledge Library for the new section
  if (section === 'knowledge-library') {
    return <KnowledgeLibrary />;
  }

  // Keep existing behavior for other sections
  return <KnowledgeSectionPage />;
}
