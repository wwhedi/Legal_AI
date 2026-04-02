"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { fetchPendingRegulations } from "@/services/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RegulationList } from "@/components/regulations/RegulationList";
import { useDemoMode } from "@/hooks/useDemoMode";
import { DEMO_REGULATION_ROWS } from "@/demo/mock-data";
import type {
  PendingRegulationItem,
  PendingRegulationViewItem,
  RegulationDiffData,
} from "@/types";

function buildMockDiff(item: PendingRegulationItem): RegulationDiffData {
  const title = item.regulation_title || item.regulation_id;
  return {
    oldText:
      `${title}\n第十二条：合同解除前无需通知对方即可立即生效。\n第十三条：违约责任由守约方单方认定。`,
    newText:
      `${title}\n第十二条：合同解除应提前十五日书面通知对方，并说明解除依据。\n第十三条：违约责任认定应基于双方约定及客观证据。`,
    aiSummary:
      "修订将“即时解除”调整为“提前通知+解除依据说明”，并将单方认定改为客观证据导向。整体降低合同解除争议风险，提升条款公平性与可执行性。",
  };
}

export default function RegulationsPage() {
  const router = useRouter();
  const { isDemo } = useDemoMode();
  const query = useQuery({
    queryKey: ["pendingRegulations"],
    queryFn: () => fetchPendingRegulations({ limit: 100, offset: 0 }),
    enabled: !isDemo,
    refetchInterval: 8000,
  });

  const rows = useMemo<PendingRegulationViewItem[]>(() => {
    if (isDemo) return DEMO_REGULATION_ROWS;
    if (!query.data) return [];
    return query.data.items.map((item) => ({
      ...item,
      uiStatus: "pending_review",
      diff: buildMockDiff(item),
    }));
  }, [isDemo, query.data]);

  const pendingRows = useMemo(
    () => rows.filter((r) => r.uiStatus === "pending_review"),
    [rows],
  );
  return (
    <div className="p-6">
      <div className="mb-4">
        <h1 className="text-2xl font-semibold">法规动态库</h1>
        <p className="text-sm text-slate-600">
          待审核法规更新列表。点击任一卡片进入独立详情页查看旧法条、AI 修订要点、新法条及审核操作。
        </p>
        {isDemo ? (
          <Badge className="mt-2 bg-violet-600 hover:bg-violet-600">Demo Mode</Badge>
        ) : null}
      </div>

      {query.isLoading ? (
        <Alert>
          <AlertTitle>加载中</AlertTitle>
          <AlertDescription>正在拉取待审核法规列表...</AlertDescription>
        </Alert>
      ) : null}

      {query.isError ? (
        <Alert variant="destructive">
          <AlertTitle>加载失败</AlertTitle>
          <AlertDescription>
            {query.error instanceof Error ? query.error.message : "未知错误"}
          </AlertDescription>
        </Alert>
      ) : null}

      <Card className="border-slate-100 bg-white shadow-none">
        <CardHeader className="flex flex-row items-center justify-between border-b border-slate-100 pb-4">
          <CardTitle className="text-base font-semibold text-slate-900">待审核</CardTitle>
          <Badge variant="secondary" className="bg-slate-100 font-normal text-slate-700">
            {pendingRows.length} 条
          </Badge>
        </CardHeader>
        <CardContent className="pt-4">
          {pendingRows.length > 0 ? (
            <RegulationList
              items={pendingRows}
              onOpen={(id) => router.push(`/regulations/${id}`)}
            />
          ) : (
            <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
              当前没有待审核法规记录（可能都已标记为 Success）。
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

