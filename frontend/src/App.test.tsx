import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import App from "./App";

const dashboardPayload = {
  logs: [
    {
      dataset: "openstack",
      timestamp: "2017-05-16 00:14:47.687",
      level: "ERROR",
      service: "nova-api",
      message: "nova-api timed out while calling hdfs namenode",
      rawLog: "ERROR nova-api timed out while calling hdfs namenode",
      log_id: "openstack-1",
      template_id: "T_TIMEOUT",
      anomaly: {
        score: 0.86,
        level: "high",
        decision: "anomalous",
        baseline_status: "ready",
        reasons: ["new_template_for_service", "new_template_transition"],
        components: { template_score: 1, transition_score: 0.8, window_score: 0.5, severity_hint: 1 }
      }
    },
    {
      dataset: "openstack",
      timestamp: "2017-05-16 00:12:00.000",
      level: "WARN",
      service: "nova-api",
      message: "compute queue is backing up before timeout",
      rawLog: "WARN compute queue is backing up before timeout",
      log_id: "openstack-0",
      template_id: "T_QUEUE",
      anomaly_score: 0.72,
      anomaly_level: "medium",
      anomaly_decision: "watch",
      anomaly_baseline_status: "ready",
      anomaly_reasons: ["window_template_distribution_shift"]
    },
    {
      dataset: "apache",
      timestamp: "2005-12-04 04:47:44.000",
      level: "INFO",
      service: "mod_jk",
      message: "Worker initialized",
      rawLog: "INFO Worker initialized"
    }
  ]
};

