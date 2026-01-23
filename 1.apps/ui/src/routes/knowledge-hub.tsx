import { createFileRoute, Outlet } from '@tanstack/react-router';

function KnowledgeHubLayout() {
  return <Outlet />;
}

export const Route = createFileRoute('/knowledge-hub')({
  component: KnowledgeHubLayout,
});
