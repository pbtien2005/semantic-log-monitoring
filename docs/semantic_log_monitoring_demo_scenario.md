# 1. Tổng Quan Kịch Bản Demo

Kịch bản demo này mô phỏng một control plane phân tán, kết hợp log phong cách OpenStack với hoạt động block kiểu HDFS. Phần lớn log là luồng bình thường: request tạo server hoàn tất, port được bind, volume được attach, và HDFS block được replicate. Ba anomaly đã được cài sẵn:

- `demo:0034`: lỗi `nova-api` 500 cuối luồng, nguyên nhân thật nằm ở latency của storage backend trước đó.
- `demo:0044`: lỗi port-binding của network, nguyên nhân là burst các sự kiện OVSDB connection reset.
- `demo:0050`: transition detach/attach hiếm trên cùng một instance và boot volume, do stale connector metadata.

Dataset được thiết kế để thể hiện giá trị của semantic retrieval và template-based retrieval so với keyword search thuần túy: root cause có thể là log `WARN`, có thể xuất hiện trước log `ERROR` cuối cùng, và có thể không có cùng request id với incident.

# 2. Bộ Dữ Liệu Log

Dataset JSONL:

`data/realtime_test/semantic_log_monitoring_demo_logs.jsonl`

Mỗi dòng có các trường `log_id`, `timestamp`, `dataset`, `source_id`, `service`, `level`, `request_id`, `instance_id`, `block_id`, `message`, và `raw_log`. Dataset gồm 50 log theo thứ tự thời gian, từ `demo:0001` đến `demo:0050`.

# 3. Nhãn Chuẩn Anomaly

File ground truth:

`data/realtime_test/semantic_log_monitoring_ground_truth.json`

Các anomaly đã được gán nhãn trước:

| log_id | anomaly_type | expected score | key signals |
| --- | --- | ---: | --- |
| `demo:0034` | `causal_downstream_failure` | 0.94 | `sequence_anomaly`, `entity_linkage` |
| `demo:0044` | `burst_network_binding_failure` | 0.91 | `burst_anomaly`, `sequence_anomaly`, `entity_linkage` |
| `demo:0050` | `rare_entity_transition` | 0.89 | `template_rarity`, `sequence_anomaly`, `entity_linkage` |

Vì sao các log này là anomaly:

- `demo:0034` không bất thường chỉ vì nó là `ERROR`; nó bất thường vì một luồng create-server bình thường bị lệch khỏi sequence sau khi cinder báo storage backend latency cao, sau đó retry tích tụ trước lỗi 500 cuối cùng mà người dùng nhìn thấy.
- `demo:0044` bất thường vì cùng một template retry của network xuất hiện dồn dập trên nhiều request chỉ trong vài giây, rồi một request kết thúc bằng 503.
- `demo:0050` bất thường vì một instance đang `ACTIVE` và boot volume của nó đi vào chuỗi detach/attach conflict hiếm trong lúc rebuild validation.

# 4. Nhãn Chuẩn RCA

| incident_log_id | root_cause_log_id | root cause summary | evidence |
| --- | --- | --- | --- |
| `demo:0034` | `demo:0028` | Storage backend `ceph-az1` bị chậm/quá tải với `vol-774`. | `demo:0027`, `demo:0028`, `demo:0029`, `demo:0030`, `demo:0031`, `demo:0032`, `demo:0033`, `demo:0034` |
| `demo:0044` | `demo:0039` | Host `net-17` mất kết nối OVSDB, gây retry port-binding và delayed convergence. | `demo:0039`, `demo:0040`, `demo:0041`, `demo:0042`, `demo:0043`, `demo:0044` |
| `demo:0050` | `demo:0046` | Stale connector mapping của `vol-551` trên `inst-9a77` gây xung đột detach/attach. | `demo:0045`, `demo:0046`, `demo:0047`, `demo:0048`, `demo:0049`, `demo:0050` |

RCA không nên chọn log `ERROR` cuối cùng làm root cause nếu log đó chỉ là hệ quả. Với `demo:0034`, tín hiệu nhân quả đầu tiên là `demo:0028`. Với `demo:0044`, root log quan trọng không có `request_id`, nên retrieval cần dùng ngữ cảnh service, thời gian, host và template. Với `demo:0050`, evidence chain được liên kết bằng `instance_id` cùng volume id nằm trong message.

# 5. Câu Hỏi Kiểm Thử

File JSON chứa 7 query sẵn sàng để test, bao gồm expected retrieved log ids và expected answers:

- tra cứu request/session cho `req-create-2002`
- câu hỏi ngôn ngữ tự nhiên dạng "vì sao request này lỗi?"
- query tường minh `RCA for log_id=demo:0044`
- liệt kê anomaly theo time window
- query semantic tiếng Việt về storage bị chậm
- query template/burst về lỗi network lặp lại
- query entity-linkage cho `inst-9a77` và `vol-551`

# 6. Luồng Demo Kỳ Vọng

1. Stream `demo:0001`-`demo:0027` như baseline traffic bình thường.
2. Stream `demo:0028`-`demo:0034`; dashboard nên đánh dấu `demo:0034` và retrieve evidence từ storage.
3. Stream `demo:0035`-`demo:0044`; dashboard nên đánh dấu network burst kết thúc ở `demo:0044`.
4. Stream `demo:0045`-`demo:0050`; dashboard nên đánh dấu transition hiếm trên cùng instance/cùng volume, kết thúc ở `demo:0050`.
5. Người dùng hỏi RCA/chat query và hệ thống phải trả lời kèm citation bằng `log_id`.
6. So sánh anomaly được detect, root cause ids, evidence chains và câu trả lời với file ground truth.

# 7. Tiêu Chí Đánh Giá

- Anomaly detector tìm được `demo:0034`, `demo:0044`, và `demo:0050`.
- RCA rank `demo:0028`, `demo:0039`, và `demo:0046` là root cause đúng cho từng incident.
- Retrieval trả về đúng evidence chain kỳ vọng, không chỉ lấy log `ERROR` cuối cùng.
- Câu trả lời có citation bằng `log_id`.
- Query ngôn ngữ tự nhiên retrieve được log liên quan về mặt ngữ nghĩa ngay cả khi từ khóa khác với raw log.
- Template retrieval gom được các pattern connection-reset/port-binding retry lặp lại.
- Hệ thống tránh kéo quá nhiều log bình thường không liên quan vào evidence context.
