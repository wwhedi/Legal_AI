"use client";

import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Bot, RotateCcw, Send, Trash2, Upload, User, X } from "lucide-react";

import { askLegalQuestion } from "@/services/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useDemoMode } from "@/hooks/useDemoMode";
import { buildDemoAssistantPayload, DEMO_QA_QUESTION, resolveDemoChatScenario } from "@/demo/mock-data";
import {
  useChatSessions,
  type CitationDetail,
  type ChatMessage,
} from "@/contexts/chat-sessions-context";
import type { Citation } from "@/types";
import {
  formatCitationSummaryLine,
  inferLawEffectKind,
  lawEffectTagClasses,
  verificationLabelZh,
  verifySourceLabelZh,
} from "@/lib/citation-styles";
import { sanitizeAssistantAnswerText, sanitizeMarkdownPart, splitCitationParts } from "@/lib/assistant-text";

function finalizeAssistantContent(raw: string): string {
  return sanitizeAssistantAnswerText(raw);
}

/** 合并仅含标点的独立行，避免 Markdown 分段产生孤行标点 */
function normalizeMarkdownLines(lines: string[]): string[] {
  const out: string[] = [];
  const loneLine = /^[。．，、；：！？\s,.!?;:：]+$/;
  for (const line of lines) {
    const t = line.trim();
    if (!t) {
      out.push("");
      continue;
    }
    if (loneLine.test(t) && out.length > 0 && out[out.length - 1] !== "") {
      out[out.length - 1] = `${out[out.length - 1].trimEnd()}${t}`;
    } else {
      out.push(line);
    }
  }
  return out;
}

function renderInlineMarkdown(text: string) {
  const chunks = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return chunks.map((chunk, idx) => {
    const bold = /^\*\*[^*]+\*\*$/.test(chunk);
    if (!bold) return <Fragment key={idx}>{chunk}</Fragment>;
    return <strong key={idx}>{chunk.slice(2, -2)}</strong>;
  });
}

function renderMarkdownBlocks(text: string) {
  const sanitized = sanitizeMarkdownPart(text || "").trim();
  if (/^[。．]+$/.test(sanitized)) {
    return <span className="inline">{sanitized}</span>;
  }
  const lines = normalizeMarkdownLines(sanitized.split("\n"));
  const nodes: JSX.Element[] = [];
  let pendingBullets: string[] = [];

  const flushBullets = (key: string) => {
    if (!pendingBullets.length) return;
    nodes.push(
      <ul
        key={key}
        className="mb-4 list-outside list-disc space-y-3 pl-6 text-[0.95em] leading-relaxed marker:text-slate-400"
      >
        {pendingBullets.map((item, idx) => (
          <li key={`${key}-${idx}`} className="pl-1 [&_button]:mx-0.5 [&_button]:align-baseline">
            {renderInlineMarkdown(item)}
          </li>
        ))}
      </ul>,
    );
    pendingBullets = [];
  };

  lines.forEach((line, idx) => {
    const bullet = /^\s*[-*]\s+(.+)$/.exec(line);
    if (bullet) {
      pendingBullets.push(bullet[1]);
      return;
    }
    flushBullets(`list-${idx}`);
    if (!line.trim()) {
      nodes.push(<div key={`gap-${idx}`} className="h-3" />);
      return;
    }
    nodes.push(
      <p key={`p-${idx}`} className="mb-3 leading-7 [&_button]:mx-0.5 [&_button]:align-baseline">
        {renderInlineMarkdown(line)}
      </p>,
    );
  });
  flushBullets("list-end");
  return nodes;
}

const EMPTY_MESSAGES: ChatMessage[] = [];

function getLawMetaForRef(
  refId: string,
  citations: Citation[] | undefined,
  detail: CitationDetail | undefined,
): Pick<Citation, "status" | "status_display"> {
  const c = citations?.find((x) => x.ref_id === refId);
  if (c) return { status: c.status, status_display: c.status_display };
  return {
    status: undefined,
    status_display: detail?.evidence_status_display,
  };
}

