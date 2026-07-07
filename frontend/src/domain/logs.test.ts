import { describe, expect, it } from "vitest";

import {
  answerRecentLogs,
  buildResourceSeries,
  buildTrafficSeries,
  filterLogs,
  normalizeLog,
  rankRcaCandidates,
  summarizeLogs
} from "./logs";

const records = [
  {
    dataset: "openstack",
    timestamp: "2017-05-16 00:14:47.687",
    level: "ERROR",
    service: "nova-api",
    message: "nova-api timed out while calling hdfs namenode",
    rawLog: "ERROR nova-api timed out while calling hdfs namenode",
    anomaly: {
      score: 0.84,
      level: "high",
      decision: "anomalous",
      baseline_status: "ready",
      reasons: ["new_template_for_service"],
      components: { template_score: 1, transition_score: 0.8, window_score: 0.5, severity_hint: 1 }
    },
    template_id: "T_TIMEOUT",
    log_id: "log-1"
  },
  {
    dataset: "openstack",
    timestamp: "2017-05-16 00:10:00.000",
    level: "WARN",
    service: "nova-compute",
    message: "compute queue is backing up",
    rawLog: "WARN compute queue is backing up",
    anomaly_score: 0.62,
    anomaly_level: "medium",
    anomaly_decision: "watch",
    anomaly_baseline_status: "ready",
    anomaly_reasons: ["window_template_distribution_shift"],
    template_id: "T_QUEUE",
    log_id: "log-2"
  },
  {
    dataset: "hdfs",
    timestamp: "2008-11-10 21:15:41.000",
    level: "INFO",
    service: "dfs.DataNode",
    message: "Starting thread to transfer block",
    rawLog: "INFO dfs.DataNode Starting thread to transfer block"
  }
] as const;

describe("dashboard log domain", () => {
  it("summarizes health metrics from benchmark logs", () => {
    expect(summarizeLogs(records)).toMatchObject({
      totalLogs: 3,
      errorLogs: 1,
      warnLogs: 1,
      activeServices: 3,
      errorRatePercent: 33.3,
      latestDisplay: "00:14:47"
    });
  });

  it("filters logs by dataset, service and selected levels", () => {
    expect(
      filterLogs(records, {
        dataset: "openstack",
        service: "nova-api",
        levels: ["ERROR"]
      })
    ).toHaveLength(1);
  });

  it("builds traffic and resource series for chart panels", () => {
    expect(buildTrafficSeries(records)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ bucket: "00:10", level: "WARN", count: 1 }),
        expect.objectContaining({ bucket: "00:10", level: "ERROR", count: 1 })
      ])
    );
    expect(buildResourceSeries(buildTrafficSeries(records))[0]).toEqual(
      expect.objectContaining({
        bucket: "00:10",
        latencyMs: expect.any(Number),
        cpuPercent: expect.any(Number)
      })
    );
  });

  it("answers latest-log questions relative to the newest dataset timestamp", () => {
    const answer = answerRecentLogs(records, "cho tôi log mới nhất trong 1 tiếng gần đây");

    expect(answer).toContain("2017-05-16 00:14:47.687");
    expect(answer).toContain("nova-api");
    expect(answer).not.toContain("2008-11-10 21:15:41.000");
  });

  it("normalizes nested and flat anomaly fields", () => {
    const nested = normalizeLog(records[0]);
    const flat = normalizeLog(records[1]);

    expect(nested).toMatchObject({
      anomalyScore: 0.84,
      anomalyLevel: "high",
      anomalyDecision: "anomalous",
      anomalyBaselineStatus: "ready"
    });
    expect(nested.anomalyReasons).toContain("new_template_for_service");
    expect(flat.anomalyScore).toBe(0.62);
    expect(flat.anomalyDecision).toBe("watch");
  });

  it("ranks RCA evidence candidates before the selected incident", () => {
    const logs = [
      normalizeLog({
        ...records[1],
        timestamp_ms: Date.UTC(2017, 4, 16, 0, 12, 0),
        anomaly_score: 0.7,
        service: "nova-api"
      }),
      normalizeLog({
        ...records[0],
        timestamp_ms: Date.UTC(2017, 4, 16, 0, 14, 47)
      })
    ];

    const candidates = rankRcaCandidates(logs, logs[1], 5);

    expect(candidates).toHaveLength(1);
    expect(candidates[0].log.message).toContain("queue is backing up");
    expect(candidates[0].reasons).toContain("candidate anomaly");
  });
});
