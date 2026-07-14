export type LogLevel = "ERROR" | "WARN" | "NOTICE" | "INFO" | "DEBUG" | "UNKNOWN";
export type AnomalyLevel = "normal" | "low" | "medium" | "high" | "unknown";
export type AnomalyDecision = "normal" | "watch" | "anomalous" | "warming_up" | "not_scored";
export type BaselineStatus = "ready" | "insufficient_history" | "missing_baseline" | "disabled" | "error";
export type IndexStatus = "pending" | "indexed" | "failed" | "unknown";

export type AnomalyPayload = {
  score?: number | null;
  level?: string | null;
  decision?: string | null;
  baseline_status?: string | null;
  reasons?: readonly string[] | null;
  components?: Record<string, number | null> | null;
};

export type LogRecord = {
  dataset?: string | null;
  timestamp?: string | null;
  timestamp_ms?: number | null;
  parsedMs?: number | null;
  level?: string | null;
  service?: string | null;
  component?: string | null;
  logger?: string | null;
  message?: string | null;
  rawLog?: string | null;
  raw_log?: string | null;
  log_id?: string | null;
  line_number?: number | null;
  template_id?: string | null;
  anomaly?: AnomalyPayload | null;
  anomaly_score?: number | null;
  anomaly_level?: string | null;
  anomaly_decision?: string | null;
  anomaly_baseline_status?: string | null;
  anomaly_reasons?: readonly string[] | null;
  anomaly_components?: Record<string, number | null> | null;
  index_status?: string | null;
  indexed_at?: string | null;
  index_error?: string | null;
};

export type DashboardLog = {
  dataset: string;
  timestamp: string;
  parsedMs: number | null;
  level: LogLevel;
  service: string;
  message: string;
  rawLog: string;
  logId: string | null;
  lineNumber: number | null;
  templateId: string | null;
  anomalyScore: number | null;
  anomalyLevel: AnomalyLevel;
  anomalyDecision: AnomalyDecision;
  anomalyBaselineStatus: BaselineStatus;
  anomalyReasons: string[];
  anomalyComponents: Record<string, number | null>;
  indexStatus: IndexStatus;
  indexedAt: string | null;
  indexError: string | null;
};

export type LogFilters = {
  dataset?: string;
  service?: string;
  levels?: readonly string[];
};

export type DashboardSummary = {
  totalLogs: number;
  errorLogs: number;
  warnLogs: number;
  activeServices: number;
  errorRatePercent: number;
  latestDisplay: string;
};

export type TrafficPoint = {
  bucket: string;
  level: LogLevel;
  count: number;
};

export type ResourcePoint = {
  bucket: string;
  latencyMs: number;
  cpuPercent: number;
};

export type RcaCandidate = {
  log: DashboardLog;
  score: number;
  reasons: string[];
};

const LEVELS = new Set(["ERROR", "WARN", "NOTICE", "INFO", "DEBUG"]);
const ANOMALY_LEVELS = new Set(["normal", "low", "medium", "high", "unknown"]);
const ANOMALY_DECISIONS = new Set(["normal", "watch", "anomalous", "warming_up", "not_scored"]);
const BASELINE_STATUSES = new Set(["ready", "insufficient_history", "missing_baseline", "disabled", "error"]);
const INDEX_STATUSES = new Set(["pending", "indexed", "failed", "unknown"]);
const RECENT_TERMS = ["moi nhat", "gan day", "vua xay ra", "latest", "recent", "newest", "last logs"];

export const levelColors: Record<LogLevel, string> = {
  ERROR: "#f87171",
  WARN: "#fbbf24",
  NOTICE: "#a78bfa",
  INFO: "#38bdf8",
  DEBUG: "#94a3b8",
  UNKNOWN: "#64748b"
};

export function normalizeText(value: unknown, fallback = ""): string {
  const text = String(value ?? "").trim();
  return text || fallback;
}