export default function ChatPage() {
  const { isDemo } = useDemoMode();
  const { activeSession, updateActiveSession } = useChatSessions();

  const messages = activeSession?.messages ?? EMPTY_MESSAGES;
  const citationDetails = activeSession?.citationDetails ?? {};

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedRef, setSelectedRef] = useState<string | null>(null);
  const [isCitationPanelOpen, setIsCitationPanelOpen] = useState(false);
  const [lastQuestion, setLastQuestion] = useState("");
  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const openCitationPanel = (ref: string) => {
    setSelectedRef(ref);
    setIsCitationPanelOpen(true);
  };

  const send = async (question?: string) => {
    const q = (question ?? input).trim();
    if (!q || loading || !activeSession) return;
    const userMsg: ChatMessage = { id: `u_${Date.now()}`, role: "user", content: q };
    const base = [...messages, userMsg];
    const titleFromUser = q.length > 24 ? `${q.slice(0, 24)}…` : q;
    updateActiveSession({
      messages: base,
      title: titleFromUser,
      updatedAt: Date.now(),
    });
    setInput("");
    setLastQuestion(q);
    setLoading(true);
    await new Promise((r) => setTimeout(r, 450));

    const mocked = isDemo
      ? buildDemoAssistantPayload(resolveDemoChatScenario(q))
      : await (async () => {
          const resp = await askLegalQuestion({ question: q });
          const verificationMap = new Map<string, Record<string, unknown>>();
          (resp.verification_details || []).forEach((item) => {
            const raw = String(item?.raw ?? "");
            if (raw) verificationMap.set(raw, item);
          });
          const details = (resp.citations || []).map((c) => ({
            ref_id: c.ref_id,
            law_name: c.law_name ? `《${c.law_name}》` : "法规依据",
            article: c.article ? `第${c.article}条` : "条款待核验",
            evidence_status_display: c.status_display || undefined,
            status: c.verified === false ? ("Unverified" as const) : ("Verified" as const),
            verify_source: c.verify_source,
            excerpt:
              c.verified === false
                ? "该引用未通过自动校验，请人工复核后再作为依据使用。"
                : "该引用已通过自动校验。",
          }));
          details.forEach((d) => {
            const v = verificationMap.get(d.ref_id);
            if (!v) return;
            const evidence = v.fallback_evidence as Record<string, unknown> | undefined;
            if (evidence?.text && typeof evidence.text === "string") {
              d.excerpt = evidence.text.slice(0, 220);
            }
          });
          return {
            content: finalizeAssistantContent(resp.answer),
            citations: resp.citations || [],
            details,
            answerNeedsHumanReview: resp.answer_needs_human_review,
          };
        })().catch(() => buildDemoAssistantPayload(resolveDemoChatScenario(q)));
    const assistantId = `a_${Date.now()}`;
    const finalContent = finalizeAssistantContent(mocked.content);
    const assistantShell: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      citations: mocked.citations,
      answerNeedsHumanReview: mocked.answerNeedsHumanReview,
    };

    for (let i = 1; i <= finalContent.length; i += 4) {
      const next = finalContent.slice(0, i);
      updateActiveSession({
        messages: [...base, { ...assistantShell, content: next }],
        updatedAt: Date.now(),
      });
      await new Promise((r) => setTimeout(r, 20));
    }

    const mergedDetails: Record<string, CitationDetail> = {
      ...(activeSession.citationDetails ?? {}),
    };
    mocked.details.forEach((d) => {
      mergedDetails[d.ref_id] = d;
    });
    updateActiveSession({
      messages: [...base, { ...assistantShell, content: finalContent }],
      citationDetails: mergedDetails,
      updatedAt: Date.now(),
    });
    setLoading(false);
  };

  useEffect(() => {
    const el = chatScrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages.length, loading, messages]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const maxHeight = Math.floor(window.innerHeight * 0.3);
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
  }, [input]);

  useEffect(() => {
    if (!isDemo || !activeSession) return;
    if (activeSession.messages.length > 0) return;
    const seeded = buildDemoAssistantPayload(resolveDemoChatScenario(DEMO_QA_QUESTION));
    const userMsg: ChatMessage = {
      id: "demo_user",
      role: "user",
      content: DEMO_QA_QUESTION,
    };
    const assistantMsg: ChatMessage = {
      id: "demo_assistant",
      role: "assistant",
      content: seeded.content,
      citations: seeded.citations,
      answerNeedsHumanReview: seeded.answerNeedsHumanReview,
    };
    const seededDetails: Record<string, CitationDetail> = {};
    seeded.details.forEach((d) => {
      seededDetails[d.ref_id] = d;
    });
    updateActiveSession({
      messages: [userMsg, assistantMsg],
      citationDetails: seededDetails,
      title: "演示对话",
      updatedAt: Date.now(),
    });
  }, [isDemo, activeSession, updateActiveSession]);

  const headerSubtitle = useMemo(
    () => (isDemo ? "Demo 模式 · 智能问答与法条检索" : "智能问答与法条检索"),
    [isDemo],
  );

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden bg-[#F9FAFB] text-slate-900">
      <header className="sticky top-0 z-10 flex shrink-0 items-center justify-between border-b border-slate-200/80 bg-[#F9FAFB]/90 px-4 py-2 backdrop-blur-md">
        <div className="flex min-w-0 items-center gap-2">
          <Bot className="size-5 shrink-0 text-blue-600" />
          <div className="min-w-0">
            <h1 className="truncate text-base font-semibold leading-tight">法律 AI 助手</h1>
            <p className="truncate text-xs text-slate-500">{headerSubtitle}</p>
          </div>
        </div>
        {isDemo ? (
          <Badge className="shrink-0 bg-violet-600 hover:bg-violet-600">Demo</Badge>
        ) : null}
      </header>

      <div className="relative min-h-0 flex-1 overflow-hidden">
        <div
          ref={chatScrollRef}
          className="h-full overflow-y-auto px-4 pb-40 pt-3"
        >
          <div className="mx-auto max-w-[900px] space-y-4">
            {messages.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-500">
                请输入法律问题，例如：自动续约条款是否存在合规风险？
              </p>
            ) : null}
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex max-w-[min(92%,900px)] gap-2.5 text-sm ${
                  m.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
                }`}
              >
                <div
                  className={`mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full ${
                    m.role === "user"
                      ? "bg-blue-100 text-blue-700"
                      : "bg-slate-200/90 text-slate-600"
                  }`}
                  aria-hidden
                >
                  {m.role === "user" ? <User className="size-4" /> : <Bot className="size-4" />}
                </div>
                <div
                  className={`min-w-0 flex-1 ${
                    m.role === "user"
                      ? "rounded-3xl bg-blue-600 px-4 py-3 text-white shadow-sm"
                      : "rounded-3xl bg-slate-100/70 px-4 py-3 text-slate-800"
                  }`}
                >
                  <div className="leading-[1.7] text-pretty [word-break:keep-all]">
                    {m.role === "assistant"
                      ? splitCitationParts(m.content).map((part, idx) => {
                          const isRef = /^\[\d+\]$/.test(part);
                          if (!isRef) {
                            if (!part.trim()) return null;
                            return (
                              <span key={`${m.id}-${idx}`} className="inline">
                                {renderMarkdownBlocks(part)}
                              </span>
                            );
                          }
                          const tip = citationDetails[part];
                          const lawMeta = getLawMetaForRef(part, m.citations, tip);
                          const kind = inferLawEffectKind(lawMeta);
                          const tag = lawEffectTagClasses(kind);
                          return (
                            <span key={`${m.id}-${idx}`} className="group relative mx-1 inline-block align-baseline">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  openCitationPanel(part);
                                }}
                                className={`rounded-md px-2 py-0.5 text-xs font-semibold shadow-sm ring-1 transition duration-300 hover:scale-[1.06] hover:shadow-lg hover:brightness-105 motion-reduce:hover:scale-100 ${tag.bg} ${tag.text} ${tag.ring}`}
                              >
                                {part}
                              </button>
                              {tip ? (
                                <span className="pointer-events-none invisible absolute bottom-full left-1/2 z-30 mb-2 w-56 -translate-x-1/2 rounded-xl border border-white/70 bg-white/80 px-3 py-2 text-left text-xs text-slate-700 opacity-0 shadow-lg backdrop-blur-md transition group-hover:visible group-hover:opacity-100">
                                  {tip.law_name} {tip.article}
                                </span>
                              ) : null}
                            </span>
                          );
                        })
                      : m.content}
                  </div>
                  {m.citations?.length ? (
                    <div className="mt-4 flex flex-col gap-2 border-t border-slate-200/80 pt-3">
                      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        引用汇总
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {m.citations.map((c) => {
                          const kind = inferLawEffectKind(c);
                          const tag = lawEffectTagClasses(kind);
                          return (
                            <button
                              type="button"
                              key={`${m.id}-${c.ref_id}`}
                              onClick={() => openCitationPanel(c.ref_id)}
                              className={`rounded-md px-2.5 py-1.5 text-left text-xs font-medium shadow-sm ring-1 transition hover:scale-[1.02] hover:shadow-md ${tag.bg} ${tag.text} ${tag.ring}`}
                            >
                              {formatCitationSummaryLine(c)}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ) : null}
                  {m.role === "assistant" && m.answerNeedsHumanReview ? (
                    <Alert className="mt-3 border-amber-300 bg-amber-50">
                      <AlertTitle>需要人工复核</AlertTitle>
                      <AlertDescription>
                        引用中存在未通过校验项，请法务复核后再作为最终结论使用。
                      </AlertDescription>
                    </Alert>
                  ) : null}
                </div>
              </div>
            ))}
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                助手正在检索法规并生成回答
                <span className="inline-flex gap-1">
                  <span className="size-1.5 animate-pulse rounded-full bg-slate-400" />
                  <span className="size-1.5 animate-pulse rounded-full bg-slate-400 [animation-delay:120ms]" />
                  <span className="size-1.5 animate-pulse rounded-full bg-slate-400 [animation-delay:240ms]" />
                </span>
              </div>
            ) : null}
          </div>
        </div>

        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center px-4 pb-4 pt-10">
          <div className="pointer-events-auto w-full max-w-[900px] rounded-2xl border border-slate-200/80 bg-white/85 p-3 shadow-[0_8px_30px_rgb(0,0,0,0.08)] backdrop-blur-xl">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入你的法律问题..."
              className="max-h-[30vh] min-h-[52px] resize-none border-none bg-transparent p-1 leading-7 shadow-none focus-visible:ring-0"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send();
                }
              }}
            />
            <p className="mt-1.5 px-1 text-center text-[11px] text-slate-400">
              Enter 发送 · Shift+Enter 换行
            </p>
            <div className="mt-2 flex items-center justify-between border-t border-slate-100 pt-2">
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    updateActiveSession({
                      messages: [],
                      citationDetails: {},
                      title: "新对话",
                      updatedAt: Date.now(),
                    });
                    setSelectedRef(null);
                    setIsCitationPanelOpen(false);
                  }}
                  title="清除对话"
                >
                  <Trash2 className="size-4" />
                </Button>
                <Button variant="ghost" size="icon" onClick={() => {}} title="上传文档">
                  <Upload className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => void send(lastQuestion)}
                  disabled={!lastQuestion || loading}
                  title="重新生成"
                >
                  <RotateCcw className="size-4" />
                </Button>
              </div>
              <Button
                className="rounded-xl bg-blue-600 hover:bg-blue-700"
                onClick={() => void send()}
                disabled={loading || input.trim().length === 0}
              >
                <Send className="mr-1 size-4" />
                {loading ? "发送中..." : "发送"}
              </Button>
            </div>
          </div>
        </div>
      </div>

      <aside
        className={`will-change-transform fixed inset-y-0 right-0 z-40 flex w-[min(380px,92vw)] flex-col border-l border-slate-200/80 bg-white/95 shadow-[-8px_0_30px_rgba(0,0,0,0.06)] backdrop-blur-xl transition-transform duration-300 ease-out motion-reduce:transition-none ${
          isCitationPanelOpen ? "translate-x-0" : "translate-x-full"
        }`}
        aria-hidden={!isCitationPanelOpen}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <div className="text-sm font-semibold text-slate-800">引用详情</div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-8"
            onClick={() => setIsCitationPanelOpen(false)}
            aria-label="关闭"
          >
            <X className="size-4" />
          </Button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
          {!selectedRef ? (
            <Alert>
              <AlertTitle>未选中引用</AlertTitle>
              <AlertDescription>
                点击回答中的 [1]/[2] 或引用标签，从右侧查看法条详情与校验状态。
              </AlertDescription>
            </Alert>
          ) : null}

          {selectedRef && citationDetails[selectedRef] ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2">
                <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-xs text-slate-600">
                  {selectedRef}
                </span>
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    citationDetails[selectedRef].status === "Verified"
                      ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/80"
                      : "bg-amber-50 text-amber-800 ring-1 ring-amber-200/80"
                  }`}
                >
                  {verificationLabelZh(citationDetails[selectedRef].status === "Verified")}
                </span>
              </div>
              <Separator />
              <div className="space-y-3">
                <h2 className="text-lg font-bold leading-snug text-slate-900">
                  {citationDetails[selectedRef].law_name} {citationDetails[selectedRef].article}
                </h2>
                {citationDetails[selectedRef].evidence_status_display ? (
                  <div className="text-sm text-slate-600">
                    法律状态：{citationDetails[selectedRef].evidence_status_display}
                  </div>
                ) : null}
                {citationDetails[selectedRef].verify_source ? (
                  <div className="text-xs text-slate-500">
                    校验来源：{verifySourceLabelZh(citationDetails[selectedRef].verify_source)}
                  </div>
                ) : null}
                <div className="rounded-xl bg-slate-50/90 p-4 text-[15px] leading-[1.65] text-slate-800">
                  {citationDetails[selectedRef].excerpt}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
