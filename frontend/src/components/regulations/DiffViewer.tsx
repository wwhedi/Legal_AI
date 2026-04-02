"use client";

import { useMemo, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RegulationDiffData } from "@/types";

type DiffLine = {
  oldText: string;
  newText: string;
  kind: "unchanged" | "modified" | "added" | "removed";
};

function buildDiffLines(oldText: string, newText: string): DiffLine[] {
  const oldLines = oldText.split("\n");
  const newLines = newText.split("\n");
  const maxLen = Math.max(oldLines.length, newLines.length);
  const rows: DiffLine[] = [];

  for (let i = 0; i < maxLen; i += 1) {
    const oldLine = oldLines[i] ?? "";
    const newLine = newLines[i] ?? "";

    if (oldLine && newLine) {
      rows.push({
        oldText: oldLine,
        newText: newLine,
        kind: oldLine === newLine ? "unchanged" : "modified",
      });
      continue;
    }
    if (!oldLine && newLine) {
      rows.push({ oldText: "", newText: newLine, kind: "added" });
      continue;
    }
    rows.push({ oldText: oldLine, newText: "", kind: "removed" });
  }

  return rows;
}

export function DiffViewer({
  diff,
  onSelectChange,
  selectedChangeIndex,
}: {
  diff: RegulationDiffData;
  onSelectChange?: (index: number) => void;
  selectedChangeIndex?: number | null;
}) {
  const leftRef = useRef<HTMLDivElement | null>(null);
  const rightRef = useRef<HTMLDivElement | null>(null);
  const syncingRef = useRef<"left" | "right" | null>(null);
  const lines = useMemo(() => buildDiffLines(diff.oldText, diff.newText), [diff.oldText, diff.newText]);

  const syncScroll = (source: "left" | "right") => {
    if (syncingRef.current && syncingRef.current !== source) return;
    syncingRef.current = source;
    const from = source === "left" ? leftRef.current : rightRef.current;
    const to = source === "left" ? rightRef.current : leftRef.current;
    if (from && to) {
      to.scrollTop = from.scrollTop;
    }
    requestAnimationFrame(() => {
      syncingRef.current = null;
    });
  };

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader>
          <CardTitle>旧法条</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            ref={leftRef}
            onScroll={() => syncScroll("left")}
            className="h-[62vh] overflow-auto rounded-md bg-slate-50 p-3 text-sm leading-7 text-slate-700"
          >
            <div className="space-y-2">
              {lines.map((line, idx) => {
                const clickable = line.kind !== "unchanged";
                const active = selectedChangeIndex === idx;
                return (
                  <button
                    key={`old-${idx}`}
                    type="button"
                    disabled={!clickable}
                    onClick={() => onSelectChange?.(idx)}
                    className={`block w-full rounded px-2 py-1 text-left transition ${
                      line.kind === "modified" || line.kind === "removed"
                        ? "bg-rose-50 text-rose-900 line-through"
                        : "bg-transparent"
                    } ${active ? "ring-2 ring-blue-300" : ""} ${
                      clickable ? "hover:bg-rose-100" : ""
                    }`}
                  >
                    {line.oldText || " "}
                  </button>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader>
          <CardTitle>新法条</CardTitle>
        </CardHeader>
        <CardContent>
          <div
            ref={rightRef}
            onScroll={() => syncScroll("right")}
            className="h-[62vh] overflow-auto rounded-md bg-slate-50 p-3 text-sm leading-7 text-slate-700"
          >
            <div className="space-y-2">
              {lines.map((line, idx) => {
                const clickable = line.kind !== "unchanged";
                const active = selectedChangeIndex === idx;
                return (
                  <button
                    key={`new-${idx}`}
                    type="button"
                    disabled={!clickable}
                    onClick={() => onSelectChange?.(idx)}
                    className={`block w-full rounded px-2 py-1 text-left transition ${
                      line.kind === "modified" || line.kind === "added"
                        ? "bg-emerald-50 text-emerald-900"
                        : "bg-transparent"
                    } ${active ? "ring-2 ring-blue-300" : ""} ${
                      clickable ? "hover:bg-emerald-100" : ""
                    }`}
                  >
                    {line.newText || " "}
                  </button>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

