import { createFileRoute, Outlet } from '@tanstack/react-router';

function SystemsLayout() {
  return <Outlet />;
}

export const Route = createFileRoute('/systems')({
  component: SystemsLayout,
});
