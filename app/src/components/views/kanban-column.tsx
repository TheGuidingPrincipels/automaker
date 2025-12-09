"use client";

import { useDroppable } from "@dnd-kit/core";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface KanbanColumnProps {
  id: string;
  title: string;
  color: string;
  count: number;
  children: ReactNode;
  isDoubleWidth?: boolean;
  headerAction?: ReactNode;
}

export function KanbanColumn({
  id,
  title,
  color,
  count,
  children,
  isDoubleWidth = false,
  headerAction,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex flex-col h-full rounded-lg bg-zinc-900/50 backdrop-blur-sm border border-white/5 transition-colors",
        isDoubleWidth ? "w-[37rem]" : "w-72",
        isOver && "bg-zinc-800/50"
      )}
      data-testid={`kanban-column-${id}`}
    >
      {/* Column Header */}
      <div className="flex items-center gap-2 p-3 border-b border-white/5">
        <div className={cn("w-3 h-3 rounded-full", color)} />
        <h3 className="font-medium text-sm flex-1">{title}</h3>
        {headerAction}
        <span className="text-xs text-muted-foreground bg-background px-2 py-0.5 rounded-full">
          {count}
        </span>
      </div>

      {/* Column Content */}
      <div
        className={cn(
          "flex-1 overflow-y-auto p-2",
          isDoubleWidth
            ? "columns-2 gap-2 [&>*]:break-inside-avoid [&>*]:mb-2"
            : "space-y-2"
        )}
      >
        {children}
      </div>
    </div>
  );
}
