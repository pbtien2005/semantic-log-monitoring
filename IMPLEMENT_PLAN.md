# Implement Plan: Anomaly Detection and RCA MVP

## Goal

Add a non-rule-based anomaly detection layer to the semantic log monitoring
project, then surface anomaly status in the live log stream and provide a
compact RCA evidence list for anomalous logs.

The MVP should answer two operator questions:

1. Which incoming logs look unusual compared with learned history?
2. When a log is anomalous, which earlier logs are the strongest root-cause
   candidates?

## Non-Goals for V1

- No graph-based RCA.
- No LLM/agent-based RCA engine.
- No keyword/rule-based anomaly decision.
- No DeepLog/LSTM/Transformer training.
- No invariant mining or metric/trace correlation in the first release.

`level`, `message`, and known error words may be displayed as context, but they
must not be the main anomaly decision mechanism. If `level` is used, keep it as
a small triage hint or set its score weight to `0.0` in production config.

## Current Starting Point

Relevant existing pieces:

- `src/anomaly/schema.py`: anomaly schemas and config.
- `src/anomaly/scoring.py`: baseline builder and explainable scoring using
  template frequency, transition surprise, and window distribution shift.
- `tests/test_anomaly_detection.py`: tests for current anomaly scoring behavior.
- `src/chunking/builders.py`: line chunk construction with template/entity
  metadata.
- `infra/scripts/ingestion/consume_kafka_logs.py`: online Kafka worker path:
  raw records -> chunks -> Milvus rows.
- `frontend/scripts/build-dashboard-data.mjs`: static dashboard data build.
- `frontend/src/domain/logs.ts`: React dashboard log normalization/filtering.
- `frontend/src/App.tsx`: current log stream UI.

The plan is to extend the existing anomaly module instead of replacing it.

## Selected Detection Strategy

Use unsupervised normality modeling:

```text
anomaly_score =
    0.40 * template_surprise
  + adaptive_transition_weight * transition_surprise
  + adaptive_window_weight * window_distribution_shift
```

Core signals:

- `template_surprise`: how rare/new a template is for a service/component.
- `transition_surprise`: how unlikely the current template is after the previous
  template for the same service/session stream.
- `window_distribution_shift`: how much the recent window's template distribution
  differs from learned normal windows.

Transition surprise is only reliable when the stream is meaningful. Resolve the
transition scope in this priority order:

```text
1. trace_id / request_id / session_id
2. block_id / instance_id / entity_id
3. host / pod / source_id
4. service/component fallback
```

Use higher transition weight only for scoped streams:

```text
scoped stream:       transition_weight = 0.35, window_weight = 0.25
service fallback:    transition_weight = 0.15-0.20, window_weight = 0.40-0.45
```

Service-level fallback can be noisy because multiple requests are interleaved.
It is still useful for demo/local data, but it must not dominate the score.

For V1, avoid using error keywords as anomaly logic. Treat log level separately
as `severity_hint`, not as the detector's core score.

Thresholds must be configuration, not hardcoded constants:

```yaml
anomaly:
  thresholds:
    low: 0.40
    medium: 0.60
    high: 0.80
```

## Target Data Contract

Every enriched log should expose:

```json
{
  "log_id": "openstack:abc",
  "template_id": "template::...",
  "anomaly": {
    "score": 0.82,
    "level": "high",
    "decision": "anomalous",
    "baseline_status": "ready",
    "reasons": [
      "new_template_for_service",
      "new_template_transition",
      "window_template_distribution_shift"
    ],
    "components": {
      "template_score": 1.0,
      "transition_score": 0.9,
      "window_score": 0.6,
      "severity_hint": 0.0
    }
  }
}
```

Suggested levels:

- `normal`: score < 0.40
- `low`: 0.40 <= score < 0.60
- `medium`: 0.60 <= score < 0.80
- `high`: score >= 0.80
- `unknown`: score could not be computed

Suggested decisions:

- `normal`: below low threshold
- `watch`: low or medium score
- `anomalous`: high score
- `warming_up`: service does not have enough baseline history
- `not_scored`: scoring failed or is disabled

