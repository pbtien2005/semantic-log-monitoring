# Qrels Generation Report: apache

## Summary

- Total queries: 30
- Queries with positive logs: 26
- Queries with empty positive_log_ids: 4
- Queries needing review: 14
- Avg positives/query: 17.33
- Avg hard negatives/query: 8.67
- Query levels: easy=6, medium=18, hard=6
- Categories: service_unavailable=14, permission=8, unknown=8

## Unsupported Queries

| query_id | category | query | reason |
| --- | --- | --- | --- |
| apache_q011 | unknown | Kiểm tra các thông báo NOTICE về quá trình khởi tạo worker. | no candidate log matched category/filter rules |
| apache_q012 | unknown | Có bản ghi scoreboard hoặc child process nào đáng chú ý không? | no candidate log matched category/filter rules |
| apache_q018 | unknown | Show Apache startup or worker initialization notices. | no candidate log matched category/filter rules |
| apache_q026 | unknown | Có tín hiệu NOTICE nào giúp phân biệt khởi động bình thường với worker bất thường không? | no candidate log matched category/filter rules |


## Queries Needing Most Review

| query_id | positive_count | negative_count | reasons | query |
| --- | --- | --- | --- | --- |
| apache_q003 | 20 | 0 | category unknown requires manual review, too few hard negative candidates, query contains multiple intents or clauses | Apache có dấu hiệu khởi tạo hoặc worker bất thường không? |
| apache_q012 | 0 | 10 | category unknown requires manual review, unsupported by category/filter rules, query contains multiple intents or clauses | Có bản ghi scoreboard hoặc child process nào đáng chú ý không? |
| apache_q018 | 0 | 10 | category unknown requires manual review, unsupported by category/filter rules, query contains multiple intents or clauses | Show Apache startup or worker initialization notices. |
| apache_q026 | 0 | 10 | category unknown requires manual review, hard query requires manual review, unsupported by category/filter rules | Có tín hiệu NOTICE nào giúp phân biệt khởi động bình thường với worker bất thường không? |
| apache_q011 | 0 | 10 | category unknown requires manual review, unsupported by category/filter rules | Kiểm tra các thông báo NOTICE về quá trình khởi tạo worker. |
| apache_q015 | 20 | 0 | category unknown requires manual review, too few hard negative candidates | Tìm các dấu hiệu web tier bị suy giảm nhưng không phải lỗi quyền truy cập. |
| apache_q019 | 20 | 0 | category unknown requires manual review, too few hard negative candidates | Look for web server health signals around child workers. |
| apache_q025 | 20 | 10 | hard query requires manual review, query contains multiple intents or clauses | Tìm bối cảnh trước sau các lỗi permission để xem có phải cấu hình web root sai không. |
| apache_q030 | 20 | 0 | category unknown requires manual review, too few hard negative candidates | Có bất thường tổng quan nào trong vòng đời child worker không? |
| apache_q007 | 20 | 10 | query contains multiple intents or clauses | Tìm các lỗi ERROR liên quan đến workerEnv hoặc mod_jk. |
| apache_q023 | 20 | 10 | hard query requires manual review | Vì sao Apache có thể vẫn chạy nhưng worker lại không xử lý request ổn định? |
| apache_q024 | 20 | 10 | hard query requires manual review | Có nhóm log nào cho thấy lỗi worker lặp lại theo thời gian không? |
| apache_q027 | 20 | 10 | hard query requires manual review | Which logs suggest mod_jk worker health is degrading over time? |
| apache_q028 | 20 | 10 | hard query requires manual review | Find evidence of repeated forbidden access that may indicate an Apache config issue. |