export function normalizeQueryText(query: string): string {
  return query
    .toLowerCase()
    .replace(/đ/g, "d")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

export function parseTimestampMs(timestamp: string | null | undefined): number | null {
  const value = normalizeText(timestamp);
  if (!value) {
    return null;
  }

  const isoLike = value.match(
    /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?/
  );
  if (isoLike) {
    const [, year, month, day, hour, minute, second, fraction = "0"] = isoLike;
    return Date.UTC(
      Number(year),
      Number(month) - 1,
      Number(day),
      Number(hour),
      Number(minute),
      Number(second),
      Number(fraction.padEnd(3, "0").slice(0, 3))
    );
  }

  const hdfs = value.match(/^(\d{2})(\d{2})(\d{2})\s+(\d{2})(\d{2})(\d{2})/);
  if (hdfs) {
    const [, yy, month, day, hour, minute, second] = hdfs;
    return Date.UTC(2000 + Number(yy), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second));
  }

  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
}

export function normalizeLog(record: LogRecord): DashboardLog {
  const dataset = normalizeText(record.dataset, "unknown");
  const level = normalizeText(record.level, "UNKNOWN").toUpperCase();
  const message = normalizeText(record.message ?? record.rawLog ?? record.raw_log);
  const service = normalizeText(record.service ?? record.component ?? record.logger, `${dataset}-service`);
  const timestamp = normalizeText(record.timestamp);
  const anomaly = record.anomaly ?? {};
  const anomalyLevel = normalizeText(record.anomaly_level ?? anomaly.level, "unknown");
  const anomalyDecision = normalizeText(record.anomaly_decision ?? anomaly.decision, "not_scored");
  const anomalyBaselineStatus = normalizeText(record.anomaly_baseline_status ?? anomaly.baseline_status, "disabled");
  const indexStatus = normalizeText(record.index_status, "unknown").toLowerCase();
  const anomalyScore =
    typeof record.anomaly_score === "number"
      ? record.anomaly_score
      : typeof anomaly.score === "number"
        ? anomaly.score
        : null;
  const anomalyReasons = record.anomaly_reasons ?? anomaly.reasons ?? [];
  const anomalyComponents = record.anomaly_components ?? anomaly.components ?? {};
  const parsedMs =
    typeof record.parsedMs === "number"
      ? record.parsedMs
      : typeof record.timestamp_ms === "number"
        ? record.timestamp_ms
        : parseTimestampMs(timestamp);

  return {
    dataset,
    timestamp,
    parsedMs,
    level: LEVELS.has(level) ? (level as LogLevel) : "UNKNOWN",
    service,
    message,
    rawLog: normalizeText(record.rawLog ?? record.raw_log, message),
    logId: normalizeText(record.log_id) || null,
    lineNumber: typeof record.line_number === "number" ? record.line_number : null,
    templateId: normalizeText(record.template_id) || null,
    anomalyScore,
    anomalyLevel: ANOMALY_LEVELS.has(anomalyLevel) ? (anomalyLevel as AnomalyLevel) : "unknown",
    anomalyDecision: ANOMALY_DECISIONS.has(anomalyDecision) ? (anomalyDecision as AnomalyDecision) : "not_scored",
    anomalyBaselineStatus: BASELINE_STATUSES.has(anomalyBaselineStatus)
      ? (anomalyBaselineStatus as BaselineStatus)
      : "disabled",
    anomalyReasons: Array.isArray(anomalyReasons) ? [...anomalyReasons] : [],
    anomalyComponents: anomalyComponents && typeof anomalyComponents === "object" ? anomalyComponents : {},
    indexStatus: INDEX_STATUSES.has(indexStatus) ? (indexStatus as IndexStatus) : "unknown",
    indexedAt: normalizeText(record.indexed_at) || null,
    indexError: normalizeText(record.index_error) || null
  };
}

export function normalizeLogs(records: readonly LogRecord[]): DashboardLog[] {
  return records.map(normalizeLog);
}

