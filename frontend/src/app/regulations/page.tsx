"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchPendingRegulations } from "@/services/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DiffViewer } from "@/components/regulations/DiffViewer";
import { RegulationList } from "@/components/regulations/RegulationList";
import { ReviewActionBar } from "@/components/regulations/ReviewActionBar";
import { useDemoMode } from "@/hooks/useDemoMode";
import { DEMO_REGULATION_ROWS } from "@/demo/mock-data";
import type {
  PendingRegulationItem,
  PendingRegulationViewItem,
  RegulationDiffData,
} from "@/types";
import { approveRegulationChange } from "@/services/api";

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
  const { isDemo } = useDemoMode();
  const query = useQuery({
    queryKey: ["pendingRegulations"],
    queryFn: () => fetchPendingRegulations({ limit: 100, offset: 0 }),
    enabled: !isDemo,
    refetchInterval: 8000,
  });

  const [rows, setRows] = useState<PendingRegulationViewItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    if (isDemo) {
      setRows(DEMO_REGULATION_ROWS);
      setSelectedId(DEMO_REGULATION_ROWS[0]?.id ?? null);
      return;
    }
    if (!query.data) return;
    const nextRows: PendingRegulationViewItem[] = query.data.items.map((item) => ({
      ...item,
      uiStatus: "pending_review",
      diff: buildMockDiff(item),
    }));
    setRows(nextRows);
    if (!selectedId && nextRows.length > 0) {
      setSelectedId(nextRows[0].id);
    }
  }, [isDemo, query.data, selectedId]);

  const pendingRows = useMemo(
    () => rows.filter((r) => r.uiStatus === "pending_review"),
    [rows],
  );
  const selected = useMemo(
    () => rows.find((r) => r.id === selectedId) ?? null,
    [rows, selectedId],
  );

  const approveToSuccess = async (id: string) => {
    if (isDemo) return;
    if (approving) return;
    try {
      setApproving(true);
      await approveRegulationChange(id);
      setSelectedId(null);
      // 以后端为准刷新 pending 列表（approved 的记录会从 /pending 中消失）
      await query.refetch();
    } catch (e) {
      // 简化：这里不引入新的 toast 依赖，只在控制台打印错误
      console.error(e);
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-4">
        <h1 className="text-2xl font-semibold">法规动态库</h1>
        <p className="text-sm text-slate-600">
          待审核法规更新列表 + 旧新条文对比 + AI 修订要点 + 审核入库操作（Demo）。
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

      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <Card className="border-slate-200 bg-white/80 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Pending Review</CardTitle>
            <Badge>{pendingRows.length} 条</Badge>
          </CardHeader>
          <CardContent>
            {pendingRows.length > 0 ? (
              <RegulationList
                items={pendingRows}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            ) : (
              <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
                当前没有待审核法规记录（可能都已标记为 Success）。
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          {selected ? (
            <>
              <DiffViewer diff={selected.diff} />
              <ReviewActionBar item={selected} onApprove={approveToSuccess} />
            </>
          ) : (
            <Alert>
              <AlertTitle>未选中条目</AlertTitle>
              <AlertDescription>
                请从左侧 Pending Review 列表选择一个法规变更条目查看对比详情。
              </AlertDescription>
            </Alert>
          )}
        </div>
      </div>
    </div>
  );
}

