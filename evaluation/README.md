# Semantic Log Monitoring Evaluation

This directory contains evaluation-only tooling. It must not affect production
API, ingestion, retrieval, anomaly scoring, or RCA ranking unless an evaluation
script is explicitly called.

## Phase 1 Foundation

The current foundation provides:

- streaming JSONL and JSON helpers in `evaluation.io`
- deterministic ID helpers in `evaluation.ids`
- UTC timestamp helpers in `evaluation.time_utils`
- SHA-256 manifest helpers in `evaluation.checksums`
- path helpers in `evaluation.paths`
- a stdlib-only config loader in `evaluation.config`
- placeholder artifact directories for datasets, scenarios, results, reports,
  and run history

## Config

The starter config lives at:

```bash
evaluation/config.example.yaml
```

It is intentionally simple and can be loaded without adding PyYAML:

```bash
python -c "from evaluation.config import load_config; print(load_config('evaluation/config.example.yaml'))"
```

Later phases will add dataset generation, validation, loaders, experiment
runners, metrics, review export, and comparison reports.

## Phase 2 Incident Blueprints

Scenario definitions live in:

```bash
evaluation/scenarios/incident_blueprints.jsonl
```

The first blueprint set contains 15 incidents:

- 13 explicit root-cause scenarios
- 2 silent root-cause scenarios
- OpenStack, HDFS, and Apache coverage
- per-scenario service/entity metadata
- root cause, intermediate evidence, and incident event templates
- noise plans for lexical noise, template duplication, entity collision,
  temporal noise, and cross-service noise

## Phase 3 Dataset Generator

Generate the initial deterministic controlled dataset:

```bash
python -m evaluation.scripts.generate_dataset --config evaluation/config.example.yaml
```

Or override core counts directly:

```bash
python -m evaluation.scripts.generate_dataset \
  --output-dir evaluation/datasets \
  --log-count 2000 \
  --query-count 50 \
  --incident-count 15 \
  --anomaly-count 18 \
  --seed 20260714
```

The generator writes:

- `evaluation/datasets/logs.jsonl`
- `evaluation/datasets/groundtruth_queries.jsonl`
- `evaluation/datasets/anomalies.jsonl`
- `evaluation/datasets/incidents.jsonl`
- `evaluation/datasets/dataset_manifest.json`

The generated log records intentionally include evaluation-only fields such as
`ground_truth_role` and `scenario_id`. Later loader phases must strip those
fields before sending records through production ingestion.

## Phase 4 Ground Truth Validation

Validate the generated dataset:

```bash
python -m evaluation.scripts.validate_groundtruth --dataset-dir evaluation/datasets
```

The validator checks cross-file references, duplicate IDs, timestamp ordering,
explicit versus silent root-cause contracts, relevance values, required evidence
subsets, deterministic log IDs, manifest counts, and SHA-256 checksums. It exits
with a non-zero status if validation fails.

## Phase 5 Evaluation Log Loader

Dry-run the loader without sending logs:

```bash
python -m evaluation.scripts.load_evaluation_logs \
  --dataset evaluation/datasets/logs.jsonl \
  --mode api \
  --dry-run
```

Send logs through the real ingestion API:

```bash
python -m evaluation.scripts.load_evaluation_logs \
  --dataset evaluation/datasets/logs.jsonl \
  --mode api \
  --base-url http://localhost:8000 \
  --batch-size 100
```

The loader strips evaluation-only fields such as `ground_truth_role` and
`scenario_id` before submitting payloads. `direct` mode is intentionally guarded
until a reusable full worker entrypoint can be called without bypassing the
production normalize/chunk/embed/anomaly/Milvus/OpenSearch path.

## Phase 6 Retrieval Experiment Runner

Run local evaluation-only retrieval adapters:

```bash
python -m evaluation.scripts.run_retrieval_evaluation \
  --experiment baseline_log_only_v1 \
  --top-k 24

python -m evaluation.scripts.run_retrieval_evaluation \
  --experiment template_first_recency_v1 \
  --top-k 24
```

Outputs are written to:

- `evaluation/results/retrieval_baseline_log_only_v1.jsonl`
- `evaluation/results/retrieval_template_first_recency_v1.jsonl`

These adapters do not call production retrieval and do not use ground-truth
labels while ranking. They provide deterministic result files for metrics and
review workflow development before live Milvus/OpenSearch-backed experiments are
connected.

## Phase 8 Live Retrieval Runner

After loading `evaluation/datasets/logs.jsonl` through the ingestion API, run the
same benchmark queries against the production retrieval primitives:

```bash
python -m evaluation.scripts.run_live_retrieval_evaluation \
  --mode direct \
  --experiment production_direct_v1 \
  --top-k 24 \
  --template-k 8
```

This calls the production `plan_query` + `execute_plan` path and writes:

```bash
evaluation/results/retrieval_production_direct_v1.jsonl
```

If you expose a retrieval-compatible HTTP endpoint, the API runner can be used:

```bash
python -m evaluation.scripts.run_live_retrieval_evaluation \
  --mode api \
  --base-url http://localhost:8000 \
  --endpoint /api/chat \
  --experiment production_api_v1
```

The API response must contain ranked log objects under common keys such as
`logs`, `log_lines`, `results`, `retrieved`, `context`, or `data`. Each log
object should include `log_id`; optional `template_id` and `score` fields are
preserved. The existing `/api/chat` endpoint currently returns summarized
context, so direct mode is the recommended benchmark path unless the API is
extended to return ranked evidence IDs.

## Phase 7 Retrieval and RCA Metrics

Calculate metrics from a retrieval result file:

```bash
python -m evaluation.scripts.calculate_retrieval_metrics \
  --results evaluation/results/retrieval_baseline_log_only_v1.jsonl

python -m evaluation.scripts.calculate_retrieval_metrics \
  --results evaluation/results/retrieval_template_first_recency_v1.jsonl
```

Default reports are written to:

- `evaluation/reports/retrieval_baseline_log_only_v1_metrics.json`
- `evaluation/reports/retrieval_template_first_recency_v1_metrics.json`

The metric layer reports retrieval quality with `Hit@K`, `Recall@K`,
`Precision@K`, `MRR`, `nDCG@K`, `RequiredEvidenceRecall@K`,
`UniqueTemplate@K`, and `DuplicateTemplateRatio@K`. It also reports RCA quality
with `RootCauseHit@K`, `RootCauseMRR`, `EvidenceRecall@K`, and
`CausalChainCompleteness@K`. Silent root-cause queries are excluded from
root-cause hit/MRR denominators and counted separately because the root cause is
intentionally absent from observable logs.

Calculate anomaly metrics once an anomaly experiment writes prediction JSONL:

```bash
python -m evaluation.scripts.calculate_anomaly_metrics \
  --predictions evaluation/results/anomaly_predictions.jsonl \
  --threshold 0.5
```

Prediction rows should include `log_id`, plus either `predicted_anomaly` (or
`is_anomaly`) or a numeric `score` that can be thresholded. Optional fields
`severity`/`predicted_severity` and `signals`/`predicted_signals` are used for
severity agreement and signal-overlap metrics. The report includes precision,
recall, F1, false-positive rate, false-negative rate, accuracy, severity
agreement, score-range agreement, and signal overlap.
