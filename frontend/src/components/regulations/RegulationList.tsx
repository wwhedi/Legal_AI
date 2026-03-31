"use client";

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { PendingRegulationViewItem } from "@/types";

export function RegulationList({
  items,
  selectedId,
  onSelect,
}: {
  items: PendingRegulationViewItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <ScrollArea className="h-[640px] pr-2">
      <div className="space-y-2">
        {items.map((item) => {
          const active = selectedId === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              className={`w-full rounded-lg border p-3 text-left transition-colors ${
                active
                  ? "border-blue-300 bg-blue-50 ring-1 ring-blue-300"
                  : "border-slate-200 bg-white hover:bg-slate-50"
              }`}
            >
              <div className="mb-1 flex items-start justify-between gap-2">
                <div className="font-medium text-slate-800">
                  {item.regulation_title || item.regulation_id}
                </div>
                <Badge
                  className={
                    item.uiStatus === "success"
                      ? "bg-emerald-600 hover:bg-emerald-600"
                      : "bg-amber-600 hover:bg-amber-600"
                  }
                >
                  {item.uiStatus === "success" ? "Success" : "Pending Review"}
                </Badge>
              </div>
              <div className="mb-1 text-xs text-slate-500">
                regulation_id: {item.regulation_id}
              </div>
              <div className="line-clamp-2 text-sm text-slate-700">
                {item.summary || "暂无变更摘要。"}
              </div>
            </button>
          );
        })}
      </div>
    </ScrollArea>
  );
}

