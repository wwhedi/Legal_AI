"use client";

import { useEffect, useState } from "react";
import { Bot } from "lucide-react";

import type { Citation } from "@/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useDemoMode } from "@/hooks/useDemoMode";
import {
  DEMO_QA_ANSWER,
  DEMO_QA_CITATION_DETAILS,
  DEMO_QA_CITATIONS,
  DEMO_QA_QUESTION,
} from "@/demo/mock-data";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

type CitationDetail = {
  ref_id: string;
  law_name: string;
  article: string;
  status: "Verified" | "Unverified";
  excerpt: string;
};

function mockAssistantAnswer(question: string): {
  content: string;
  citations: Citation[];
  details: CitationDetail[];
} {
  return {
    content:
      `针对你的问题“${question}”，初步结论是：应重点审查合同中的权利义务对等性与提示义务。` +
      "若包含自动续约、免责、单方解除条款，建议结合《民法典》格式条款规则核对显著提示与合理说明义务[1]。" +
      "对于解除权触发条件，建议约定客观标准并保留通知与救济期，避免条款失衡导致争议[2]。",
    citations: [
      {
        ref_id: "[1]",
        law_name: "民法典",
        article: "496",
        status: "effective",
        score: 0.88,
      },
      {
        ref_id: "[2]",
        law_name: "民法典",
        article: "563",
        status: "effective",
        score: 0.83,
      },
    ],
    details: [
      {
        ref_id: "[1]",
        law_name: "《民法典》",
        article: "第496条",
        status: "Verified",
        excerpt:
          "提供格式条款的一方应当遵循公平原则确定当事人之间的权利和义务，并采取合理方式提示对方注意免除或者减轻其责任等与对方有重大利害关系的条款。",
      },
      {
        ref_id: "[2]",
        law_name: "《民法典》",
        article: "第563条",
        status: "Verified",
        excerpt:
          "当事人一方迟延履行主要债务，经催告后在合理期限内仍未履行等法定情形下，对方可以解除合同。解除应满足法定或约定条件。",
      },
    ],
  };
}

function demoAssistantAnswer(): {
  content: string;
  citations: Citation[];
  details: CitationDetail[];
} {
  return {
    content: DEMO_QA_ANSWER,
    citations: DEMO_QA_CITATIONS,
    details: Object.entries(DEMO_QA_CITATION_DETAILS).map(([ref_id, detail]) => ({
      ref_id,
      ...detail,
    })),
  };
}

function splitByCitationRefs(text: string): string[] {
  return text.split(/(\[\d+\])/g).filter(Boolean);
}

export default function ChatPage() {
  const { isDemo } = useDemoMode();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRef, setSelectedRef] = useState<string | null>(null);
  const [citationDetails, setCitationDetails] = useState<Record<string, CitationDetail>>(
    {},
  );

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    const userMsg: ChatMessage = { id: `u_${Date.now()}`, role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    await new Promise((r) => setTimeout(r, 450));

    const mocked = isDemo ? demoAssistantAnswer() : mockAssistantAnswer(q);
    const assistantId = `a_${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "", citations: mocked.citations },
    ]);

    // 模拟流式输出：逐字更新助手消息
    for (let i = 1; i <= mocked.content.length; i += 4) {
      const next = mocked.content.slice(0, i);
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, content: next } : m)),
      );
      await new Promise((r) => setTimeout(r, 20));
    }

    setCitationDetails((prev) => {
      const merged = { ...prev };
      mocked.details.forEach((d) => {
        merged[d.ref_id] = d;
      });
      return merged;
    });
    if (!selectedRef && mocked.details[0]) {
      setSelectedRef(mocked.details[0].ref_id);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (!isDemo) return;
    if (messages.length > 0) return;
    const seeded = demoAssistantAnswer();
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
    };
    setMessages([userMsg, assistantMsg]);
    setCitationDetails(DEMO_QA_CITATION_DETAILS);
    setSelectedRef("[1]");
    setInput(DEMO_QA_QUESTION);
  }, [isDemo, messages.length]);

  return (
    <div className="p-6">
      <div className="mb-4">
        <h1 className="text-2xl font-semibold">法律 AI 助手</h1>
        <p className="text-sm text-slate-600">
          智能问答与法条检索演示页（当前为前端 mock，可后续接入后端 QA API）。
        </p>
        {isDemo ? (
          <Badge className="mt-2 bg-violet-600 hover:bg-violet-600">Demo Mode</Badge>
        ) : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card className="border-slate-200 bg-white/80 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="size-4" />
              对话流
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ScrollArea className="h-[520px] rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div className="space-y-3">
                {messages.length === 0 ? (
                  <div className="text-sm text-slate-500">
                    请输入法律问题，例如：自动续约条款是否存在合规风险？
                  </div>
                ) : null}
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={`rounded-lg p-3 text-sm transition-all ${
                      m.role === "user" ? "bg-blue-600 text-white" : "bg-white text-slate-800"
                    }`}
                  >
                    <div className="mb-1 font-medium">{m.role === "user" ? "你" : "助手"}</div>
                    <div className="leading-6">
                      {m.role === "assistant"
                        ? splitByCitationRefs(m.content).map((part, idx) => {
                            const isRef = /^\[\d+\]$/.test(part);
                            if (!isRef) return <span key={`${m.id}-${idx}`}>{part}</span>;
                            return (
                              <button
                                key={`${m.id}-${idx}`}
                                type="button"
                                onClick={() => setSelectedRef(part)}
                                className="mx-0.5 rounded bg-emerald-50 px-1.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-300 hover:bg-emerald-100"
                              >
                                {part}
                              </button>
                            );
                          })
                        : m.content}
                    </div>
                    {m.citations?.length ? (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {m.citations.map((c) => (
                          <button
                            type="button"
                            key={`${m.id}-${c.ref_id}`}
                            onClick={() => setSelectedRef(c.ref_id)}
                          >
                            <Badge variant="secondary">
                              {c.ref_id} {c.law_name} 第{c.article}条
                            </Badge>
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
                {loading ? (
                  <div className="text-sm text-slate-500">助手正在检索法规并生成回答...</div>
                ) : null}
              </div>
            </ScrollArea>

            <div className="space-y-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入你的法律问题..."
                className="min-h-[110px] bg-white"
              />
              <div className="flex justify-end">
                <Button onClick={send} disabled={loading || input.trim().length === 0}>
                  {loading ? "发送中..." : "发送"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white/80 shadow-sm">
          <CardHeader>
            <CardTitle>引用详情</CardTitle>
          </CardHeader>
          <CardContent>
            {!selectedRef ? (
              <Alert>
                <AlertTitle>未选中引用</AlertTitle>
                <AlertDescription>
                  点击回答中的 [1]/[2] 或引用标签，查看右侧法条详情与校验状态。
                </AlertDescription>
              </Alert>
            ) : null}

            {selectedRef && citationDetails[selectedRef] ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge>{selectedRef}</Badge>
                  <Badge className="bg-emerald-600 hover:bg-emerald-600">
                    {citationDetails[selectedRef].status}
                  </Badge>
                </div>
                <Separator />
                <div className="space-y-1">
                  <div className="text-sm font-medium">
                    {citationDetails[selectedRef].law_name} {citationDetails[selectedRef].article}
                  </div>
                  <div className="rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-700">
                    {citationDetails[selectedRef].excerpt}
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

