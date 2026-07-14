# Semantic Log Monitoring

Hệ thống giám sát và phân tích log theo ngữ nghĩa, hỗ trợ theo dõi log, tìm kiếm bằng ngôn ngữ tự nhiên, hỏi đáp theo mô hình RAG, phát hiện bất thường và gợi ý các log liên quan dưới dạng RCA candidates.

Project sử dụng dữ liệu mẫu từ LogHub gồm Apache, OpenStack và HDFS, đồng thời có luồng tiếp nhận log mới phát sinh thông qua Kafka để mô phỏng giám sát gần thời gian thực.

## Tính Năng Chính

- Xử lý và chuẩn hóa log từ các bộ dữ liệu Apache, OpenStack và HDFS.
- Trích xuất thông tin quan trọng như timestamp, level, service/component, template và entity.
- Tạo embedding cho log và lưu vào Milvus để phục vụ tìm kiếm ngữ nghĩa.
- Lưu log gốc vào OpenSearch để truy xuất, lọc và hiển thị lại dữ liệu ban đầu.
- Hỗ trợ hỏi đáp log theo mô hình RAG thông qua API backend và CLIProxyAPI.
- Chấm điểm bất thường dựa trên template frequency, transition surprise và window distribution shift.
- Gợi ý RCA candidates nhằm hỗ trợ phân tích các log có liên quan đến sự cố.
- Cung cấp React dashboard để hiển thị log, bộ lọc, KPI, biểu đồ, anomaly badge và khung chat.
- Hỗ trợ tiếp nhận luồng log mới phát sinh qua Kafka và semantic worker.

## Kiến Trúc Tổng Quát

```text
User / Operator
      |
      v
React Dashboard  <---->  Starlette API
                             |
                             +--> Query Planner
                             +--> Semantic Retrieval
                             +--> RAG Answering ----> CLIProxyAPI / LLM
                             +--> Anomaly Scoring
                             +--> RCA Candidates
                             |
             +---------------+----------------+
             |                                |
          Milvus                         OpenSearch
     Vector database                    Raw log store

Offline data:
Apache / OpenStack / HDFS
      -> parse
      -> chunk/template/entity
      -> embedding
      -> Milvus + dashboard data

Streaming data:
POST /api/ingest/logs
      -> API kiểm tra raw log
      -> Kafka logs.raw
      -> semantic-worker xử lý theo batch
      -> parse/template/entity + batch embedding
      -> Milvus + OpenSearch
```

## Công Nghệ Sử Dụng

- Python: xử lý log, pipeline dữ liệu, retrieval, anomaly detection, RCA và API backend.
- React, TypeScript, Vite: xây dựng dashboard.
- Starlette, Uvicorn: xây dựng và chạy API backend.
- Sentence Transformers, PyTorch: tạo embedding cho log.
- Milvus, PyMilvus: lưu trữ và truy vấn vector log.
- OpenSearch: lưu trữ và truy xuất log gốc.
- Apache Kafka: tiếp nhận và xử lý luồng log mới phát sinh.
- CLIProxyAPI, OpenAI-compatible API: hỗ trợ chức năng hỏi đáp RAG.
- Docker Compose: đóng gói và chạy các thành phần hệ thống.
- pytest, Vitest: kiểm thử backend và frontend.

## Cấu Trúc Thư Mục

```text
app/                      # Starlette API và chat service
src/core/                 # Schema, IO và tiện ích dùng chung
src/ingestion/            # Kafka contract, Kafka IO, raw log store
src/chunking/             # Parse log, build chunk, template matching
src/retrieval/            # Query planning, Milvus search, context builder
src/rag/                  # Sinh câu trả lời RAG
src/anomaly/              # Baseline, scoring, online state, enrichment
src/rca/                  # RCA evidence ranking
infra/scripts/            # CLI xử lý ingestion, chunking, storage, anomaly, benchmark
infra/scripts/demo/       # Kịch bản và công cụ gửi log demo RCA
frontend/                 # React dashboard
data/                     # Raw logs, benchmark data, chunks, templates, retrieval artifacts
evaluation/               # Dataset, runner và metrics đánh giá retrieval/anomaly/RCA
tests/                    # Unit/integration tests
docker-compose.yml        # Compose stack cho app, API, Kafka, OpenSearch, Milvus, CLIProxyAPI
```

