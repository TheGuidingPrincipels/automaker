import { createFileRoute } from '@tanstack/react-router';
import { SystemDetailPage } from '@/components/views/system-detail-page';

export const Route = createFileRoute('/systems/$systemId')({
  component: SystemDetailPage,
});
