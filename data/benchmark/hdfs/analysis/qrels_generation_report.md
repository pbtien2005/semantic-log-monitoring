# Qrels Generation Report: hdfs

## Summary

- Total queries: 30
- Queries with positive logs: 28
- Queries with empty positive_log_ids: 2
- Queries needing review: 25
- Avg positives/query: 18.67
- Avg hard negatives/query: 4.67
- Query levels: easy=6, medium=18, hard=6
- Categories: storage=16, service_unavailable=10, unknown=4

## Unsupported Queries

| query_id | category | query | reason |
| --- | --- | --- | --- |
| hdfs_q013 | unknown | Có quá trình verification block nào thành công không? | no candidate log matched category/filter rules |
| hdfs_q019 | unknown | Show block scanner verification records. | no candidate log matched category/filter rules |


## Queries Needing Most Review

| query_id | positive_count | negative_count | reasons | query |
| --- | --- | --- | --- | --- |
| hdfs_q002 | 20 | 0 | too few hard negative candidates, query contains multiple intents or clauses | Có block nào được ghi nhận hoặc cập nhật trong HDFS không? |
| hdfs_q008 | 20 | 0 | too few hard negative candidates, query contains multiple intents or clauses | Có block nào được DataNode nhận hoặc phục vụ không? |
| hdfs_q013 | 0 | 10 | category unknown requires manual review, unsupported by category/filter rules | Có quá trình verification block nào thành công không? |
| hdfs_q019 | 0 | 10 | category unknown requires manual review, unsupported by category/filter rules | Show block scanner verification records. |
| hdfs_q022 | 20 | 0 | too few hard negative candidates, query contains multiple intents or clauses | Tìm các log về block replication hoặc vị trí block được cập nhật. |
| hdfs_q024 | 20 | 0 | hard query requires manual review, too few hard negative candidates | Có chuỗi sự kiện nào từ nhận block đến responder kết thúc không? |
| hdfs_q025 | 20 | 0 | hard query requires manual review, too few hard negative candidates | Tìm bằng chứng blockMap thay đổi quanh các block có sự cố. |
| hdfs_q026 | 20 | 10 | category unknown requires manual review, hard query requires manual review | Có log nào cho thấy block vẫn được verify dù cluster có cảnh báo không? |
| hdfs_q028 | 20 | 0 | hard query requires manual review, too few hard negative candidates | Find evidence of repeated block movement across DataNodes. |
| hdfs_q003 | 20 | 0 | too few hard negative candidates | Có node nào liên quan đến truyền dữ liệu block không? |
| hdfs_q004 | 20 | 10 | category unknown requires manual review | Cluster HDFS có dấu hiệu bất thường không? |
| hdfs_q006 | 20 | 0 | too few hard negative candidates | Are there block metadata updates in NameNode logs? |
| hdfs_q007 | 20 | 10 | query contains multiple intents or clauses | Tìm exception khi DataXceiver gửi block cho client hoặc node khác. |
| hdfs_q009 | 20 | 0 | too few hard negative candidates | Kiểm tra các log PacketResponder kết thúc xử lý block. |
| hdfs_q010 | 20 | 0 | too few hard negative candidates | Tìm cập nhật blockMap từ FSNamesystem. |
| hdfs_q011 | 20 | 0 | too few hard negative candidates | Có block nào được allocate cho file tạm trong HDFS không? |
| hdfs_q014 | 20 | 0 | too few hard negative candidates | Kiểm tra FSDataset trong các thao tác lưu trữ block. |
| hdfs_q015 | 20 | 10 | query contains multiple intents or clauses | Có node hoặc địa chỉ nào xuất hiện khi block transfer gặp sự cố không? |
| hdfs_q017 | 20 | 0 | too few hard negative candidates | Find FSNamesystem records that update block locations. |
| hdfs_q018 | 20 | 0 | too few hard negative candidates | Look for PacketResponder block completion events. |