## Dữ Liệu Sử Dụng

Project dùng ba bộ log mẫu từ LogHub:

- Apache
- OpenStack
- HDFS

Các file log thô được đặt tại:

```text
data/raw/apache/Apache_2k.log
data/raw/openstack/OpenStack_2k.log
data/raw/hdfs/HDFS_2k.log
```

## Chạy Hệ Thống Bằng Docker

Chạy toàn bộ hệ thống:

```powershell
docker compose up -d --build
```

Dashboard:

```text
http://localhost:8501
```

API backend trong Docker Compose được frontend gọi nội bộ qua nginx tại đường dẫn `/api/*`. Nếu muốn truy cập API trực tiếp từ host, cần chạy backend local hoặc publish thêm port cho service `api`.

```text
http://localhost:8501/api/...
```

Một số service chính trong Docker Compose:

- `app`: React dashboard được build và phục vụ qua nginx.
- `api`: Starlette API cho chat, ingest và recent logs.
- `semantic-worker`: đọc log từ Kafka, xử lý và ghi vào Milvus/OpenSearch.
- `kafka`: message broker cho luồng log mới phát sinh.
- `opensearch`: lưu trữ log gốc.
- `milvus`: vector database cho semantic search.
- `cliproxyapi`: lớp trung gian gọi LLM cho RAG.

## API Chính

Kiểm tra health:

```text
GET /healthz
```

Endpoint này thuộc service `api`. Khi chạy backend local trên port mặc định, URL đầy đủ là `http://localhost:8000/healthz`; nginx của dashboard chỉ proxy các endpoint `/api/*`.

Hỏi đáp log:

```text
POST /api/chat
```

Tiếp nhận log mới:

```text
POST /api/ingest/logs
```

Payload tối thiểu:

```json
{
  "dataset": "apache",
  "source_id": "demo-stream",
  "raw_log": "[Sun Dec 04 04:47:44 2005] [notice] workerEnv.init() ok"
}
```

API chỉ nhận log thô và metadata tối thiểu. Các bước xử lý sâu như template, entity, anomaly và embedding được thực hiện ở `semantic-worker`.

Lấy danh sách log gần đây:

```text
GET /api/logs/recent?limit=200
```

## Pipeline Xử Lý Dữ Liệu Mẫu

Kiểm tra dữ liệu thô:

```powershell
python infra/scripts/ingestion/check_raw_data.py
```

Build corpus từ raw logs:

```powershell
python infra/scripts/ingestion/build_log_corpus.py --dataset all
```

Build chunks và templates:

```powershell
python infra/scripts/chunking/build_chunks.py --dataset all
```

Build template registry:

```powershell
python infra/scripts/storage/build_template_registry.py --dataset all
```

Khởi tạo Milvus và insert log vectors:

```powershell
python infra/scripts/storage/init_milvus.py --reset
python infra/scripts/storage/insert_chunks.py --dataset all
```

Build dữ liệu anomaly cho dashboard:

```powershell
python infra/scripts/anomaly/build_dashboard_anomaly_data.py
```

## Luồng Log Mới Phát Sinh

Hệ thống hỗ trợ tiếp nhận log mới qua API:

```text
POST /api/ingest/logs
```

API ingest chỉ nhận log thô và một số metadata tối thiểu, ví dụ `dataset`, `source_id` và `raw_log`. API không thực hiện template extraction, entity extraction hay embedding.

Luồng xử lý chính:

```text
Raw log payload
      -> Ingest API
      -> validate + normalize basic fields
      -> OpenSearch pending status
      -> Kafka topic logs.raw
      -> semantic-worker đọc theo batch
      -> parse + normalize log record
      -> template + entity extraction
      -> optional anomaly enrichment
      -> tạo Milvus rows
      -> batch embedding
      -> upsert theo batch vào Milvus
      -> update OpenSearch index status
```

Trong luồng này, `semantic-worker` là nơi xử lý semantic chính. Worker đọc log từ Kafka theo batch, tạo chunk bằng `build_line_chunk`, trích xuất template/entity, gắn anomaly payload nếu được bật, sau đó gom các log thành batch để tạo embedding và upsert vào collection `log_line` trong Milvus.

