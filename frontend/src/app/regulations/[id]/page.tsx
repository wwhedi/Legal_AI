"use client";

import Link from "next/link";
import { Fragment, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Check, ChevronRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { approveRegulationChange, fetchPendingRegulations } from "@/services/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DiffViewer } from "@/components/regulations/DiffViewer";
import { ReviewActionBar } from "@/components/regulations/ReviewActionBar";
import { useDemoMode } from "@/hooks/useDemoMode";
import { DEMO_REGULATION_ROWS } from "@/demo/mock-data";
import type {
  PendingRegulationItem,
  PendingRegulationViewItem,
  RegulationDiffData,
} from "@/types";

const WORKFLOW_STEPS = ["法规爬取", "AI 预处理", "人工待审核", "完成入库"] as const;

function stepVisual(
  index: number,
  isSuccess: boolean,
): "done" | "current" | "upcoming" {
  if (isSuccess) return "done";
  if (index < 2) return "done";
  if (index === 2) return "current";
  return "upcoming";
}

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

export default function RegulationDetailPage() {
  const { isDemo } = useDemoMode();
  const params = useParams<{ id: string }>();
  const recordId = decodeURIComponent(params.id);
  const [approving, setApproving] = useState(false);
  const [selectedChangeIndex, setSelectedChangeIndex] = useState<number | null>(null);
  const [showAiPanel, setShowAiPanel] = useState(false);

  const query = useQuery({
    queryKey: ["pendingRegulations"],
    queryFn: () => fetchPendingRegulations({ limit: 100, offset: 0 }),
    enabled: !isDemo,
    refetchInterval: 8000,
  });

  const rows = useMemo<PendingRegulationViewItem[]>(() => {
    if (isDemo) return DEMO_REGULATION_ROWS;
    const items = query.data?.items || [];
    return items.map((item) => ({
      ...item,
      uiStatus: "pending_review",
      diff: buildMockDiff(item),
    }));
  }, [isDemo, query.data]);

  const selected = useMemo(
    () => rows.find((row) => row.id === recordId) ?? null,
    [recordId, rows],
  );

  const approveToSuccess = async (id: string) => {
    if (approving) return;
    if (isDemo) return;
    try {
      setApproving(true);
      await approveRegulationChange(id);
      await query.refetch();
    } catch (e) {
      console.error(e);
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F7FA] p-6 font-sans">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">法规详情</h1>
          <p className="text-sm text-slate-600">
            在此页面查看旧法条、AI 修订要点与新法条，并执行审核入库操作。
          </p>
          {isDemo ? (
            <Badge className="mt-2 bg-violet-600 hover:bg-violet-600">Demo Mode</Badge>
          ) : null}
        </div>
        <Button asChild variant="ghost" className="text-slate-600 hover:text-slate-900">
          <Link href="/regulations">返回列表</Link>
        </Button>
      </div>

      {query.isLoading && !isDemo ? (
        <Alert>
          <AlertTitle>加载中</AlertTitle>
          <AlertDescription>正在拉取法规详情...</AlertDescription>
        </Alert>
      ) : null}

      {query.isError && !isDemo ? (
        <Alert variant="destructive">
          <AlertTitle>加载失败</AlertTitle>
          <AlertDescription>
            {query.error instanceof Error ? query.error.message : "未知错误"}
          </AlertDescription>
        </Alert>
      ) : null}

      {!selected ? (
        <Alert>
          <AlertTitle>未找到记录</AlertTitle>
          <AlertDescription>该法规不在当前待审核列表中，可能已被处理。</AlertDescription>
        </Alert>
      ) : (
        <>
          <div className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 text-sm font-medium text-slate-700">审核工作流</div>
            <div className="flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center md:justify-between md:gap-2">
              {WORKFLOW_STEPS.map((step, idx) => {
                const isSuccess = selected.uiStatus === "success";
                const sv = stepVisual(idx, isSuccess);
                const isDone = sv === "done";
                const isCurrent = sv === "current";
                return (
                  <Fragment key={step}>
                    <div
                      className={`flex min-w-0 flex-1 items-center gap-2 rounded-xl border px-3 py-2.5 text-xs transition-colors md:min-w-[140px] ${
                        isCurrent
                          ? "border-blue-400 bg-blue-50 text-blue-900 shadow-sm ring-2 ring-blue-200"
                          : isDone
                            ? "border-emerald-200 bg-emerald-50/80 text-emerald-900"
                            : "border-dashed border-slate-200 bg-slate-50 text-slate-500"
                      }`}
                    >
                      <span
                        className={`flex size-7 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                          isCurrent
                            ? "bg-blue-600 text-white"
                            : isDone
                              ? "bg-emerald-600 text-white"
                              : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        {isDone ? <Check className="size-4" strokeWidth={3} /> : idx + 1}
                      </span>
                      <span className="min-w-0 font-medium leading-snug">
                        {idx + 1}. {step}
                        {isCurrent ? (
                          <span className="ml-1.5 rounded bg-blue-100 px-1.5 py-0.5 text-[10px] text-blue-700">
                            进行中
                          </span>
                        ) : null}
                      </span>
                    </div>
                    {idx < WORKFLOW_STEPS.length - 1 ? (
                      <ChevronRight
                        className="mx-1 hidden size-6 shrink-0 text-slate-400 md:block"
                        aria-hidden
                      />
                    ) : null}
                  </Fragment>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-slate-500 md:hidden">
              从左至右：法规爬取 → AI 预处理 → 人工待审核 → 完成入库
            </p>
          </div>

          <div className="relative space-y-4 pb-24">
            <DiffViewer
              diff={selected.diff}
              selectedChangeIndex={selectedChangeIndex}
              onSelectChange={(idx) => {
                setSelectedChangeIndex(idx);
                setShowAiPanel(true);
              }}
            />
            {showAiPanel ? (
              <aside className="fixed right-6 top-28 z-20 w-80 rounded-xl border border-slate-200 bg-white/95 p-4 shadow-lg backdrop-blur">
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-sm font-semibold text-slate-800">AI 修订要点</div>
                  <button
                    type="button"
                    className="text-xs text-slate-500 hover:text-slate-700"
                    onClick={() => setShowAiPanel(false)}
                  >
                    收起
                  </button>
                </div>
                <div className="text-sm leading-6 text-slate-700">
                  {selectedChangeIndex !== null ? (
                    <>
                      <div className="mb-2 text-xs text-slate-500">
                        当前定位：第 {selectedChangeIndex + 1} 处变更
                      </div>
                      {selected.diff.aiSummary}
                    </>
                  ) : (
                    "点击任一高亮变更后，查看对应修订说明。"
                  )}
                </div>
              </aside>
            ) : null}
            <ReviewActionBar
              item={selected}
              onApprove={approveToSuccess}
              onEdit={() => {}}
              onReject={() => {}}
            />
          </div>
        </>
      )}
    </div>
  );
}

