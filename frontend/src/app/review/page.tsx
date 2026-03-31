"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { pollReviewStatus } from "@/services/api";
import type {
  ContractReviewReport,
  ReviewStatusResponse,
  RiskAssessment,
  SubmitReviewResponse,
} from "@/types";

import { FileUpload } from "@/components/review/FileUpload";
import { ReviewStepper } from "@/components/review/ReviewStepper";
import { HumanReviewGate } from "@/components/review/HumanReviewGate";
import { FinalReport } from "@/components/review/FinalReport";
import { useDemoMode } from "@/hooks/useDemoMode";
import { DEMO_REVIEW_CONTRACT_TEXT, DEMO_REVIEW_RISK } from "@/demo/mock-data";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

function coerceRiskAssessment(
  value: ReviewStatusResponse["risk_assessment"] | undefined,
): RiskAssessment | null {
  const v = value as unknown as RiskAssessment | undefined;
  if (!v) return null;
  if (!Array.isArray(v.high_risks) || !Array.isArray(v.medium_risks)) return null;
  if (typeof v.summary !== "string") return null;
  return v;
}

export default function ReviewPage() {
  const queryClient = useQueryClient();
  const { isDemo } = useDemoMode();
  const [demoStatus, setDemoStatus] = useState<
    "idle" | "in_progress" | "waiting_human_review" | "completed"
  >("idle");
  const [demoRisk, setDemoRisk] = useState<RiskAssessment | null>(null);
  const [demoReport, setDemoReport] = useState<ContractReviewReport | null>(null);

  const [threadId, setThreadId] = useState<string>(() => {
    if (typeof window === "undefined") return "";
    return localStorage.getItem("legal_ai_review_thread_id") || "";
  });
  const [, setSubmitResp] = useState<SubmitReviewResponse | null>(null);

  useEffect(() => {
    if (threadId) localStorage.setItem("legal_ai_review_thread_id", threadId);
  }, [threadId]);

  const statusQuery = useQuery({
    queryKey: ["reviewStatus", threadId],
    enabled: Boolean(threadId),
    queryFn: () => pollReviewStatus(threadId),
    refetchInterval: (query) => {
      const status = (query.state.data as ReviewStatusResponse | undefined)?.status;
      if (!status) return 2000;
      if (
        status === "waiting_human_review" ||
        status === "completed" ||
        status === "not_found"
      ) {
        return false;
      }
      return 2000;
    },
  });

  const status = statusQuery.data?.status;
  const riskAssessment = useMemo(
    () => coerceRiskAssessment(statusQuery.data?.risk_assessment),
    [statusQuery.data?.risk_assessment],
  );
  const effectiveStatus = isDemo
    ? demoStatus === "idle"
      ? undefined
      : demoStatus
    : status;
  const effectiveRisk = isDemo ? demoRisk : riskAssessment;
  const effectiveReport = isDemo ? demoReport : statusQuery.data?.report;

  const resetReview = () => {
    localStorage.removeItem("legal_ai_review_thread_id");
    setThreadId("");
    setDemoStatus("idle");
    setDemoRisk(null);
    setDemoReport(null);
  };

  const startDemoFlow = () => {
    const demoThread = `demo_review_${Date.now().toString().slice(-6)}`;
    setThreadId(demoThread);
    setDemoStatus("in_progress");
    setDemoRisk(null);
    setDemoReport(null);
    window.setTimeout(() => {
      setDemoRisk(DEMO_REVIEW_RISK);
      setDemoStatus("waiting_human_review");
    }, 1200);
  };

  const finishDemoFlow = (approved: boolean, comment: string) => {
    const report: ContractReviewReport = {
      summary: "合同审查报告（Demo）",
      risk_assessment: DEMO_REVIEW_RISK,
      critique_notes: [],
      human_decision: {
        approved,
        comment,
        action: approved ? "approve" : "revise",
      },
      final_recommendation: approved
        ? "通过（建议按审查意见修订后签署）"
        : "需进一步修订后重新评估",
    };
    setDemoReport(report);
    setDemoStatus("completed");
  };

  return (
    <div className="flex flex-1 justify-center bg-slate-50 px-4 py-10 text-slate-900 transition-colors">
      <div className="w-full max-w-4xl space-y-6">
        <div className="rounded-2xl border bg-white/70 p-5 shadow-sm backdrop-blur transition-all">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <div className="text-2xl font-semibold tracking-tight">
                合同合规审查 Demo
              </div>
              <div className="text-sm text-slate-600">
                提交合同文本 → 自动审查 → 命中高风险则进入人工复核 → 审批后生成报告
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isDemo ? (
                <Badge className="bg-violet-600 hover:bg-violet-600">Demo Mode</Badge>
              ) : null}
              {threadId ? (
                <Badge variant="secondary" className="font-mono">
                  {threadId}
                </Badge>
              ) : (
                <Badge variant="secondary">等待提交</Badge>
              )}
              {!isDemo && statusQuery.isFetching ? (
                <Badge className="bg-blue-600 hover:bg-blue-600">轮询中…</Badge>
              ) : null}
              {effectiveStatus ? (
                <Badge variant="outline">{effectiveStatus}</Badge>
              ) : null}
            </div>
          </div>
        </div>

        <Separator />

        {!threadId ? (
          <div className="transition-all duration-300 ease-out">
            <FileUpload
              defaultText={isDemo ? DEMO_REVIEW_CONTRACT_TEXT : ""}
              demoMode={isDemo}
              onStartDemo={startDemoFlow}
              onSubmitted={(resp) => {
                setSubmitResp(resp);
                setThreadId(resp.thread_id);
              }}
            />
          </div>
        ) : null}

        {threadId ? (
          <div className="space-y-4 transition-all duration-300 ease-out">
            {statusQuery.isError ? (
              <Alert variant="destructive">
                <AlertTitle>状态查询失败</AlertTitle>
                <AlertDescription>
                  {statusQuery.error instanceof Error
                    ? statusQuery.error.message
                    : "未知错误"}
                </AlertDescription>
              </Alert>
            ) : null}

            {effectiveStatus === "in_progress" ? (
              <div className="transition-all duration-300 ease-out">
                <ReviewStepper status={effectiveStatus} />
              </div>
            ) : null}

            {effectiveStatus === "waiting_human_review" ? (
              <div className="transition-all duration-300 ease-out">
                <HumanReviewGate
                  threadId={threadId}
                  demoMode={isDemo}
                  riskAssessment={effectiveRisk ?? null}
                  onDemoDecision={finishDemoFlow}
                  onApproved={() => {
                    // 审批后继续轮询，直到 completed
                    queryClient.invalidateQueries({
                      queryKey: ["reviewStatus", threadId],
                    });
                  }}
                />
              </div>
            ) : null}

            {effectiveStatus === "completed" && effectiveReport ? (
              <div className="transition-all duration-300 ease-out">
                <FinalReport report={effectiveReport} citations={[]} />
                <div className="mt-3 flex justify-end">
                  <Button variant="outline" onClick={resetReview}>
                    新建审查
                  </Button>
                </div>
              </div>
            ) : null}

            {!isDemo && status === "not_found" ? (
              <Alert variant="destructive">
                <AlertTitle>thread_id 不存在</AlertTitle>
                <AlertDescription>
                  当前 thread 已不存在或后端已清理状态。请返回重新提交合同文本。
                </AlertDescription>
              </Alert>
            ) : null}

            {!effectiveStatus ? (
              <Alert>
                <AlertTitle>处理中</AlertTitle>
                <AlertDescription>
                  正在初始化审查流程并拉取状态，请稍候…
                </AlertDescription>
              </Alert>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