describe("Semantic log React dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "/api/chat") {
          return {
            ok: true,
            json: async () => ({
              answer: "nova-api bị lỗi do timeout khi gọi HDFS namenode.",
              source: "rag"
            })
          };
        }
        return {
          ok: true,
          json: async () => dashboardPayload
        };
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the Figma-style dashboard surface with live log sections", async () => {
    render(<App />);

    expect(await screen.findByText("Bảng Điều Khiển Log")).toBeInTheDocument();
    expect(screen.getByText("Trợ lý AI Phân tích Log")).toBeInTheDocument();
    expect(screen.getByText("Luồng Log Thời gian Thực")).toBeInTheDocument();
    expect(screen.getByText("Bản đồ Service")).toBeInTheDocument();
    expect(screen.getAllByText("3").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("live log row").length).toBeGreaterThan(0);
  });

  it("loads live logs from the recent logs API", async () => {
    render(<App />);

    await screen.findByText("nova-api timed out while calling hdfs namenode");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/^\/api\/logs\/recent\?/),
      expect.objectContaining({ cache: "no-store" })
    );
  });

  it("uses the full viewport width for the main dashboard content", () => {
    const styles = readFileSync(resolve(__dirname, "styles.css"), "utf-8");
    const shellRule = styles.match(/\.dashboard-shell\s*\{[^}]+\}/)?.[0] ?? "";

    expect(shellRule).toContain("width: 100%");
    expect(shellRule).not.toContain("1280px");
  });

  it("does not open the removed RCA evidence panel when a log row is clicked", async () => {
    render(<App />);

    fireEvent.click(await screen.findByText("nova-api timed out while calling hdfs namenode"));

    expect(screen.queryByText("RCA Evidence Candidates")).not.toBeInTheDocument();
  });

  it("renders live logs as compact single-line rows", async () => {
    const { container } = render(<App />);

    await screen.findByText("nova-api timed out while calling hdfs namenode");
    const rows = screen.getAllByLabelText("live log row");

    expect(rows.length).toBeGreaterThan(0);
    expect(rows[0].querySelector(".log-status-dot")).toBeInTheDocument();
    expect(rows[0].querySelector(".log-level-badge")).toBeInTheDocument();
    expect(rows[0].querySelector(".log-message")).toHaveTextContent("nova-api timed out while calling hdfs namenode");
    expect(rows[0]).toHaveAttribute(
      "data-log-tooltip",
      expect.stringContaining("nova-api timed out while calling hdfs namenode")
    );
    fireEvent.mouseEnter(rows[0]);
    expect(screen.getByRole("tooltip")).toHaveTextContent("nova-api timed out while calling hdfs namenode");
    expect(container.querySelector(".anomaly-line")).not.toBeInTheDocument();
  });

  it("marks anomaly log rows and sends an RCA prompt to chat", async () => {
    render(<App />);

    await screen.findByText("nova-api timed out while calling hdfs namenode");

    expect(screen.getByText("ANOMALY")).toBeInTheDocument();
    expect(screen.getByText("0.86")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /RCA for anomaly openstack-1/i }));

    await waitFor(() => {
      expect(screen.getByText(/RCA anomaly log_id=openstack-1/)).toBeInTheDocument();
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        method: "POST"
      })
    );
  });

  it("hides watch-only rows from anomaly badges and RCA actions", async () => {
    render(<App />);

    await screen.findByText("compute queue is backing up before timeout");
    const watchRow = screen.getByText("compute queue is backing up before timeout").closest("article");

    expect(screen.queryByText("WATCH")).not.toBeInTheDocument();
    expect(watchRow?.querySelector(".anomaly-signal")).toBeInTheDocument();
    expect(watchRow).not.toHaveClass("has-anomaly");
    expect(watchRow).not.toHaveClass("anomaly-medium");
    expect(screen.queryByRole("button", { name: /RCA for anomaly openstack-0/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /RCA for anomaly openstack-1/i })).toBeInTheDocument();
  });

  it("shows RCA for error watch rows with investigative anomaly reasons", async () => {
    const rcaPayload = {
      logs: [
        {
          dataset: "hdfs",
          timestamp: "260709 103050",
          level: "ERROR",
          service: "hdfs-datanode",
          message: "Got exception while serving blk_9000000000000000420",
          rawLog: "ERROR Got exception while serving blk_9000000000000000420",
          log_id: "hdfs:error-watch",
          template_id: "hdfs::E4",
          anomaly_score: 0.64,
          anomaly_level: "medium",
          anomaly_decision: "watch",
          anomaly_baseline_status: "ready",
          anomaly_reasons: ["new_template_transition", "error_severity_hint"]
        },
        {
          dataset: "hdfs",
          timestamp: "260709 103049",
          level: "WARN",
          service: "hdfs-datanode",
          message: "Slow packet responder for block",
          rawLog: "WARN Slow packet responder for block",
          log_id: "hdfs:warn-watch",
          template_id: "hdfs::E9",
          anomaly_score: 0.74,
          anomaly_level: "medium",
          anomaly_decision: "watch",
          anomaly_baseline_status: "ready",
          anomaly_reasons: ["new_template_for_service"]
        }
      ]
    };
    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/chat") {
        return {
          ok: true,
          json: async () => ({
            answer: "RCA ok",
            source: "rca"
          })
        } as Response;
      }
      return {
        ok: true,
        json: async () => rcaPayload
      } as Response;
    });

    render(<App />);

    await screen.findByText("Got exception while serving blk_9000000000000000420");
    const rcaWatchRow = screen.getByText("Got exception while serving blk_9000000000000000420").closest("article");
    const warnWatchRow = screen.getByText("Slow packet responder for block").closest("article");

    expect(screen.queryByText("WATCH")).not.toBeInTheDocument();
    expect(rcaWatchRow).toHaveClass("rca-worthy");
    expect(rcaWatchRow?.querySelector(".anomaly-signal")).toBeInTheDocument();
    expect(warnWatchRow).not.toHaveClass("rca-worthy");
    expect(warnWatchRow?.querySelector(".anomaly-signal")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /RCA for anomaly hdfs:error-watch/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /RCA for anomaly hdfs:warn-watch/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /RCA for anomaly hdfs:error-watch/i }));

    await waitFor(() => {
      expect(screen.getByText(/RCA anomaly log_id=hdfs:error-watch/)).toBeInTheDocument();
    });
  });

  it("shows embedding and Milvus indexing status for live log rows", async () => {
    const indexingPayload = {
      logs: [
        {
          dataset: "hdfs",
          timestamp: "260709 103050",
          level: "INFO",
          service: "dfs.DataNode",
          message: "PacketResponder finished for block",
          rawLog: "INFO PacketResponder finished for block",
          log_id: "hdfs-indexed",
          index_status: "indexed",
          indexed_at: "2026-07-13T09:30:00Z"
        },
        {
          dataset: "hdfs",
          timestamp: "260709 103051",
          level: "WARN",
          service: "dfs.DataNode",
          message: "Waiting for embedding worker",
          rawLog: "WARN Waiting for embedding worker",
          log_id: "hdfs-pending",
          index_status: "pending"
        },
        {
          dataset: "hdfs",
          timestamp: "260709 103052",
          level: "ERROR",
          service: "dfs.DataNode",
          message: "Milvus upsert failed",
          rawLog: "ERROR Milvus upsert failed",
          log_id: "hdfs-failed",
          index_status: "failed",
          index_error: "Milvus insert failed"
        }
      ]
    };
    vi.mocked(fetch).mockImplementation(async () => ({
      ok: true,
      json: async () => indexingPayload
    }) as Response);

    render(<App />);

    await screen.findByText("PacketResponder finished for block");

    expect(screen.getByLabelText(/Milvus indexed/i)).toHaveTextContent("Milvus");
    expect(screen.getByLabelText(/Embedding pending/i)).toHaveTextContent("Embedding");
    expect(screen.getByLabelText(/Milvus index failed/i)).toHaveTextContent("Index lỗi");
    expect(screen.getByLabelText(/Milvus index failed/i)).toHaveAttribute(
      "title",
      expect.stringContaining("Milvus insert failed")
    );
  });

  it("keeps previous real-time logs available behind a vertical scrollbar", async () => {
    const manyLogsPayload = {
      logs: Array.from({ length: 15 }, (_, index) => ({
        dataset: "hdfs",
        timestamp: `2008-11-09 20:35:${String(index).padStart(2, "0")}.000`,
        level: index % 5 === 0 ? "ERROR" : "INFO",
        service: "dfs.DataNode",
        message: `live hdfs log ${index}`,
        rawLog: `INFO dfs.DataNode live hdfs log ${index}`,
        log_id: `hdfs-live-${index}`,
        template_id: "T_LIVE"
      }))
    };
    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/chat") {
        return {
          ok: true,
          json: async () => ({
            answer: "ok",
            source: "rag"
          })
        } as Response;
      }
      return {
        ok: true,
        json: async () => manyLogsPayload
      } as Response;
    });

    render(<App />);

    await screen.findByText("live hdfs log 14");
    expect(screen.queryByLabelText("Số log hiển thị")).not.toBeInTheDocument();
    expect(screen.getAllByLabelText("live log row")).toHaveLength(15);

    const styles = readFileSync(resolve(__dirname, "styles.css"), "utf-8");
    const streamRule = styles.match(/\.live-log-panel\s+\.log-stream\s*\{[^}]+\}/)?.[0] ?? "";

    expect(streamRule).toContain("overflow-y: auto");
    expect(streamRule).toContain("max-height: 520px");
  });

  it("places traffic below live logs and removes resource telemetry", async () => {
    render(<App />);

    expect(await screen.findByText("Lưu lượng Log theo Cấp độ & Thời gian")).toBeInTheDocument();
    expect(screen.getByLabelText("stacked log traffic chart")).toBeInTheDocument();
    expect(screen.getByText("Anomaly Spike")).toBeInTheDocument();
    expect(screen.queryByLabelText("api resource area chart")).not.toBeInTheDocument();
    expect(screen.queryByText("Độ trễ API & Tài nguyên")).not.toBeInTheDocument();
  });

  it("spans the AI assistant beside the live log and traffic panels", () => {
    const styles = readFileSync(resolve(__dirname, "styles.css"), "utf-8");
    const analysisRule = styles.match(/\.analysis-grid\s*\{[^}]+\}/)?.[0] ?? "";
    const chatRule = styles.match(/\.analysis-grid\s*>\s*\.chat-panel\s*\{[^}]+\}/)?.[0] ?? "";
    const chartRule = styles.match(/\.traffic-panel\s*\{[^}]+\}/)?.[0] ?? "";

    expect(analysisRule).toContain("grid-template-columns");
    expect(analysisRule).toContain("grid-template-rows");
    expect(chatRule).toContain("grid-row: 1 / span 2");
    expect(chatRule).toContain("display: flex");
    expect(chartRule).toContain("min-height: 340px");
    expect(styles).toContain(".chart-surface svg");
    expect(styles).toContain("height: 100%");
  });

  it("lets operators filter and ask for recent logs with response timing", async () => {
    render(<App />);

    await screen.findByText("Bảng Điều Khiển Log");
    fireEvent.change(screen.getByLabelText("Dataset"), {
      target: { value: "openstack" }
    });
    fireEvent.change(screen.getByPlaceholderText("Hỏi về log, service, lỗi..."), {
      target: { value: "cho tôi log mới nhất trong 1 tiếng gần đây" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Gửi" }));

    await waitFor(() => {
      expect(screen.getByText(/timeout khi gọi HDFS namenode/)).toBeInTheDocument();
      expect(screen.getAllByText(/\d+\.\d{2}s/).length).toBeGreaterThan(0);
    });
    expect(fetch).toHaveBeenCalledWith("/api/chat", expect.any(Object));
  });
});
