export type ChatRequest = {
  query: string;
  dataset: string;
  service: string;
  levels: string[];
  mode?: "rca";
  incidentLog?: Record<string, unknown>;
  contextLogs?: Record<string, unknown>[];
};

export type ChatResponse = {
  answer: string;
  source: "rag" | "local" | "fallback" | "rca";
  context?: unknown;
};

export async function requestChatAnswer(payload: ChatRequest): Promise<ChatResponse> {
  const requestBody = {
    query: payload.query,
    dataset: payload.dataset,
    service: payload.service,
    levels: payload.levels,
    ...(payload.mode ? { mode: payload.mode } : {}),
    ...(payload.incidentLog ? { incident_log: payload.incidentLog } : {}),
    ...(payload.contextLogs ? { context_logs: payload.contextLogs } : {})
  };

  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(requestBody)
  });

  if (!response.ok) {
    throw new Error(`Chat API failed with ${response.status}`);
  }

  const responseBody = (await response.json()) as Partial<ChatResponse>;
  return {
    answer: responseBody.answer || "Khong co cau tra loi tu RAG backend.",
    source: responseBody.source || "fallback",
    context: responseBody.context
  };
}
