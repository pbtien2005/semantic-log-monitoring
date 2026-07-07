import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { DEFAULT_DASHBOARD_TIME_ZONE, getDateKey, selectDashboardLogs } from "./dashboard-data-filter.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, "..");
const projectRoot = path.resolve(frontendDir, "..");
const benchmarkDir = path.join(projectRoot, "data", "benchmark");
const anomalyDashboardDir = path.join(projectRoot, "data", "anomaly", "dashboard");
const outputPath = path.join(frontendDir, "public", "dashboard-data.json");
const datasets = ["apache", "hdfs", "openstack"];
const dashboardTimeZone = process.env.DASHBOARD_TIME_ZONE ?? DEFAULT_DASHBOARD_TIME_ZONE;
const dashboardNow = process.env.DASHBOARD_CURRENT_DATE ? new Date(process.env.DASHBOARD_CURRENT_DATE) : new Date();
const dashboardDate = getDateKey(dashboardNow, dashboardTimeZone);

async function readPreferredDataset(dataset) {
  const anomalyPath = path.join(anomalyDashboardDir, dataset, "logs.jsonl");
  try {
    return {
      content: await readFile(anomalyPath, "utf8"),
      source: path.relative(projectRoot, anomalyPath)
    };
  } catch (error) {
    if (error?.code !== "ENOENT") {
      throw error;
    }
  }

  const benchmarkPath = path.join(benchmarkDir, dataset, "logs.jsonl");
  return {
    content: await readFile(benchmarkPath, "utf8"),
    source: path.relative(projectRoot, benchmarkPath)
  };
}

const allLogs = [];
const sources = [];
for (const dataset of datasets) {
  const { content, source } = await readPreferredDataset(dataset);
  sources.push(source);
  for (const line of content.split(/\r?\n/)) {
    if (!line.trim()) {
      continue;
    }
    const record = JSON.parse(line);
    allLogs.push({
      dataset: record.dataset ?? dataset,
      timestamp: record.timestamp ?? "",
      timestamp_ms: record.timestamp_ms ?? null,
      level: String(record.level ?? "UNKNOWN").toUpperCase(),
      service: record.component ?? record.service ?? record.logger ?? `${dataset}-service`,
      message: record.message ?? record.raw_log ?? "",
      rawLog: record.raw_log ?? record.message ?? "",
      log_id: record.log_id ?? null,
      line_number: record.line_number ?? null,
      template_id: record.template_id ?? null,
      anomaly: record.anomaly ?? null,
      anomaly_score: record.anomaly_score ?? null,
      anomaly_level: record.anomaly_level ?? null,
      anomaly_decision: record.anomaly_decision ?? null,
      anomaly_baseline_status: record.anomaly_baseline_status ?? null,
      anomaly_reasons: record.anomaly_reasons ?? null,
      anomaly_components: record.anomaly_components ?? null
    });
  }
}

const logs = selectDashboardLogs(allLogs, {
  now: dashboardNow,
  timeZone: dashboardTimeZone,
  latestLimit: Number(process.env.DASHBOARD_LATEST_LOG_LIMIT ?? 200)
});

await mkdir(path.dirname(outputPath), { recursive: true });
await writeFile(
  outputPath,
  `${JSON.stringify(
    {
      generatedAt: new Date().toISOString(),
      source: sources,
      filter: {
        mode: "current-day",
        date: dashboardDate,
        timeZone: dashboardTimeZone,
        inputLogCount: allLogs.length
      },
      logs
    },
    null,
    2
  )}\n`,
  "utf8"
);

console.log(
  `Wrote ${logs.length} dashboard logs (${dashboardDate}, ${dashboardTimeZone}) to ${path.relative(
    projectRoot,
    outputPath
  )}`
);
