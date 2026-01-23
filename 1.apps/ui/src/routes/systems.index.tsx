import { createFileRoute } from '@tanstack/react-router';
import { SystemsPage } from '@/components/views/systems-page';

export const Route = createFileRoute('/systems/')({
  component: SystemsPage,
});
