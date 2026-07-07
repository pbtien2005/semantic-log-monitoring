import { afterEach, describe, expect, it, vi } from "vitest";

import { requestChatAnswer } from "./chat";

describe("requestChatAnswer", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the operator query and filters to the chat API", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ answer: "RAG response", source: "rag" })
    }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await requestChatAnswer({
      query: "Tại sao nova-api lỗi?",
      dataset: "openstack",
      service: "nova-api",
      levels: ["ERROR"]
    });

    expect(result).toEqual({ answer: "RAG response", source: "rag" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          query: "Tại sao nova-api lỗi?",
          dataset: "openstack",
          service: "nova-api",
          levels: ["ERROR"]
        })
      })
    );
  });

  it("posts RCA incident metadata and context logs when provided", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ answer: "RCA response", source: "rca" })
    }));
    vi.stubGlobal("fetch", fetchMock);

    await requestChatAnswer({
      query: "RCA log_id=hdfs:incident",
      dataset: "hdfs",
      service: "dfs.DataNode",
      levels: ["ERROR"],
      mode: "rca",
      incidentLog: {
        log_id: "hdfs:incident",
        dataset: "hdfs",
        timestamp: "2026-07-06T02:08:30+07:00",
        level: "ERROR",
        service: "dfs.DataNode",
        message: "Connection reset by peer"
      },
      contextLogs: [
        {
          log_id: "hdfs:slow",
          dataset: "hdfs",
          timestamp: "2026-07-06T02:08:15+07:00",
          level: "WARN",
          service: "dfs.DataNode",
          message: "Slow BlockReceiver write packet"
        }
      ]
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        body: JSON.stringify({
          query: "RCA log_id=hdfs:incident",
          dataset: "hdfs",
          service: "dfs.DataNode",
          levels: ["ERROR"],
          mode: "rca",
          incident_log: {
            log_id: "hdfs:incident",
            dataset: "hdfs",
            timestamp: "2026-07-06T02:08:30+07:00",
            level: "ERROR",
            service: "dfs.DataNode",
            message: "Connection reset by peer"
          },
          context_logs: [
            {
              log_id: "hdfs:slow",
              dataset: "hdfs",
              timestamp: "2026-07-06T02:08:15+07:00",
              level: "WARN",
              service: "dfs.DataNode",
              message: "Slow BlockReceiver write packet"
            }
          ]
        })
      })
    );
  });
});
