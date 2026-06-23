# Query Bank Validation: apache

## Summary

- Total queries: 30
- Query levels: easy=6, medium=18, hard=6
- Languages: vi=21, en=9
- Categories: service_unavailable=14, permission=8, unknown=8
- Queries with candidate logs: 26
- Queries without candidate logs: 4
- Queries with filters: 11
- Filters with no matching logs: 0
- Queries needing review: 22
- Broad queries: 18

## Filter Mismatches

| query_id | query | category | filters | suggestion |
| --- | --- | --- | --- | --- |


## Queries Needing Review

| query_id | level | language | category | candidates | matched_patterns | reasons | query | suggestion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| apache_q001 | easy | vi | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is large | Có worker nào của Apache rơi vào trạng thái lỗi không? | Make the query more specific or add a component/level filter. |
| apache_q003 | easy | vi | unknown | 595 | level=ERROR=595, \berror\b=595 | unknown category uses ERROR/WARN-only fallback, candidate set is large | Apache có dấu hiệu khởi tạo hoặc worker bất thường không? | Make the query more specific or add a component/level filter. |
| apache_q004 | easy | vi | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is large | Có lỗi nào khiến web service không phục vụ ổn định không? | Make the query more specific or add a component/level filter. |
| apache_q005 | easy | en | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is large | Find Apache worker errors that may affect availability. | Make the query more specific or add a component/level filter. |
| apache_q007 | medium | vi | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is broad | Tìm các lỗi ERROR liên quan đến workerEnv hoặc mod_jk. | Make the query more specific or add a component/level filter. |
| apache_q008 | medium | vi | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is broad | Có worker child nào bị đặt vào trạng thái không khỏe không? | Make the query more specific or add a component/level filter. |
| apache_q011 | medium | vi | unknown | 0 |  | unknown category uses ERROR/WARN-only fallback, no candidate logs found | Kiểm tra các thông báo NOTICE về quá trình khởi tạo worker. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| apache_q012 | medium | vi | unknown | 0 |  | unknown category uses ERROR/WARN-only fallback, no candidate logs found | Có bản ghi scoreboard hoặc child process nào đáng chú ý không? | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| apache_q013 | medium | vi | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is large | Tìm dấu hiệu mod_jk connector đang ở trạng thái lỗi. | Make the query more specific or add a component/level filter. |
| apache_q014 | medium | vi | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is broad | Có lỗi Apache nào lặp lại quanh worker process không? | Make the query more specific or add a component/level filter. |
| apache_q015 | medium | vi | unknown | 595 | level=ERROR=595, \berror\b=595 | unknown category uses ERROR/WARN-only fallback, candidate set is large | Tìm các dấu hiệu web tier bị suy giảm nhưng không phải lỗi quyền truy cập. | Make the query more specific or add a component/level filter. |
| apache_q016 | medium | en | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is broad | Find repeated worker error-state messages. | Make the query more specific or add a component/level filter. |
| apache_q018 | medium | en | unknown | 0 |  | unknown category uses ERROR/WARN-only fallback, no candidate logs found | Show Apache startup or worker initialization notices. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| apache_q019 | medium | en | unknown | 595 | level=ERROR=595, \berror\b=595 | unknown category uses ERROR/WARN-only fallback, candidate set is large | Look for web server health signals around child workers. | Make the query more specific or add a component/level filter. |
| apache_q020 | medium | en | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is large | Which Apache errors suggest requests may not be served reliably? | Make the query more specific or add a component/level filter. |
| apache_q021 | medium | vi | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is broad | Có chuỗi ERROR nào cho thấy worker Apache bị kẹt trong trạng thái lỗi không? | Make the query more specific or add a component/level filter. |
| apache_q023 | hard | vi | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is large | Vì sao Apache có thể vẫn chạy nhưng worker lại không xử lý request ổn định? | Make the query more specific or add a component/level filter. |
| apache_q024 | hard | vi | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is large | Có nhóm log nào cho thấy lỗi worker lặp lại theo thời gian không? | Make the query more specific or add a component/level filter. |
| apache_q026 | hard | vi | unknown | 0 |  | unknown category uses ERROR/WARN-only fallback, no candidate logs found | Có tín hiệu NOTICE nào giúp phân biệt khởi động bình thường với worker bất thường không? | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| apache_q027 | hard | en | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is large | Which logs suggest mod_jk worker health is degrading over time? | Make the query more specific or add a component/level filter. |
| apache_q029 | medium | vi | service_unavailable | 551 | mod_jk=551, error state=539 | candidate set is large | Có lỗi nào không nói service down trực tiếp nhưng cho thấy Apache phục vụ không ổn định không? | Make the query more specific or add a component/level filter. |
| apache_q030 | medium | vi | unknown | 595 | level=ERROR=595, \berror\b=595 | unknown category uses ERROR/WARN-only fallback, candidate set is large | Có bất thường tổng quan nào trong vòng đời child worker không? | Make the query more specific or add a component/level filter. |


