"use client";

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { PendingRegulationViewItem } from "@/types";

/** 变更时间：YYYY-MM-DD HH:mm */
function formatChangeTime(iso: string | undefined | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${day} ${h}:${min}`;
}

export function RegulationList({
  items,
  onOpen,
}: {
  items: PendingRegulationViewItem[];
  onOpen: (id: string) => void;
}) {
  return (
    <ScrollArea className="h-[calc(100vh-220px)] pr-2">
      <ul className="flex w-full flex-col gap-3">
        {items.map((item) => {
          const changeTime = formatChangeTime(item.updated_at);
          return (
            <li key={item.id} className="border-b border-slate-100 last:border-0">
              <button
                type="button"
                onClick={() => onOpen(item.id)}
                className="group flex w-full max-w-full items-start justify-between gap-4 rounded-lg bg-white px-1 py-1 text-left transition-colors hover:bg-slate-50/90"
              >
                <div className="min-w-0 flex-1">
                  <div className="font-medium leading-snug text-slate-900">
                    {item.regulation_title || item.regulation_id}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    regulation_id: {item.regulation_id}
                  </div>
                  <div className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-slate-600">
                    {item.summary || "暂无变更摘要。"}
                  </div>
                </div>
                <div className="flex shrink-0 flex-row items-center gap-2 sm:gap-3">
                  <div className="flex flex-col items-end gap-0.5 sm:flex-row sm:items-baseline sm:gap-1.5">
                    <span
                      className="whitespace-nowrap text-[11px] font-normal leading-none"
                      style={{ color: "#8C8C8C" }}
                    >
                      变更时间
                    </span>
                    <time
                      dateTime={item.updated_at}
                      aria-label={`变更时间 ${changeTime}`}
                      className="whitespace-nowrap text-[12px] font-normal tabular-nums leading-none"
                      style={{ color: "#8C8C8C" }}
                    >
                      {changeTime}
                    </time>
                  </div>
                  <Badge
                    className={
                      item.uiStatus === "success"
                        ? "shrink-0 bg-emerald-600 font-normal hover:bg-emerald-600"
                        : "shrink-0 bg-amber-600 font-normal hover:bg-amber-600"
                    }
                  >
                    {item.uiStatus === "success" ? "已入库" : "待审核"}
                  </Badge>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </ScrollArea>
  );
}
