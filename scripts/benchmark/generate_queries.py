"""Generate deterministic, data-informed seed queries for retrieval benchmarks."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.core.io_utils import benchmark_dir, write_jsonl
from src.core.schema import (
    DATASETS,
    Category,
    Intent,
    Language,
    QueryFilters,
    QueryLevel,
    QueryRecord,
    validate_dataset,
    validate_query_record,
)


EXPECTED_QUERY_COUNT = 30
EXPECTED_LEVEL_COUNTS = {"easy": 6, "medium": 18, "hard": 6}
EXPECTED_LANGUAGE_COUNTS = {"vi": 21, "en": 9}


@dataclass(frozen=True, slots=True)
class QuerySpec:
    query: str
    language: Language
    query_level: QueryLevel
    category: Category
    intent: Intent
    filters: QueryFilters = field(default_factory=QueryFilters)


QUERY_BANK: dict[str, tuple[QuerySpec, ...]] = {
    "apache": (
        QuerySpec("Có worker nào của Apache rơi vào trạng thái lỗi không?", "vi", "easy", "service_unavailable", "log_retrieval"),
        QuerySpec("Có request nào bị chặn vì không đủ quyền truy cập không?", "vi", "easy", "permission", "log_retrieval"),
        QuerySpec("Apache có dấu hiệu khởi tạo hoặc worker bất thường không?", "vi", "easy", "unknown", "status_overview"),
        QuerySpec("Có lỗi nào khiến web service không phục vụ ổn định không?", "vi", "easy", "service_unavailable", "log_retrieval"),
        QuerySpec("Find Apache worker errors that may affect availability.", "en", "easy", "service_unavailable", "log_retrieval"),
        QuerySpec("Are there forbidden directory access events?", "en", "easy", "permission", "log_retrieval"),
        QuerySpec("Tìm các lỗi ERROR liên quan đến workerEnv hoặc mod_jk.", "vi", "medium", "service_unavailable", "incident_investigation", QueryFilters(level="ERROR")),
        QuerySpec("Có worker child nào bị đặt vào trạng thái không khỏe không?", "vi", "medium", "service_unavailable", "incident_investigation", QueryFilters(level="ERROR")),
        QuerySpec("Tìm các request bị từ chối do rule truy cập thư mục.", "vi", "medium", "permission", "log_retrieval", QueryFilters(level="ERROR")),
        QuerySpec("Có client nào cố truy cập thư mục nhưng bị Apache cấm không?", "vi", "medium", "permission", "incident_investigation", QueryFilters(level="ERROR")),
        QuerySpec("Kiểm tra các thông báo NOTICE về quá trình khởi tạo worker.", "vi", "medium", "unknown", "status_overview", QueryFilters(level="NOTICE")),
        QuerySpec("Có bản ghi scoreboard hoặc child process nào đáng chú ý không?", "vi", "medium", "unknown", "log_retrieval", QueryFilters(level="NOTICE")),
        QuerySpec("Tìm dấu hiệu mod_jk connector đang ở trạng thái lỗi.", "vi", "medium", "service_unavailable", "incident_investigation"),
        QuerySpec("Có lỗi Apache nào lặp lại quanh worker process không?", "vi", "medium", "service_unavailable", "status_overview", QueryFilters(level="ERROR")),
        QuerySpec("Tìm các dấu hiệu web tier bị suy giảm nhưng không phải lỗi quyền truy cập.", "vi", "medium", "unknown", "incident_investigation"),
        QuerySpec("Find repeated worker error-state messages.", "en", "medium", "service_unavailable", "log_retrieval", QueryFilters(level="ERROR")),
        QuerySpec("Find denied access attempts against directory listings.", "en", "medium", "permission", "log_retrieval"),
        QuerySpec("Show Apache startup or worker initialization notices.", "en", "medium", "unknown", "status_overview", QueryFilters(level="NOTICE")),
        QuerySpec("Look for web server health signals around child workers.", "en", "medium", "unknown", "incident_investigation"),
        QuerySpec("Which Apache errors suggest requests may not be served reliably?", "en", "medium", "service_unavailable", "incident_investigation"),
        QuerySpec("Có chuỗi ERROR nào cho thấy worker Apache bị kẹt trong trạng thái lỗi không?", "vi", "medium", "service_unavailable", "incident_investigation", QueryFilters(level="ERROR")),
        QuerySpec("Có dấu hiệu phân quyền sai khiến nhiều request đến web root thất bại không?", "vi", "medium", "permission", "incident_investigation"),
        QuerySpec("Vì sao Apache có thể vẫn chạy nhưng worker lại không xử lý request ổn định?", "vi", "hard", "service_unavailable", "incident_investigation"),
        QuerySpec("Có nhóm log nào cho thấy lỗi worker lặp lại theo thời gian không?", "vi", "hard", "service_unavailable", "status_overview"),
        QuerySpec("Tìm bối cảnh trước sau các lỗi permission để xem có phải cấu hình web root sai không.", "vi", "hard", "permission", "incident_investigation"),
        QuerySpec("Có tín hiệu NOTICE nào giúp phân biệt khởi động bình thường với worker bất thường không?", "vi", "hard", "unknown", "incident_investigation", QueryFilters(level="NOTICE")),
        QuerySpec("Which logs suggest mod_jk worker health is degrading over time?", "en", "hard", "service_unavailable", "incident_investigation"),
        QuerySpec("Find evidence of repeated forbidden access that may indicate an Apache config issue.", "en", "hard", "permission", "incident_investigation"),
        QuerySpec("Có lỗi nào không nói service down trực tiếp nhưng cho thấy Apache phục vụ không ổn định không?", "vi", "medium", "service_unavailable", "incident_investigation"),
        QuerySpec("Có bất thường tổng quan nào trong vòng đời child worker không?", "vi", "medium", "unknown", "status_overview"),
    ),
    "openstack": (
        QuerySpec("Có request Nova API nào xử lý chậm bất thường không?", "vi", "easy", "latency", "log_retrieval"),
        QuerySpec("Có cảnh báo nào về image cache hoặc base file không?", "vi", "easy", "storage", "log_retrieval"),
        QuerySpec("Có sự kiện mạng liên quan đến VIF của instance không?", "vi", "easy", "network", "log_retrieval"),
        QuerySpec("Control plane Nova có dấu hiệu bất thường không?", "vi", "easy", "unknown", "status_overview"),
        QuerySpec("Find slow Nova instance operations.", "en", "easy", "latency", "log_retrieval"),
        QuerySpec("Are there storage cache warnings in Nova compute?", "en", "easy", "storage", "log_retrieval"),
        QuerySpec("Tìm các thao tác instance mất nhiều giây để hoàn thành.", "vi", "medium", "latency", "incident_investigation", QueryFilters(component="nova.compute.manager")),
        QuerySpec("Có API call nào trả về bình thường nhưng thời gian xử lý cao không?", "vi", "medium", "latency", "log_retrieval", QueryFilters(component="nova.osapi_compute.wsgi.server")),
        QuerySpec("Tìm cảnh báo Unknown base file trong image cache.", "vi", "medium", "storage", "log_retrieval", QueryFilters(component="nova.virt.libvirt.imagecache", level="WARN")),
        QuerySpec("Có base image nào đang được kiểm tra hoặc đánh dấu in-use không?", "vi", "medium", "storage", "status_overview", QueryFilters(component="nova.virt.libvirt.imagecache")),
        QuerySpec("Kiểm tra các event network-vif-plugged của instance.", "vi", "medium", "network", "log_retrieval", QueryFilters(component="nova.api.openstack.compute.server_external_events")),
        QuerySpec("Có thao tác lifecycle nào của VM đáng chú ý không?", "vi", "medium", "unknown", "status_overview", QueryFilters(component="nova.compute.manager")),
        QuerySpec("Tìm dấu hiệu mismatch giữa trạng thái instance trong database và hypervisor.", "vi", "medium", "database", "incident_investigation", QueryFilters(component="nova.compute.manager")),
        QuerySpec("Có cảnh báo WARN nào trong nova compute không?", "vi", "medium", "storage", "log_retrieval", QueryFilters(level="WARN")),
        QuerySpec("Tìm các log về resource claim hoặc tài nguyên instance.", "vi", "medium", "unknown", "log_retrieval", QueryFilters(component="nova.compute.claims")),
        QuerySpec("Find image cache records for active or unknown base files.", "en", "medium", "storage", "log_retrieval", QueryFilters(component="nova.virt.libvirt.imagecache")),
        QuerySpec("Find network VIF events emitted by the compute API.", "en", "medium", "network", "log_retrieval", QueryFilters(component="nova.api.openstack.compute.server_external_events")),
        QuerySpec("Look for slow compute-manager operations.", "en", "medium", "latency", "incident_investigation", QueryFilters(component="nova.compute.manager")),
        QuerySpec("Show Nova API request handling records.", "en", "medium", "unknown", "status_overview", QueryFilters(component="nova.osapi_compute.wsgi.server")),
        QuerySpec("Which logs indicate storage housekeeping in Nova image cache?", "en", "medium", "storage", "status_overview"),
        QuerySpec("Có dấu hiệu scheduler hoặc resource tracker thay đổi trạng thái tài nguyên không?", "vi", "medium", "unknown", "status_overview", QueryFilters(component="nova.compute.resource_tracker")),
        QuerySpec("Tìm log metadata API phục vụ request từ instance.", "vi", "medium", "unknown", "log_retrieval", QueryFilters(component="nova.metadata.wsgi.server")),
        QuerySpec("Vì sao thao tác instance bị chậm dù request API vẫn thành công?", "vi", "hard", "latency", "incident_investigation"),
        QuerySpec("Có chuỗi log nào liên kết image cache warning với trạng thái instance không?", "vi", "hard", "storage", "incident_investigation", QueryFilters(level="WARN")),
        QuerySpec("Tìm bằng chứng control plane đang bận xử lý lifecycle của VM.", "vi", "hard", "unknown", "incident_investigation"),
        QuerySpec("Có dấu hiệu network event ảnh hưởng đến tiến trình spawn hoặc resume instance không?", "vi", "hard", "network", "incident_investigation"),
        QuerySpec("Which logs suggest Nova compute is doing slow backend work?", "en", "hard", "latency", "incident_investigation"),
        QuerySpec("Find evidence of image cache inconsistency on the compute host.", "en", "hard", "storage", "incident_investigation"),
        QuerySpec("Có bất thường nào giữa database, hypervisor và trạng thái instance không?", "vi", "medium", "database", "incident_investigation"),
        QuerySpec("Có dấu hiệu tổng quan nào cho thấy Nova control plane không khỏe không?", "vi", "medium", "unknown", "status_overview"),
    ),
    "hdfs": (
        QuerySpec("Có lỗi nào khi DataNode phục vụ block không?", "vi", "easy", "service_unavailable", "log_retrieval"),
        QuerySpec("Có block nào được ghi nhận hoặc cập nhật trong HDFS không?", "vi", "easy", "storage", "log_retrieval"),
        QuerySpec("Có node nào liên quan đến truyền dữ liệu block không?", "vi", "easy", "storage", "log_retrieval"),
        QuerySpec("Cluster HDFS có dấu hiệu bất thường không?", "vi", "easy", "unknown", "status_overview"),
        QuerySpec("Find block transfer exceptions in HDFS.", "en", "easy", "service_unavailable", "log_retrieval"),
        QuerySpec("Are there block metadata updates in NameNode logs?", "en", "easy", "storage", "log_retrieval"),
        QuerySpec("Tìm exception khi DataXceiver gửi block cho client hoặc node khác.", "vi", "medium", "service_unavailable", "incident_investigation", QueryFilters(component="dfs.DataNode$DataXceiver", level="WARN")),
        QuerySpec("Có block nào được DataNode nhận hoặc phục vụ không?", "vi", "medium", "storage", "log_retrieval", QueryFilters(component="dfs.DataNode$DataXceiver")),
        QuerySpec("Kiểm tra các log PacketResponder kết thúc xử lý block.", "vi", "medium", "storage", "status_overview", QueryFilters(component="dfs.DataNode$PacketResponder")),
        QuerySpec("Tìm cập nhật blockMap từ FSNamesystem.", "vi", "medium", "storage", "log_retrieval", QueryFilters(component="dfs.FSNamesystem")),
        QuerySpec("Có block nào được allocate cho file tạm trong HDFS không?", "vi", "medium", "storage", "log_retrieval", QueryFilters(component="dfs.FSNamesystem")),
        QuerySpec("Tìm các cảnh báo WARN liên quan đến block serving.", "vi", "medium", "service_unavailable", "incident_investigation", QueryFilters(level="WARN")),
        QuerySpec("Có quá trình verification block nào thành công không?", "vi", "medium", "unknown", "status_overview", QueryFilters(component="dfs.DataBlockScanner")),
        QuerySpec("Kiểm tra FSDataset trong các thao tác lưu trữ block.", "vi", "medium", "storage", "log_retrieval", QueryFilters(component="dfs.FSDataset")),
        QuerySpec("Có node hoặc địa chỉ nào xuất hiện khi block transfer gặp sự cố không?", "vi", "medium", "service_unavailable", "incident_investigation", QueryFilters(level="WARN")),
        QuerySpec("Find DataXceiver warnings while serving blocks.", "en", "medium", "service_unavailable", "log_retrieval", QueryFilters(component="dfs.DataNode$DataXceiver", level="WARN")),
        QuerySpec("Find FSNamesystem records that update block locations.", "en", "medium", "storage", "log_retrieval", QueryFilters(component="dfs.FSNamesystem")),
        QuerySpec("Look for PacketResponder block completion events.", "en", "medium", "storage", "status_overview", QueryFilters(component="dfs.DataNode$PacketResponder")),
        QuerySpec("Show block scanner verification records.", "en", "medium", "unknown", "status_overview", QueryFilters(component="dfs.DataBlockScanner")),
        QuerySpec("Which logs show storage activity inside HDFS dataset handling?", "en", "medium", "storage", "log_retrieval", QueryFilters(component="dfs.FSDataset")),
        QuerySpec("Có dấu hiệu block pipeline bị gián đoạn khi phục vụ dữ liệu không?", "vi", "medium", "service_unavailable", "incident_investigation"),
        QuerySpec("Tìm các log về block replication hoặc vị trí block được cập nhật.", "vi", "medium", "storage", "log_retrieval"),
        QuerySpec("Node nào có dấu hiệu gặp lỗi lặp lại khi phục vụ block?", "vi", "hard", "service_unavailable", "incident_investigation", QueryFilters(level="WARN")),
        QuerySpec("Có chuỗi sự kiện nào từ nhận block đến responder kết thúc không?", "vi", "hard", "storage", "incident_investigation"),
        QuerySpec("Tìm bằng chứng blockMap thay đổi quanh các block có sự cố.", "vi", "hard", "storage", "incident_investigation", QueryFilters(component="dfs.FSNamesystem")),
        QuerySpec("Có log nào cho thấy block vẫn được verify dù cluster có cảnh báo không?", "vi", "hard", "unknown", "status_overview"),
        QuerySpec("Which logs suggest HDFS block serving is unreliable?", "en", "hard", "service_unavailable", "incident_investigation"),
        QuerySpec("Find evidence of repeated block movement across DataNodes.", "en", "hard", "storage", "incident_investigation"),
        QuerySpec("Có bất thường nào liên quan cùng lúc đến node, IP và block id không?", "vi", "medium", "service_unavailable", "incident_investigation"),
        QuerySpec("Có dấu hiệu tổng quan nào cho thấy HDFS storage layer không khỏe không?", "vi", "medium", "storage", "status_overview"),
    ),
}


def validate_query_bank(dataset: str, specs: tuple[QuerySpec, ...]) -> None:
    if len(specs) != EXPECTED_QUERY_COUNT:
        raise ValueError(
            f"{dataset} must have {EXPECTED_QUERY_COUNT} queries, got {len(specs)}"
        )
    level_counts = Counter(spec.query_level for spec in specs)
    language_counts = Counter(spec.language for spec in specs)
    if {key: level_counts[key] for key in EXPECTED_LEVEL_COUNTS} != EXPECTED_LEVEL_COUNTS:
        raise ValueError(f"{dataset} query_level distribution is wrong: {level_counts}")
    if {key: language_counts[key] for key in EXPECTED_LANGUAGE_COUNTS} != EXPECTED_LANGUAGE_COUNTS:
        raise ValueError(f"{dataset} language distribution is wrong: {language_counts}")


def generate_queries(dataset: str) -> list[dict[str, Any]]:
    dataset = validate_dataset(dataset)
    specs = QUERY_BANK[dataset]
    validate_query_bank(dataset, specs)

    records: list[dict[str, Any]] = []
    for index, spec in enumerate(specs, start=1):
        record = QueryRecord(
            query_id=f"{dataset}_q{index:03d}",
            dataset=dataset,
            query=spec.query,
            language=spec.language,
            query_level=spec.query_level,
            category=spec.category,
            intent=spec.intent,
            filters=spec.filters,
        ).to_dict()
        validate_query_record(record)
        records.append(record)
    return records


def write_dataset_queries(dataset: str, root: Path, output: Path | None = None) -> Path:
    dataset = validate_dataset(dataset)
    output_path = output or benchmark_dir(dataset, root) / "queries.jsonl"
    records = generate_queries(dataset)
    write_jsonl(output_path, records)
    counts_by_level = Counter(record["query_level"] for record in records)
    counts_by_language = Counter(record["language"] for record in records)
    counts_by_category = Counter(record["category"] for record in records)
    print(f"Dataset: {dataset}")
    print(f"Output: {output_path}")
    print(f"Queries: {len(records)}")
    print(
        "Levels: "
        + ", ".join(f"{key}={counts_by_level[key]}" for key in ("easy", "medium", "hard"))
    )
    print(
        "Languages: "
        + ", ".join(f"{key}={counts_by_language[key]}" for key in ("vi", "en"))
    )
    print(
        "Categories: "
        + ", ".join(f"{key}={value}" for key, value in counts_by_category.most_common())
    )
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=(*DATASETS, "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path. Only valid when --dataset is not 'all'.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dataset == "all" and args.output is not None:
        raise SystemExit("--output can only be used with one dataset, not --dataset all")

    datasets = DATASETS if args.dataset == "all" else (args.dataset,)
    for index, dataset in enumerate(datasets):
        if index:
            print()
        write_dataset_queries(dataset, args.root, args.output)


if __name__ == "__main__":
    main()
