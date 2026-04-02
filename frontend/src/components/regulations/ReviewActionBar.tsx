"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PendingRegulationViewItem } from "@/types";

export function ReviewActionBar({
  item,
  onApprove,
  onReject,
  onEdit,
}: {
  item: PendingRegulationViewItem;
  onApprove: (id: string) => void;
  onReject?: (id: string) => void;
  onEdit?: (id: string) => void;
}) {
  return (
    <div className="sticky bottom-4 z-30 rounded-2xl border border-slate-200/80 bg-white/70 px-4 py-3 shadow-lg backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="text-sm font-medium text-slate-800">
            当前审核：{item.regulation_title || item.regulation_id}
          </div>
          <div className="text-xs text-slate-500">
            状态：
            <Badge
              className={`ml-2 ${
                item.uiStatus === "success"
                  ? "bg-emerald-600 hover:bg-emerald-600"
                  : "bg-amber-600 hover:bg-amber-600"
              }`}
            >
              {item.uiStatus === "success" ? "Success" : "Pending Review"}
            </Badge>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" onClick={() => onEdit?.(item.id)} disabled={!onEdit}>
            编辑
          </Button>
          <Button variant="outline" onClick={() => onReject?.(item.id)} disabled={!onReject}>
            退回
          </Button>
          <Button
            className="bg-blue-600 text-white hover:bg-blue-700"
            onClick={() => onApprove(item.id)}
            disabled={item.uiStatus === "success"}
          >
            {item.uiStatus === "success" ? "已批准入库" : "批准入库"}
          </Button>
        </div>
      </div>
    </div>
  );
}

