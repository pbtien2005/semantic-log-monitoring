import { describe, expect, it } from "vitest";

import { filterCurrentDayLogs, getDateKey, selectDashboardLogs } from "./dashboard-data-filter.mjs";

describe("dashboard current-day data filter", () => {
  it("keeps only logs matching the current date in the configured timezone", () => {
    const logs = [
      { timestamp: "2017-05-16 00:14:47.687", message: "old benchmark log" },
      { timestamp: "2026-07-06T08:15:00+07:00", message: "today log" },
      { timestamp: "2026-07-05T23:58:00+07:00", message: "yesterday log" }
    ];

    expect(
      filterCurrentDayLogs(logs, {
        now: new Date("2026-07-06T09:00:00+07:00"),
        timeZone: "Asia/Ho_Chi_Minh"
      })
    ).toEqual([{ timestamp: "2026-07-06T08:15:00+07:00", message: "today log" }]);
  });

  it("formats date keys using Vietnam local date instead of UTC day", () => {
    expect(getDateKey("2026-07-05T18:30:00Z", "Asia/Ho_Chi_Minh")).toBe("2026-07-06");
  });

  it("keeps current-day logs that only provide timestamp_ms", () => {
    const currentMs = new Date("2026-07-06T10:00:00+07:00").getTime();
    const oldMs = new Date("2026-07-05T10:00:00+07:00").getTime();

    expect(
      filterCurrentDayLogs(
        [
          { timestamp_ms: oldMs, message: "old numeric timestamp" },
          { timestamp_ms: currentMs, message: "current numeric timestamp" }
        ],
        {
          now: new Date("2026-07-06T12:00:00+07:00"),
          timeZone: "Asia/Ho_Chi_Minh"
        }
      )
    ).toEqual([{ timestamp_ms: currentMs, message: "current numeric timestamp" }]);
  });

  it("uses the latest logs when no current-day logs exist", () => {
    const logs = [
      { timestamp: "2017-05-16T00:14:47Z", message: "newest historical" },
      { timestamp: "2008-11-10T21:15:41Z", message: "oldest historical" },
      { timestamp: "2010-01-01T00:00:00Z", message: "middle historical" }
    ];

    expect(
      selectDashboardLogs(logs, {
        now: new Date("2026-07-06T12:00:00+07:00"),
        timeZone: "Asia/Ho_Chi_Minh",
        latestLimit: 2
      })
    ).toEqual([
      { timestamp: "2017-05-16T00:14:47Z", message: "newest historical" },
      { timestamp: "2010-01-01T00:00:00Z", message: "middle historical" }
    ]);
  });
});