## Suggestions To Revise Or Drop

| query_id | candidate_count | matched_patterns | query | suggestion |
| --- | --- | --- | --- | --- |
| apache_q001 | 551 | mod_jk=551, error state=539 | Có worker nào của Apache rơi vào trạng thái lỗi không? | Make the query more specific or add a component/level filter. |
| apache_q003 | 595 | level=ERROR=595, \berror\b=595 | Apache có dấu hiệu khởi tạo hoặc worker bất thường không? | Make the query more specific or add a component/level filter. |
| apache_q004 | 551 | mod_jk=551, error state=539 | Có lỗi nào khiến web service không phục vụ ổn định không? | Make the query more specific or add a component/level filter. |
| apache_q005 | 551 | mod_jk=551, error state=539 | Find Apache worker errors that may affect availability. | Make the query more specific or add a component/level filter. |
| apache_q007 | 551 | mod_jk=551, error state=539 | Tìm các lỗi ERROR liên quan đến workerEnv hoặc mod_jk. | Make the query more specific or add a component/level filter. |
| apache_q008 | 551 | mod_jk=551, error state=539 | Có worker child nào bị đặt vào trạng thái không khỏe không? | Make the query more specific or add a component/level filter. |
| apache_q011 | 0 |  | Kiểm tra các thông báo NOTICE về quá trình khởi tạo worker. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| apache_q012 | 0 |  | Có bản ghi scoreboard hoặc child process nào đáng chú ý không? | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| apache_q013 | 551 | mod_jk=551, error state=539 | Tìm dấu hiệu mod_jk connector đang ở trạng thái lỗi. | Make the query more specific or add a component/level filter. |
| apache_q014 | 551 | mod_jk=551, error state=539 | Có lỗi Apache nào lặp lại quanh worker process không? | Make the query more specific or add a component/level filter. |
| apache_q015 | 595 | level=ERROR=595, \berror\b=595 | Tìm các dấu hiệu web tier bị suy giảm nhưng không phải lỗi quyền truy cập. | Make the query more specific or add a component/level filter. |
| apache_q016 | 551 | mod_jk=551, error state=539 | Find repeated worker error-state messages. | Make the query more specific or add a component/level filter. |
| apache_q018 | 0 |  | Show Apache startup or worker initialization notices. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| apache_q019 | 595 | level=ERROR=595, \berror\b=595 | Look for web server health signals around child workers. | Make the query more specific or add a component/level filter. |
| apache_q020 | 551 | mod_jk=551, error state=539 | Which Apache errors suggest requests may not be served reliably? | Make the query more specific or add a component/level filter. |
| apache_q021 | 551 | mod_jk=551, error state=539 | Có chuỗi ERROR nào cho thấy worker Apache bị kẹt trong trạng thái lỗi không? | Make the query more specific or add a component/level filter. |
| apache_q023 | 551 | mod_jk=551, error state=539 | Vì sao Apache có thể vẫn chạy nhưng worker lại không xử lý request ổn định? | Make the query more specific or add a component/level filter. |
| apache_q024 | 551 | mod_jk=551, error state=539 | Có nhóm log nào cho thấy lỗi worker lặp lại theo thời gian không? | Make the query more specific or add a component/level filter. |
| apache_q026 | 0 |  | Có tín hiệu NOTICE nào giúp phân biệt khởi động bình thường với worker bất thường không? | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| apache_q027 | 551 | mod_jk=551, error state=539 | Which logs suggest mod_jk worker health is degrading over time? | Make the query more specific or add a component/level filter. |
| apache_q029 | 551 | mod_jk=551, error state=539 | Có lỗi nào không nói service down trực tiếp nhưng cho thấy Apache phục vụ không ổn định không? | Make the query more specific or add a component/level filter. |
| apache_q030 | 595 | level=ERROR=595, \berror\b=595 | Có bất thường tổng quan nào trong vòng đời child worker không? | Make the query more specific or add a component/level filter. |