Các template mới chưa có trong catalog được worker ghi vào `data/templates/pending_templates.jsonl`. Docker Compose dùng volume `template-data` chung để API có thể đọc các candidate này trong quá trình retrieval.

Các biến môi trường liên quan:

```text
KAFKA_BOOTSTRAP_SERVERS
KAFKA_LOGS_RAW_TOPIC
KAFKA_LOGS_FAILED_TOPIC
KAFKA_CONSUMER_GROUP
INGESTION_BATCH_SIZE
INGESTION_FLUSH_INTERVAL_SECONDS
MILVUS_URI
EMBEDDING_MODEL
EMBEDDING_BATCH_SIZE
ANOMALY_ENABLED
ANOMALY_BASELINE_PATH
```

## Chạy Kịch Bản Demo RCA

Sau khi Docker Compose đã healthy, gửi bộ log demo qua nginx của dashboard:

```powershell
python infra/scripts/demo/send_rca_logs.py --base-url http://localhost:8501 --scenario basic
```

Kịch bản có nhiều evidence hơn:

```powershell
python infra/scripts/demo/send_rca_logs.py --base-url http://localhost:8501 --scenario high
```

Chi tiết log, anomaly ground truth, RCA ground truth và câu hỏi kiểm thử nằm trong `docs/semantic_log_monitoring_demo_scenario.md`. Các scenario dùng `log_id` cố định; chạy lại sẽ cập nhật/upsert cùng bản ghi, không tạo một phiên demo độc lập với ID mới.

## Evaluation

Sinh lại bộ dữ liệu đánh giá có ground truth theo seed cố định:

```powershell
python -m evaluation.scripts.generate_dataset --config evaluation/config.example.yaml
python -m evaluation.scripts.validate_groundtruth --dataset-dir evaluation/datasets
```

Chạy retrieval evaluation cục bộ và tính metrics:

```powershell
python -m evaluation.scripts.run_retrieval_evaluation --experiment baseline_log_only_v1 --top-k 24
python -m evaluation.scripts.calculate_retrieval_metrics --results evaluation/results/retrieval_baseline_log_only_v1.jsonl
```

Quy trình đầy đủ, bao gồm loader và live retrieval runner, được mô tả trong `evaluation/README.md`.

## RAG Và Chat

Dashboard gửi câu hỏi đến `/api/chat`. Backend thực hiện các bước:

1. Chuẩn hóa câu hỏi và bộ lọc dataset/service/level.
2. Lập kế hoạch truy vấn.
3. Truy xuất log liên quan từ Milvus và template registry.
4. Xây dựng context.
5. Gọi CLIProxyAPI/LLM để sinh câu trả lời.
6. Trả kết quả về dashboard.

Nếu RAG hoặc dịch vụ phụ trợ chưa sẵn sàng, API có cơ chế fallback để trả lời dựa trên log local thay vì làm lỗi request.

## Anomaly Detection Và RCA

Anomaly scoring sử dụng các tín hiệu chính:

- Độ hiếm của template.
- Độ bất thường trong quan hệ chuyển tiếp giữa các template.
- Sự thay đổi phân bố template trong một cửa sổ thời gian.

RCA candidates được xếp hạng dựa trên:

- Mức độ bất thường của log ứng viên.
- Quan hệ thời gian với incident log.
- Mức độ trùng service/component.
- Mức độ liên quan template.
- Entity match như request ID, trace ID, block ID, host hoặc IP.

Kết quả RCA trong project được xem là bằng chứng hỗ trợ phân tích, không phải kết luận chắc chắn về nguyên nhân gốc rễ.

## Kiểm Thử

Chạy test Python:

```powershell
python -m pytest
```

Chạy test frontend:

```powershell
cd frontend
npm test -- --run
```

Build frontend:

```powershell
npm run build --prefix frontend
```

Build Docker images:

```powershell
docker compose build
```

## Ghi Chú

- Đây là project thử nghiệm/đồ án, tập trung vào semantic log monitoring trên dữ liệu mẫu và luồng log mô phỏng.
- Hệ thống chưa hướng tới đầy đủ các yêu cầu production như phân quyền người dùng, cảnh báo đa kênh, metric/trace correlation hoặc graph-based RCA.
- RCA candidates chỉ là các log liên quan có giá trị tham khảo trong quá trình phân tích sự cố.