`warming_up` is a baseline state, not an anomaly level. Keep it out of
`level` so UI and downstream logic do not confuse "unknown baseline" with
"high anomaly".

Suggested baseline status:

- `ready`
- `insufficient_history`
- `missing_baseline`
- `disabled`
- `error`

If a service is warming up, prefer this payload:

```json
{
  "anomaly": {
    "score": null,
    "level": "unknown",
    "decision": "warming_up",
    "baseline_status": "insufficient_history",
    "reasons": ["insufficient_service_history"],
    "components": {
      "template_score": null,
      "transition_score": null,
      "window_score": null,
      "severity_hint": 0.0
    }
  }
}
```

## Online Scoring State

Scoring is not purely per-log. The online path needs recent state:

```text
online_state[service]:
  recent_template_window
  recent_counts
  last_seen_template_by_stream_key
```

Add:

```text
src/anomaly/state.py
  OnlineAnomalyState
  stream_key_for(record)
  update(record_or_chunk)
  get_recent_window(service)
  get_prev_template(stream_key)
```

The state object should be used by Kafka/replay scoring so transition and window
scores are computed consistently with the selected transition scope.

## RCA Candidate Retrieval for Anomalous Logs

Use a lightweight evidence ranker, not graph or LLM:

```text
rca_score =
    0.30 * anomaly_score
  + 0.25 * temporal_prior_score
  + 0.20 * service_or_component_score
  + 0.15 * template_relatedness
  + 0.10 * entity_match_score
```

Candidate generation:

1. Start from an anomalous log.
2. Open an investigation window before it.
3. Prefer logs sharing `trace_id`, `request_id`, `instance_id`, or `block_id`.
4. Fall back to same `service/component` within the same time window.
5. Include related templates and high-anomaly-score logs around that time.
6. Rank and return top 5-15 evidence logs in chronological order.

Default window:

```text
T - 10 minutes -> T
same dataset
same service/component when no stronger ID exists
```

When correlation IDs exist:

```text
request_id / trace_id / session_id first
block_id / instance_id second
```

When no ID exists:

```text
same service/component
+ time window before seed
+ related template_ids
+ high anomaly score
+ global anomaly templates around that time
```

No root-cause prose generation is required in V1. The UI can show candidate
rows and their score/reason.

Use careful wording in product/UI:

- `root-cause candidates`
- `probable earlier evidence`
- `suspected upstream evidence`

Do not present candidates as certain root cause in V1.

## Implementation Phases

### Phase 1: Make Anomaly Scoring Contract Production-Ready

Scope:

- Keep `src/anomaly/scoring.py` as the core baseline scorer.
- Add a config preset for non-rule-based mode:
  - `template_weight = 0.40`
  - `transition_weight = 0.35` for scoped streams
  - `transition_weight = 0.15-0.20` for service fallback streams
  - `window_weight = 0.25-0.45`, depending on transition scope
  - `log_level_weight = 0.0`
- Add threshold config rather than hardcoded thresholds.
- Add a helper that converts `AnomalyScore` into a compact payload suitable for
  JSON/API/dashboard use.
- Rename output concepts clearly:
  - `decision`: `normal`, `watch`, `anomalous`, `warming_up`, `not_scored`
  - `baseline_status`: `ready`, `insufficient_history`, `missing_baseline`,
    `disabled`, `error`
  - `level`: `normal`, `low`, `medium`, `high`, `unknown`
- Keep `severity_hint` separate from anomaly score.
- Ensure scoring accepts records from both parsed benchmark logs and line
  chunks.

Tests:

- New test that `ERROR` alone does not produce high anomaly when template and
  transition are normal.
- New test that a new template/transition is anomalous even when level is `INFO`.
- New test that `warming_up` is emitted as a decision/baseline status, not as an
  anomaly level.
- Existing `tests/test_anomaly_detection.py` should continue to pass after
  updating expected behavior if needed.

Acceptance:

- Detector can score a list of logs without keyword rules.
- Scores include reason/evidence fields.
- Undertrained services return `decision=warming_up`,
  `baseline_status=insufficient_history`, and `level=unknown`.

### Phase 2: Offline Baseline Artifact