export function summarizeLogs(records: readonly LogRecord[]): DashboardSummary {
  const logs = normalizeLogs(records);
  const totalLogs = logs.length;
  const errorLogs = logs.filter((log) => log.level === "ERROR").length;
  const warnLogs = logs.filter((log) => log.level === "WARN").length;
  const activeServices = new Set(logs.map((log) => log.service).filter((service) => service !== "unknown")).size;
  const latestMs = Math.max(...logs.map((log) => log.parsedMs ?? Number.NEGATIVE_INFINITY));

  return {
    totalLogs,
    errorLogs,
    warnLogs,
    activeServices,
    errorRatePercent: totalLogs ? Math.round((errorLogs / totalLogs) * 1000) / 10 : 0,
    latestDisplay: Number.isFinite(latestMs) ? formatTime(latestMs) : "Không có dữ liệu"
  };
}

export function filterLogs(records: readonly LogRecord[], filters: LogFilters): DashboardLog[] {
  const levels = new Set(filters.levels?.length ? filters.levels : ["ERROR", "WARN", "NOTICE", "INFO", "DEBUG", "UNKNOWN"]);
  return normalizeLogs(records)
    .filter((log) => !filters.dataset || filters.dataset === "all" || log.dataset === filters.dataset)
    .filter((log) => !filters.service || filters.service === "all" || log.service === filters.service)
    .filter((log) => levels.has(log.level))
    .sort((a, b) => (b.parsedMs ?? 0) - (a.parsedMs ?? 0));
}

export function buildTrafficSeries(records: readonly LogRecord[]): TrafficPoint[] {
  const grouped = new Map<string, TrafficPoint>();
  for (const log of normalizeLogs(records)) {
    if (log.parsedMs === null) {
      continue;
    }
    const bucket = formatBucket(log.parsedMs);
    const key = `${bucket}:${log.level}`;
    const current = grouped.get(key);
    grouped.set(key, {
      bucket,
      level: log.level,
      count: (current?.count ?? 0) + 1
    });
  }

  return [...grouped.values()].sort((a, b) => a.bucket.localeCompare(b.bucket) || a.level.localeCompare(b.level));
}

export function buildResourceSeries(traffic: readonly TrafficPoint[]): ResourcePoint[] {
  const buckets = new Map<string, Partial<Record<LogLevel, number>>>();
  for (const point of traffic) {
    const bucket = buckets.get(point.bucket) ?? {};
    bucket[point.level] = (bucket[point.level] ?? 0) + point.count;
    buckets.set(point.bucket, bucket);
  }

  return [...buckets.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([bucket, counts]) => {
      const total = Object.values(counts).reduce((sum, count) => sum + (count ?? 0), 0);
      const errors = counts.ERROR ?? 0;
      const warns = counts.WARN ?? 0;
      return {
        bucket,
        latencyMs: Math.round(250 + total * 12 + errors * 180 + warns * 45),
        cpuPercent: Math.min(99, Math.round(25 + total * 0.35 + errors * 7 + warns * 2))
      };
    });
}

export function answerRecentLogs(
  records: readonly LogRecord[],
  query: string,
  filters: LogFilters = {},
  limit = 5
): string {
  const normalized = normalizeQueryText(query);
  const isRecent = RECENT_TERMS.some((term) => normalized.includes(term));
  if (!isRecent) {
    return "Mình đã nhận câu hỏi. Với bản React tĩnh hiện tại, mình ưu tiên trả lời nhanh các truy vấn log mới nhất và danh sách lỗi theo bộ lọc.";
  }

  const hoursMatch = normalized.match(/\b(\d{1,3})\s*(h|gio|tieng|hour|hours)\b/);
  const hours = Math.max(1, Number(hoursMatch?.[1] ?? 1));
  const filtered = filterLogs(records, filters).filter((log) => log.parsedMs !== null);
  if (!filtered.length) {
    return "Không có log phù hợp với bộ lọc hiện tại.";
  }

  const latestMs = filtered[0].parsedMs ?? 0;
  const startMs = latestMs - hours * 60 * 60 * 1000;
  const rows = filtered.filter((log) => (log.parsedMs ?? 0) >= startMs).slice(0, limit);
  if (!rows.length) {
    return `Không có log trong ${hours} tiếng gần nhất theo mốc dữ liệu hiện có.`;
  }

  return [
    `Đây là ${rows.length} log mới nhất trong ${hours} tiếng gần đây theo mốc dữ liệu hiện có (${formatDateTime(startMs)} -> ${formatDateTime(latestMs)}):`,
    ...rows.map((log) => `- ${log.timestamp} ${log.level} ${log.service}: ${truncate(log.message, 180)}`)
  ].join("\n");
}

