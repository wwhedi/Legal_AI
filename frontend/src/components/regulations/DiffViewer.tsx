"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RegulationDiffData } from "@/types";

export function DiffViewer({ diff }: { diff: RegulationDiffData }) {
  return (
    <div className="grid gap-3 xl:grid-cols-[1fr_320px_1fr]">
      <Card className="border-slate-200 bg-white/80 shadow-sm">
        <CardHeader>
          <CardTitle>旧法条</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md bg-slate-50 p-3 text-sm leading-6 whitespace-pre-wrap text-slate-700">
            {diff.oldText}
          </div>
        </CardContent>
      </Card>

      <Card className="border-blue-200 bg-blue-50/60 shadow-sm">
        <CardHeader>
          <CardTitle>AI 修订要点</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md bg-white/80 p-3 text-sm leading-6 text-slate-700">
            {diff.aiSummary}
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-200 bg-white/80 shadow-sm">
        <CardHeader>
          <CardTitle>新法条</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md bg-slate-50 p-3 text-sm leading-6 whitespace-pre-wrap text-slate-700">
            {diff.newText}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

