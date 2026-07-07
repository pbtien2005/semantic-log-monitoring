import { FormEvent, MouseEvent, ReactNode, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock3,
  Database,
  Pause,
  Radio,
  Search,
  Send,
  Server,
  UserRound,
  Zap
} from "lucide-react";

import {
  DashboardLog,
  LogRecord,
  answerRecentLogs,
  buildTrafficSeries,
  filterLogs,
  levelColors,
  summarizeLogs,
  uniqueValues
} from "./domain/logs";
import { requestChatAnswer } from "./api/chat";
import "./styles.css";

const LEVELS = ["ERROR", "WARN", "NOTICE", "INFO", "DEBUG", "UNKNOWN"];

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  time: string;
  elapsed?: string;
};

function App() {
  const [records, setRecords] = useState<LogRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [dataset, setDataset] = useState("all");
  const [service, setService] = useState("all");
  const [levels, setLevels] = useState(["ERROR", "WARN", "NOTICE", "INFO"]);
  const [streamPaused, setStreamPaused] = useState(false);
  const [query, setQuery] = useState("");
  const [chatPending, setChatPending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: "assistant",
      content:
        "Chào bạn, mình đang theo dõi luồng log Apache, OpenStack và HDFS. Hỏi mình về log mới nhất, lỗi nổi bật hoặc service đang bất thường.",
      time: new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }),
      elapsed: "0.00s"
    }
  ]);

  useEffect(() => {
    let mounted = true;
    const readLogsPayload = async (url: string) => {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Unable to read ${url}`);
      }
      return response.json() as Promise<{ logs: LogRecord[] }>;
    };

    const loadDashboardData = () => {
      readLogsPayload(`/api/logs/recent?limit=200&ts=${Date.now()}`)
      .catch(() => readLogsPayload(`/dashboard-data.json?ts=${Date.now()}`))
      .then((payload) => {
        if (mounted) {
          setRecords(payload.logs ?? []);
        }
      })
      .catch(() => {
        if (mounted) {
          setRecords([]);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });
    };

    loadDashboardData();
    const interval = window.setInterval(loadDashboardData, 1000);
    return () => {
      mounted = false;
      window.clearInterval(interval);
    };
  }, []);

  const visibleRecords = useMemo(
    () => filterLogs(records, { dataset, service, levels }),
    [dataset, levels, records, service]
  );
  const summary = useMemo(() => summarizeLogs(visibleRecords), [visibleRecords]);
  const datasets = useMemo(() => uniqueValues(records, "dataset"), [records]);
  const services = useMemo(() => uniqueValues(filterLogs(records, { dataset, levels: LEVELS }), "service"), [dataset, records]);
  const traffic = useMemo(() => buildTrafficSeries(visibleRecords), [visibleRecords]);

  const handleLevelChange = (level: string) => {
    setLevels((current) => (current.includes(level) ? current.filter((item) => item !== level) : [...current, level]));
  };

  const submitChatQuery = async (
    trimmed: string,
    options: { mode?: "rca"; incidentLog?: Record<string, unknown> } = {}
  ) => {
    if (!trimmed || chatPending) {
      return;
    }

    const startedAt = performance.now();
    const time = new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
    setQuery("");
    setChatPending(true);
    setMessages((current) => [
      ...current,
      { id: current.length + 1, role: "user", content: trimmed, time }
    ]);

    let answer: string;
    try {
      const response = await requestChatAnswer({
        query: trimmed,
        dataset,
        service,
        levels,
        mode: options.mode,
        incidentLog: options.incidentLog,
        contextLogs: visibleRecords.slice(0, 200).map(toChatLogPayload)
      });
      answer = response.answer;
    } catch {
      answer = answerRecentLogs(records, trimmed, { dataset, service, levels });
    }
    const elapsed = `${((performance.now() - startedAt) / 1000).toFixed(2)}s`;

    setMessages((current) => [
      ...current,
      { id: current.length + 1, role: "assistant", content: answer, time, elapsed }
    ]);
    setChatPending(false);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await submitChatQuery(query.trim());
  };

  const handleRcaRequest = async (log: DashboardLog) => {
    await submitChatQuery(buildRcaPrompt(log), {
      mode: "rca",
      incidentLog: toChatLogPayload(log)
    });
  };

  return (
    <main className="dashboard-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Semantic Log Intelligence v2.1</p>
          <h1>Bảng Điều Khiển Log</h1>
          <p className="hero-copy">Giám sát ngữ nghĩa cho Apache, OpenStack và HDFS từ benchmark log nội bộ.</p>
        </div>
        <div className="live-status">
          <span className="pulse" />
          <span>Live stream</span>
          <strong>{summary.latestDisplay}</strong>
        </div>
      </section>

      <section className="filters-panel" aria-label="Bộ lọc dashboard">
        <label>
          Dataset
          <select value={dataset} onChange={(event) => setDataset(event.target.value)}>
            <option value="all">Tất cả dataset</option>
            {datasets.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label>
          Service
          <select value={service} onChange={(event) => setService(event.target.value)}>
            <option value="all">Tất cả service</option>
            {services.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <div className="level-filter" aria-label="Level">
          {LEVELS.map((level) => (
            <label key={level} className="chip">
              <input checked={levels.includes(level)} type="checkbox" onChange={() => handleLevelChange(level)} />
              <span style={{ background: levelColors[level as keyof typeof levelColors] }} />
              {level}
            </label>
          ))}
        </div>
      </section>

      <section className="kpi-grid">
        <MetricCard icon={<Database />} label="Tổng số log" value={summary.totalLogs.toLocaleString("vi-VN")} helper="Theo bộ lọc hiện tại" />
        <MetricCard icon={<AlertTriangle />} label="Tỷ lệ lỗi" value={`${summary.errorRatePercent}%`} helper={`${summary.errorLogs} error / ${summary.warnLogs} warn`} tone="danger" />
        <MetricCard icon={<Server />} label="Service hoạt động" value={summary.activeServices.toLocaleString("vi-VN")} helper="Service có log hợp lệ" tone="success" />
        <MetricCard icon={<Clock3 />} label="Log mới nhất" value={summary.latestDisplay} helper={loading ? "Đang tải dữ liệu" : "Mốc mới nhất trong dữ liệu"} />
      </section>

      <section className="analysis-grid">
        <Panel title="Trợ lý AI Phân tích Log" subtitle="Semantic Log Intelligence v2.1" className="chat-panel">
          <div className="chat-history">
            {messages.map((message) => (
              <article key={message.id} className={`chat-row ${message.role}`}>
                <div className="avatar">{message.role === "assistant" ? <Bot size={16} /> : <UserRound size={16} />}</div>
                <div className="bubble">
                  <div className="message-text">{message.content}</div>
                  <time>
                    {message.time}
                    {message.elapsed ? ` · ${message.elapsed}` : ""}
                  </time>
                </div>
              </article>
            ))}
          </div>
          <form className="chat-input" onSubmit={handleSubmit}>
            <Search size={18} />
            <input
              placeholder="Hỏi về log, service, lỗi..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <button type="submit" disabled={chatPending}>
              <Send size={16} />
              {chatPending ? "Đang hỏi" : "Gửi"}
            </button>
          </form>
        </Panel>

        <Panel
          title="Luồng Log Thời gian Thực"
          subtitle="Danh sách log mới nhất theo bộ lọc"
          className="live-log-panel"
          action={
            <button className="ghost-button" type="button" onClick={() => setStreamPaused((current) => !current)}>
              {streamPaused ? <Radio size={15} /> : <Pause size={15} />}
              {streamPaused ? "Resume" : "Pause"}
            </button>
          }
        >
          <LogStream
            logs={streamPaused ? [] : visibleRecords.slice(0, 12)}
            paused={streamPaused}
            onRcaRequest={handleRcaRequest}
          />
        </Panel>

        <Panel
          title="Lưu lượng Log theo Cấp độ & Thời gian"
          subtitle="Kibana-style, gom bucket 5 phút"
          className="chart-panel traffic-panel"
          action={
            <ChartLegend
              items={[
                { label: "INFO", color: "#4fc3f7" },
                { label: "WARN", color: "#fbbf24" },
                { label: "ERROR", color: "#ef4444" }
              ]}
            />
          }
        >
          <TrafficChart points={traffic} />
        </Panel>
      </section>

      <Panel title="Bản đồ Service" subtitle="Trạng thái service suy ra từ level lỗi gần nhất">
        <ServiceMap logs={visibleRecords} />
      </Panel>
    </main>
  );
}

function MetricCard({ icon, label, value, helper, tone = "default" }: { icon: ReactNode; label: string; value: string; helper: string; tone?: "default" | "danger" | "success" }) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-icon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{helper}</small>
      </div>
    </article>
  );
}

function Panel({ title, subtitle, action, className = "", children }: { title: string; subtitle: string; action?: ReactNode; className?: string; children: ReactNode }) {
  return (
    <section className={`panel ${className}`}>
      <header className="panel-header">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        {action}
      </header>
      {children}
    </section>
  );
}

function ChartLegend({ items }: { items: { label: string; color: string; line?: boolean }[] }) {
  return (
    <div className="chart-legend">
      {items.map((item) => (
        <span key={item.label}>
          <i className={item.line ? "legend-line" : ""} style={{ background: item.color }} />
          {item.label}
        </span>
      ))}
    </div>
  );
}

function TrafficChart({ points }: { points: ReturnType<typeof buildTrafficSeries> }) {
  const buckets = [...new Set(points.map((point) => point.bucket))].slice(-13);
  const levels = ["INFO", "WARN", "ERROR"] as const;
  const data = buckets.map((bucket) => {
    const counts = Object.fromEntries(levels.map((level) => [level, 0])) as Record<(typeof levels)[number], number>;
    for (const point of points.filter((item) => item.bucket === bucket)) {
      if (point.level === "INFO" || point.level === "WARN" || point.level === "ERROR") {
        counts[point.level] += point.count;
      }
    }
    return { bucket, ...counts, total: levels.reduce((sum, level) => sum + counts[level], 0) };
  });
  const maxTotal = Math.max(1, ...data.map((point) => point.total));
  const width = 720;
  const height = 250;
  const plot = { left: 42, right: 16, top: 18, bottom: 32 };
  const plotWidth = width - plot.left - plot.right;
  const plotHeight = height - plot.top - plot.bottom;
  const slot = data.length ? plotWidth / data.length : plotWidth;
  const barWidth = Math.min(28, Math.max(10, slot * 0.44));
  const spikeIndex = Math.max(
    0,
    data.reduce((best, item, index) => (item.ERROR > data[best].ERROR ? index : best), 0)
  );

  return (
    <div className="chart-surface">
      <svg aria-label="stacked log traffic chart" viewBox={`0 0 ${width} ${height}`} role="img">
        {[0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = plot.top + plotHeight * (1 - ratio);
          return (
            <g key={ratio}>
              <line className="chart-grid-line" x1={plot.left} x2={width - plot.right} y1={y} y2={y} />
              <text className="chart-axis-label" x={10} y={y + 4}>
                {Math.round(maxTotal * ratio)}
              </text>
            </g>
          );
        })}
        {data.map((point, index) => {
          const x = plot.left + index * slot + slot / 2 - barWidth / 2;
          let yCursor = plot.top + plotHeight;
          return (
            <g key={point.bucket}>
              {levels.map((level) => {
                const segmentHeight = Math.max(point[level] ? 3 : 0, (point[level] / maxTotal) * plotHeight);
                yCursor -= segmentHeight;
                return (
                  <rect
                    key={level}
                    x={x}
                    y={yCursor}
                    width={barWidth}
                    height={segmentHeight}
                    rx={level === "ERROR" ? 3 : 1}
                    fill={levelColors[level]}
                  >
                    <title>{`${point.bucket} ${level}: ${point[level]}`}</title>
                  </rect>
                );
              })}
              <text className="chart-axis-label" x={x + barWidth / 2} y={height - 10} textAnchor="middle">
                {point.bucket}
              </text>
            </g>
          );
        })}
        {data.length ? (
          <g>
            <line
              className="chart-reference-line"
              x1={plot.left + spikeIndex * slot + slot / 2}
              x2={plot.left + spikeIndex * slot + slot / 2}
              y1={plot.top}
              y2={plot.top + plotHeight}
            />
            <text className="chart-alert-label" x={plot.left + spikeIndex * slot + slot / 2 + 8} y={plot.top + 12}>
              Anomaly Spike
            </text>
          </g>
        ) : null}
      </svg>
    </div>
  );
}

function isActionableAnomaly(log: DashboardLog): boolean {
  return (
    log.anomalyDecision === "anomalous" ||
    log.anomalyDecision === "watch" ||
    log.anomalyLevel === "high" ||
    log.anomalyLevel === "medium"
  );
}

function anomalyLabel(log: DashboardLog): string {
  if (log.anomalyDecision === "watch") {
    return "WATCH";
  }
  if (log.anomalyDecision === "anomalous" || log.anomalyLevel === "high") {
    return "ANOMALY";
  }
  return log.anomalyLevel.toUpperCase();
}

function formatAnomalyScore(score: number | null): string {
  return typeof score === "number" ? score.toFixed(2) : "--";
}

function buildAnomalyTooltip(log: DashboardLog): string {
  if (!isActionableAnomaly(log)) {
    return "";
  }
  const reasons = log.anomalyReasons.length ? log.anomalyReasons.join(", ") : "no reason payload";
  return `\nAnomaly: ${log.anomalyDecision} / ${log.anomalyLevel} score=${formatAnomalyScore(log.anomalyScore)} baseline=${log.anomalyBaselineStatus}\nReasons: ${reasons}`;
}

function buildRcaPrompt(log: DashboardLog): string {
  return [
    `RCA anomaly log_id=${log.logId ?? "unknown"}`,
    `time=${log.timestamp || "-"}`,
    `dataset=${log.dataset}`,
    `service=${log.service}`,
    `level=${log.level}`,
    `anomaly_decision=${log.anomalyDecision}`,
    `anomaly_level=${log.anomalyLevel}`,
    `anomaly_score=${formatAnomalyScore(log.anomalyScore)}`,
    `message=${log.message}`,
    "Hãy giải thích vì sao log này bất thường và liệt kê các log liên quan trước/sau nó."
  ].join("\n");
}

function toChatLogPayload(log: DashboardLog): Record<string, unknown> {
  return {
    dataset: log.dataset,
    timestamp: log.timestamp,
    timestamp_ms: log.parsedMs,
    level: log.level,
    service: log.service,
    message: log.message,
    raw_log: log.rawLog,
    log_id: log.logId,
    template_id: log.templateId,
    anomaly_score: log.anomalyScore,
    anomaly_level: log.anomalyLevel,
    anomaly_decision: log.anomalyDecision,
    anomaly_baseline_status: log.anomalyBaselineStatus,
    anomaly_reasons: log.anomalyReasons,
    anomaly_components: log.anomalyComponents
  };
}

function LogStream({
  logs,
  paused,
  onRcaRequest
}: {
  logs: DashboardLog[];
  paused: boolean;
  onRcaRequest: (log: DashboardLog) => void;
}) {
  const [tooltip, setTooltip] = useState<{ content: string; x: number; y: number } | null>(null);

  const setTooltipPosition = (xPosition: number, yPosition: number, content: string) => {
    const width = 520;
    const height = 120;
    const x = Math.max(12, Math.min(xPosition, window.innerWidth - width - 12));
    const y = Math.max(12, Math.min(yPosition, window.innerHeight - height - 12));
    setTooltip({ content, x, y });
  };

  const showTooltip = (event: MouseEvent<HTMLElement>, content: string) => {
    setTooltipPosition(event.clientX + 16, event.clientY + 18, content);
  };

  const showFocusedTooltip = (element: HTMLElement, content: string) => {
    const rect = element.getBoundingClientRect();
    setTooltipPosition(rect.left + 16, rect.bottom + 8, content);
  };

  if (paused) {
    return <div className="empty-state">Stream đang tạm dừng.</div>;
  }
  if (!logs.length) {
    return <div className="empty-state">Không có log phù hợp bộ lọc.</div>;
  }

  return (
    <div className="log-stream">
      {logs.map((log, index) => {
        const isAnomaly = isActionableAnomaly(log);
        const tooltipText = `${log.timestamp || "-"} ${log.level} ${log.service}: ${log.message}${buildAnomalyTooltip(log)}`;
        return (
          <article
            key={`${log.timestamp}-${index}`}
            className={`log-row ${log.level.toLowerCase()} anomaly-${log.anomalyLevel}${isAnomaly ? " has-anomaly" : ""}`}
            aria-label="live log row"
            data-log-tooltip={tooltipText}
            onBlur={() => setTooltip(null)}
            onFocus={(event) => showFocusedTooltip(event.currentTarget, tooltipText)}
            onMouseEnter={(event) => showTooltip(event, tooltipText)}
            onMouseLeave={() => setTooltip(null)}
            onMouseMove={(event) => showTooltip(event, tooltipText)}
            tabIndex={0}
            title={tooltipText}
          >
            <span className="log-status-dot" style={{ background: levelColors[log.level] ?? levelColors.UNKNOWN }} />
            <span className="log-time">{log.timestamp || "-"}</span>
            <strong className="log-level-badge">{log.level}</strong>
            <b>{log.service}</b>
            <span className="log-message">{log.message}</span>
            {isAnomaly ? (
              <span className={`anomaly-pill ${log.anomalyDecision}`}>
                {anomalyLabel(log)}
                <small>{formatAnomalyScore(log.anomalyScore)}</small>
              </span>
            ) : (
              <span className="anomaly-placeholder" aria-hidden="true" />
            )}
            {isAnomaly ? (
              <button
                className="rca-button"
                type="button"
                aria-label={`RCA for anomaly ${log.logId ?? log.service}`}
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  onRcaRequest(log);
                }}
              >
                RCA
              </button>
            ) : (
              <span className="rca-placeholder" aria-hidden="true" />
            )}
          </article>
        );
      })}
      {tooltip ? (
        <div className="log-tooltip" role="tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
          {tooltip.content}
        </div>
      ) : null}
    </div>
  );
}

function ServiceMap({ logs }: { logs: DashboardLog[] }) {
  const services = [...new Map(logs.map((log) => [log.service, log])).values()].slice(0, 10);
  if (!services.length) {
    return <div className="empty-state">Chưa có service để hiển thị.</div>;
  }

  return (
    <div className="service-map">
      {services.map((log) => {
        const status = log.level === "ERROR" ? "critical" : log.level === "WARN" ? "warning" : "healthy";
        return (
          <article key={log.service} className={`service-node ${status}`}>
            <div>{status === "healthy" ? <CheckCircle2 /> : status === "warning" ? <Zap /> : <AlertTriangle />}</div>
            <strong>{log.service}</strong>
            <span>{log.dataset}</span>
          </article>
        );
      })}
    </div>
  );
}

export default App;