Scope:

- Add a CLI script:

```text
infra/scripts/anomaly/build_anomaly_baseline.py
```

- Input:

```text
data/chunking/{dataset}/log_lines.jsonl
```

- Output:

```text
data/anomaly/baselines/{dataset}/baseline.json
```

- The artifact should store enough information to reconstruct
  `AnomalyBaseline`.
- Store baseline metadata:

```text
baseline_version
trained_at
dataset
mode = all | normal_only
min_service_events
min_windows_per_service
smoothing_alpha
thresholds
scoring_weights
```

Tests:

- Unit test baseline serialize/deserialize round trip.
- CLI smoke test with a small fixture or `--limit`.

Acceptance:

- Baseline can be built for `apache`, `hdfs`, `openstack`, and `all`.
- Baseline file is deterministic for the same input.

### Phase 3: Add Online Anomaly State

Scope:

- Add:

```text
src/anomaly/state.py
```

- Implement:
  - `OnlineAnomalyState`
  - `stream_key_for(record)`
  - `get_prev_template(stream_key)`
  - `get_recent_window(service)`
  - `update(record_or_chunk)`
- Support transition scope priority:
  - trace/request/session
  - block/instance/entity
  - host/pod/source
  - service fallback
- Return transition confidence/scope so scoring can lower transition weight for
  noisy service-level streams.

Tests:

- Stream key prefers request/trace IDs over service fallback.
- Service fallback is marked low-confidence.
- State updates previous template and rolling window independently per stream
  and service.

Acceptance:

- Online/replay scoring has deterministic recent state.
- Transition scoring is not accidentally based on unrelated interleaved logs
  when a stronger stream key exists.

### Phase 4: Enrich Static Dashboard Data

Scope:

- Extend `frontend/scripts/build-dashboard-data.mjs` or add a Python prebuild
  step that produces anomaly-enriched dashboard logs.
- Prefer Python for scoring because the anomaly engine lives in Python.
- Suggested script:

```text
infra/scripts/anomaly/build_dashboard_anomaly_data.py
```

- Output should still feed React through:

```text
frontend/public/dashboard-data.json
```

Additional log fields:

```text
anomaly_score
anomaly_level
anomaly_decision
anomaly_baseline_status
anomaly_reasons
anomaly_components
template_id
```

Tests:

- Frontend domain test verifies anomaly fields survive normalization.
- Script test verifies enriched logs include anomaly fields.

Acceptance:

- React dashboard can display anomaly data from static benchmark logs.
- Existing dashboard still works if anomaly fields are absent.

### Phase 5: Show Anomaly in Log Stream

Scope:

- Extend `frontend/src/domain/logs.ts`:
  - add anomaly fields to `LogRecord` and `DashboardLog`
  - normalize missing anomaly to safe defaults
- Extend `LogStream` in `frontend/src/App.tsx`:
  - show anomaly badge
  - show score
  - show short reason list on hover or compact text
- Add CSS classes for:
  - `anomaly-normal`
  - `anomaly-low`
  - `anomaly-medium`
  - `anomaly-high`
  - `anomaly-warming-up`
  - `anomaly-not-scored`

Tests:

- React test verifies high anomaly badge appears on a sample log.
- Domain test verifies sorting/filtering still works.

Acceptance:

- Operator can see anomalous rows directly in the live log stream list.
- Normal rows remain visually quiet.

### Phase 6: RCA Evidence Ranker

Scope:

- Add package:

```text
src/rca/
  __init__.py
  schema.py
  ranking.py
```

- Implement:
  - `build_investigation_window(logs, incident_log, lookback)`
  - `score_rca_candidates(candidates, incident_log)`
  - `rank_rca_evidence(logs, incident_log, limit=10)`

Candidate score:

```text
0.30 candidate anomaly score
+ 0.25 temporal prior score
+ 0.20 service/component score
+ 0.15 template relatedness
+ 0.10 entity match score
```

Entity matching should support:

```text
trace_id
request_id
instance_id
block_id
host
service/component fallback
```

Fallback when no entity exists:

```text
same service/component
+ time window before incident
+ related template_ids
+ high anomaly score
+ global anomaly templates around that time
```

