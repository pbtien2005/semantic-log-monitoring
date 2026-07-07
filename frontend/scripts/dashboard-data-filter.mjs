export const DEFAULT_DASHBOARD_TIME_ZONE = "Asia/Ho_Chi_Minh";

export function getDateKey(value, timeZone = DEFAULT_DASHBOARD_TIME_ZONE) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  const parts = new Intl.DateTimeFormat("en", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(date);
  const part = (type) => parts.find((item) => item.type === type)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

export function filterCurrentDayLogs(logs, options = {}) {
  const timeZone = options.timeZone ?? DEFAULT_DASHBOARD_TIME_ZONE;
  const now = options.now ?? new Date();
  const currentDateKey = getDateKey(now, timeZone);

  return logs.filter((log) => {
    const timestamp = log.timestamp || log.timestamp_ms || "";
    return getDateKey(timestamp, timeZone) === currentDateKey;
  });
}

export function selectDashboardLogs(logs, options = {}) {
  const currentDayLogs = filterCurrentDayLogs(logs, options);
  if (currentDayLogs.length) {
    return currentDayLogs;
  }

  const latestLimit = options.latestLimit ?? 200;
  return [...logs]
    .sort((left, right) => timestampValue(right) - timestampValue(left))
    .slice(0, latestLimit);
}

function timestampValue(log) {
  const value = log.timestamp || log.timestamp_ms || "";
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? Number.NEGATIVE_INFINITY : date.getTime();
}
