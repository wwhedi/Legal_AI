import type {
  AskQARequest,
  AskQAResponse,
  ApproveRegulationResponse,
  ApproveReviewRequest,
  ApproveReviewResponse,
  PendingRegulationResponse,
  ReviewStatusResponse,
  SubmitReviewRequest,
  SubmitReviewResponse,
} from "@/types";

const DEFAULT_BASE_URL = "http://localhost:8000";

function getBaseUrl() {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") || DEFAULT_BASE_URL
  );
}

async function request<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const url = `${getBaseUrl()}${path.startsWith("/") ? "" : "/"}${path}`;
  const headers = new Headers(init?.headers);

  let body = init?.body;
  if (init && "json" in init) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json ?? null);
  }

  const resp = await fetch(url, {
    ...init,
    headers,
    body,
  });

  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(
      `API ${resp.status} ${resp.statusText} for ${path}${
        text ? `: ${text}` : ""
      }`,
    );
  }

  // Most endpoints are JSON
  return (await resp.json()) as T;
}

export async function submitReview(
  payload: SubmitReviewRequest,
  options?: { signal?: AbortSignal },
): Promise<SubmitReviewResponse> {
  return request<SubmitReviewResponse>("/review/submit", {
    method: "POST",
    json: payload,
    signal: options?.signal,
  });
}

export async function pollReviewStatus(
  threadId: string,
  options?: { signal?: AbortSignal },
): Promise<ReviewStatusResponse> {
  return request<ReviewStatusResponse>(`/review/status/${threadId}`, {
    method: "GET",
    signal: options?.signal,
  });
}

export async function approveReview(
  threadId: string,
  payload: ApproveReviewRequest,
  options?: { signal?: AbortSignal },
): Promise<ApproveReviewResponse> {
  return request<ApproveReviewResponse>(`/review/approve/${threadId}`, {
    method: "POST",
    json: payload,
    signal: options?.signal,
  });
}

export async function fetchPendingRegulations(
  options?: { signal?: AbortSignal; limit?: number; offset?: number },
): Promise<PendingRegulationResponse> {
  const limit = options?.limit ?? 50;
  const offset = options?.offset ?? 0;
  return request<PendingRegulationResponse>(
    `/regulations/pending?limit=${limit}&offset=${offset}`,
    {
      method: "GET",
      signal: options?.signal,
    },
  );
}

export async function approveRegulationChange(
  regulationId: string,
  options?: { signal?: AbortSignal },
): Promise<ApproveRegulationResponse> {
  return request<ApproveRegulationResponse>(`/regulations/${regulationId}/approve`, {
    method: "POST",
    signal: options?.signal,
  });
}

export async function askLegalQuestion(
  payload: AskQARequest,
  options?: { signal?: AbortSignal },
): Promise<AskQAResponse> {
  return request<AskQAResponse>("/qa/ask", {
    method: "POST",
    json: payload,
    signal: options?.signal,
  });
}

