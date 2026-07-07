from __future__ import annotations

from src.anomaly.persistence import load_baseline, save_baseline
from src.anomaly.schema import AnomalyConfig
from src.anomaly.scoring import build_baseline, score_log_sequence


def test_baseline_round_trips_through_json(tmp_path) -> None:
    records = [
        {
            "line_number": index,
            "log_id": f"log-{index}",
            "dataset": "demo",
            "component": "api",
            "template_id": "T1" if index % 2 else "T2",
            "level": "INFO",
            "timestamp_ms": index * 1000,
            "raw_log": "api INFO",
        }
        for index in range(1, 12)
    ]
    config = AnomalyConfig(min_logs_per_service=3, min_windows_per_service=100)
    path = tmp_path / "baseline.json"

    save_baseline(build_baseline(records, config=config), path)
    loaded = load_baseline(path)
    [score] = score_log_sequence(
        [
            {
                **records[-1],
                "line_number": 20,
                "log_id": "log-20",
                "template_id": "T99",
                "timestamp_ms": 20_000,
            }
        ],
        loaded,
    )

    assert loaded.config.min_logs_per_service == 3
    assert loaded.metadata.trained_at is not None
    assert score.baseline_status == "ready"
    assert "new_template_for_service" in score.reasons
