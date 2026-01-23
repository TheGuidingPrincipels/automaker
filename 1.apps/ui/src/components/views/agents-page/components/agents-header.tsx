/**
 * Agents Header - Header component for the Agents page
 */

import { Button } from '@/components/ui/button';
import { Plus, Cpu } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { CustomAgentStatus } from '@automaker/types';

interface AgentsHeaderProps {
  agentCount: number;
  onCreateAgent: () => void;
  statusFilter: CustomAgentStatus | 'all';
  onStatusFilterChange: (status: CustomAgentStatus | 'all') => void;
}

export function AgentsHeader({
  agentCount,
  onCreateAgent,
  statusFilter,
  onStatusFilterChange,
}: AgentsHeaderProps) {
  return (
    <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <Cpu className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">Agents</h1>
            <p className="text-xs text-muted-foreground">{agentCount} agents</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Select
            value={statusFilter}
            onValueChange={(value) => onStatusFilterChange(value as CustomAgentStatus | 'all')}
          >
            <SelectTrigger className="w-[130px] h-9">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>

          <Button onClick={onCreateAgent} size="sm">
            <Plus className="mr-2 h-4 w-4" />
            Create Agent
          </Button>
        </div>
      </div>
    </div>
  );
}
