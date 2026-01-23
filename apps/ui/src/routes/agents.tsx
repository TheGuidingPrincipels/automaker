import { createFileRoute } from '@tanstack/react-router';
import { AgentsPage } from '@/components/views/agents-page';

export const Route = createFileRoute('/agents')({
  component: AgentsPage,
});