export function uniqueValues(records: readonly LogRecord[], key: "dataset" | "service"): string[] {
  return [...new Set(normalizeLogs(records).map((log) => log[key]).filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

export function rankRcaCandidates(
  logs: readonly DashboardLog[],
  incident: DashboardLog,
  limit = 8,
  lookbackMs = 10 * 60 * 1000
): RcaCandidate[] {
  if (incident.parsedMs === null) {
    return [];
  }
  const startMs = incident.parsedMs - lookbackMs;
  return logs
    .filter((log) => log.logId !== incident.logId)
    .filter((log) => log.dataset === incident.dataset)
    .filter((log) => log.parsedMs !== null && log.parsedMs <= incident.parsedMs! && log.parsedMs >= startMs)
    .map((log) => scoreRcaCandidate(log, incident, lookbackMs))
    .filter((candidate) => candidate.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .sort((a, b) => (a.log.parsedMs ?? 0) - (b.log.parsedMs ?? 0));
}

function scoreRcaCandidate(log: DashboardLog, incident: DashboardLog, lookbackMs: number): RcaCandidate {
  const anomalyScore = log.anomalyScore ?? 0;
  const temporalScore =
    log.parsedMs === null || incident.parsedMs === null
      ? 0
      : Math.max(0, 1 - (incident.parsedMs - log.parsedMs) / lookbackMs);
  const serviceScore = log.service === incident.service ? 1 : log.dataset === incident.dataset ? 0.25 : 0;
  const templateScore = log.templateId && log.templateId === incident.templateId ? 1 : 0;
  const score = anomalyScore * 0.3 + temporalScore * 0.25 + serviceScore * 0.2 + templateScore * 0.15;
  const reasons = [
    anomalyScore >= 0.6 ? "candidate anomaly" : "",
    temporalScore > 0 ? "before incident" : "",
    serviceScore >= 1 ? "same service" : serviceScore > 0 ? "same dataset fallback" : "",
    templateScore >= 1 ? "same template" : ""
  ].filter(Boolean);
  return { log, score: Math.round(score * 1000) / 1000, reasons };
}

export function formatTime(ms: number): string {
  const date = new Date(ms);
  return [date.getUTCHours(), date.getUTCMinutes(), date.getUTCSeconds()].map((part) => String(part).padStart(2, "0")).join(":");
}

export function formatDateTime(ms: number): string {
  const date = new Date(ms);
  const datePart = [date.getUTCFullYear(), date.getUTCMonth() + 1, date.getUTCDate()]
    .map((part, index) => (index === 0 ? String(part) : String(part).padStart(2, "0")))
    .join("-");
  return `${datePart} ${formatTime(ms)}`;
}

function formatBucket(ms: number): string {
  const date = new Date(ms);
  const hour = String(date.getUTCHours()).padStart(2, "0");
  const minute = String(Math.floor(date.getUTCMinutes() / 5) * 5).padStart(2, "0");
  return `${hour}:${minute}`;
}

function truncate(value: string, maxLength: number): string {
  return value.length <= maxLength ? value : `${value.slice(0, maxLength - 3)}...`;
}