## Per-Query Candidate Counts

| query_id | level | language | category | filters | filtered_logs | candidate_logs | weak_candidates | matched_patterns | supported |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| apache_q001 | easy | vi | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q002 | easy | vi | permission | {'component': None, 'level': None, 'time_range': None} | 2000 | 32 | 0 | forbidden=32, directory index forbidden=32 | yes |
| apache_q003 | easy | vi | unknown | {'component': None, 'level': None, 'time_range': None} | 2000 | 595 | 0 | level=ERROR=595, \berror\b=595 | yes |
| apache_q004 | easy | vi | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q005 | easy | en | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q006 | easy | en | permission | {'component': None, 'level': None, 'time_range': None} | 2000 | 32 | 0 | forbidden=32, directory index forbidden=32 | yes |
| apache_q007 | medium | vi | service_unavailable | {'component': None, 'level': 'ERROR', 'time_range': None} | 595 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q008 | medium | vi | service_unavailable | {'component': None, 'level': 'ERROR', 'time_range': None} | 595 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q009 | medium | vi | permission | {'component': None, 'level': 'ERROR', 'time_range': None} | 595 | 32 | 0 | forbidden=32, directory index forbidden=32 | yes |
| apache_q010 | medium | vi | permission | {'component': None, 'level': 'ERROR', 'time_range': None} | 595 | 32 | 0 | forbidden=32, directory index forbidden=32 | yes |
| apache_q011 | medium | vi | unknown | {'component': None, 'level': 'NOTICE', 'time_range': None} | 1405 | 0 | 0 |  | no |
| apache_q012 | medium | vi | unknown | {'component': None, 'level': 'NOTICE', 'time_range': None} | 1405 | 0 | 0 |  | no |
| apache_q013 | medium | vi | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q014 | medium | vi | service_unavailable | {'component': None, 'level': 'ERROR', 'time_range': None} | 595 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q015 | medium | vi | unknown | {'component': None, 'level': None, 'time_range': None} | 2000 | 595 | 0 | level=ERROR=595, \berror\b=595 | yes |
| apache_q016 | medium | en | service_unavailable | {'component': None, 'level': 'ERROR', 'time_range': None} | 595 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q017 | medium | en | permission | {'component': None, 'level': None, 'time_range': None} | 2000 | 32 | 0 | forbidden=32, directory index forbidden=32 | yes |
| apache_q018 | medium | en | unknown | {'component': None, 'level': 'NOTICE', 'time_range': None} | 1405 | 0 | 0 |  | no |
| apache_q019 | medium | en | unknown | {'component': None, 'level': None, 'time_range': None} | 2000 | 595 | 0 | level=ERROR=595, \berror\b=595 | yes |
| apache_q020 | medium | en | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q021 | medium | vi | service_unavailable | {'component': None, 'level': 'ERROR', 'time_range': None} | 595 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q022 | medium | vi | permission | {'component': None, 'level': None, 'time_range': None} | 2000 | 32 | 0 | forbidden=32, directory index forbidden=32 | yes |
| apache_q023 | hard | vi | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q024 | hard | vi | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q025 | hard | vi | permission | {'component': None, 'level': None, 'time_range': None} | 2000 | 32 | 0 | forbidden=32, directory index forbidden=32 | yes |
| apache_q026 | hard | vi | unknown | {'component': None, 'level': 'NOTICE', 'time_range': None} | 1405 | 0 | 0 |  | no |
| apache_q027 | hard | en | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q028 | hard | en | permission | {'component': None, 'level': None, 'time_range': None} | 2000 | 32 | 0 | forbidden=32, directory index forbidden=32 | yes |
| apache_q029 | medium | vi | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 551 | 0 | mod_jk=551, error state=539 | yes |
| apache_q030 | medium | vi | unknown | {'component': None, 'level': None, 'time_range': None} | 2000 | 595 | 0 | level=ERROR=595, \berror\b=595 | yes |
