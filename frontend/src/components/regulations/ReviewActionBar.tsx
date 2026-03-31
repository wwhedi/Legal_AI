"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { PendingRegulationViewItem } from "@/types";

export function ReviewActionBar({
  item,
  onApprove,
}: {
  item: PendingRegulationViewItem;
  onApprove: (id: string) => void;
}) {
  return (
    <Card className="border-slate-200 bg-white/80 shadow-sm">
      <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
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
        <Button
          onClick={() => onApprove(item.id)}
          disabled={item.uiStatus === "success"}
        >
          {item.uiStatus === "success" ? "已批准入库" : "批准入库"}
        </Button>
      </CardContent>
    </Card>
  );
}