Tests:

- Same `request_id` before incident ranks above unrelated logs.
- Earlier anomalous candidate ranks above later symptom-only candidate.
- If no entity exists, same service/window fallback still returns candidates.
- RCA output wording uses "candidate/evidence" language rather than claiming a
  certain root cause.

Acceptance:

- Given one anomalous log, the engine returns a ranked evidence list without
  LLM or graph logic.

### Phase 7: Surface RCA Candidates

Scope:

- Add UI behavior:
  - clicking an anomalous log opens a side/detail panel
  - panel shows top RCA evidence rows
  - include timestamp, service, score, anomaly level, and reason
- Static dashboard can compute RCA client-side from the loaded enriched logs, or
  call a Python API later. For MVP, client-side is acceptable if data is static.

Preferred split:

- Python computes anomaly fields.
- TypeScript can compute a simple RCA evidence list for display.
- Later, move RCA ranking to API if live Kafka data becomes the source.

Tests:

- UI test clicks an anomalous log and sees evidence section.

Acceptance:

- An anomalous log is actionable: the operator sees "what likely led to it".

### Phase 8: Online Kafka Path

Scope:

- Update `infra/scripts/ingestion/consume_kafka_logs.py`:
  - load anomaly baseline on startup
  - initialize `OnlineAnomalyState`
  - score chunks before `build_log_line_rows`
  - include anomaly payload in Milvus row payload
- Add env vars:

```text
ANOMALY_BASELINE_PATH
ANOMALY_ENABLED=true
```

- If baseline is missing, worker should continue and mark logs as
  `decision=warming_up` and `baseline_status=missing_baseline`, not crash.

Tests:

- Worker unit test verifies anomaly fields are added to upserted rows.
- Worker unit test verifies missing baseline does not block ingestion.
- Worker unit test verifies service-level transition fallback uses lower
  confidence/weight than request-scoped transition state.

Acceptance:

- Online-ingested logs carry anomaly fields into Milvus.
- The detection path does not break ingestion reliability.

## Suggested PR Sequence

1. `anomaly-output-contract`: finalize anomaly level, decision, baseline status,
   thresholds, and payload helpers.
2. `anomaly-baseline-cli`: baseline build/load artifact.
3. `online-anomaly-state`: stream key selection and rolling state.
4. `kafka-anomaly-enrichment`: score online Kafka logs and persist anomaly
   payloads.
5. `dashboard-anomaly-data`: enrich static dashboard JSON.
6. `react-anomaly-badges`: display score/decision in log stream.
7. `rca-ranker`: add lightweight RCA evidence ranking engine.
8. `react-rca-panel`: show evidence list for anomalous logs.

## Verification Commands

Python:

```powershell
python -m pytest tests/test_anomaly_detection.py
python -m pytest tests/test_kafka_worker.py
python -m pytest tests/test_no_streamlit_ui.py
```

Frontend:

```powershell
cd frontend
npm test -- --run
npm run build
```

Full build:

```powershell
npm run build --prefix frontend
docker compose build app api
```

## Risks and Guardrails

- False positives during warm-up:
  - keep `decision=warming_up` and `baseline_status=insufficient_history`
    until enough service history exists.
- Static benchmark bias:
  - tune thresholds on benchmark first, then retune for online services.
- Treating severity as anomaly:
  - keep `log_level_weight = 0.0` for the non-rule-based mode.
- Noisy transitions from interleaved logs:
  - use transition scope priority and lower transition weight for service-level
    fallback.
- UI noise:
  - only highlight `medium` and `high`; keep `low` subtle.
- Ingestion reliability:
  - anomaly scoring failure should not prevent log ingest/upsert.

## Definition of Done for MVP

- A baseline can be built from historical chunked logs.
- New/dashboard logs are enriched with anomaly score, level, decision, and
  baseline status.
- Online scoring keeps rolling state for previous templates and recent windows.
- The live log stream shows anomaly badges, scores, and decisions.
- An anomalous log can reveal a ranked RCA evidence list.
- Detection does not depend on keywords, graph logic, or LLM reasoning.
