# Qrels V2 Generation Report: apache

## Summary

- Positive labels v1 vs v2: 520 vs 440
- Hard negative labels v1 vs v2: 220 vs 300
- Uncertain labels v1 vs v2: 50 vs 40
- Queries with no positive: 8
- Queries needs_review: 14
- Avg positives/query v2: 14.67

## Top Positive Count Reductions

| query_id | v1_positive_count | v2_positive_count | delta |
| --- | --- | --- | --- |
| apache_q003 | 20 | 0 | -20 |
| apache_q015 | 20 | 0 | -20 |
| apache_q019 | 20 | 0 | -20 |
| apache_q030 | 20 | 0 | -20 |
| apache_q001 | 20 | 20 | 0 |
| apache_q002 | 20 | 20 | 0 |
| apache_q004 | 20 | 20 | 0 |
| apache_q005 | 20 | 20 | 0 |
| apache_q006 | 20 | 20 | 0 |
| apache_q007 | 20 | 20 | 0 |
| apache_q008 | 20 | 20 | 0 |
| apache_q009 | 20 | 20 | 0 |
| apache_q010 | 20 | 20 | 0 |
| apache_q011 | 0 | 0 | 0 |
| apache_q012 | 0 | 0 | 0 |


## Queries With No Positive

| query_id | category | query | review_reasons |
| --- | --- | --- | --- |
| apache_q003 | unknown | Apache có dấu hiệu khởi tạo hoặc worker bất thường không? | category unknown, no positive above v2 threshold, has uncertain candidates, multi-clause query |
| apache_q011 | unknown | Kiểm tra các thông báo NOTICE về quá trình khởi tạo worker. | category unknown, no positive above v2 threshold |
| apache_q012 | unknown | Có bản ghi scoreboard hoặc child process nào đáng chú ý không? | category unknown, no positive above v2 threshold, multi-clause query |
| apache_q015 | unknown | Tìm các dấu hiệu web tier bị suy giảm nhưng không phải lỗi quyền truy cập. | category unknown, no positive above v2 threshold, has uncertain candidates |
| apache_q018 | unknown | Show Apache startup or worker initialization notices. | category unknown, no positive above v2 threshold, multi-clause query |
| apache_q019 | unknown | Look for web server health signals around child workers. | category unknown, no positive above v2 threshold, has uncertain candidates |
| apache_q026 | unknown | Có tín hiệu NOTICE nào giúp phân biệt khởi động bình thường với worker bất thường không? | category unknown, hard query, no positive above v2 threshold |
| apache_q030 | unknown | Có bất thường tổng quan nào trong vòng đời child worker không? | category unknown, no positive above v2 threshold, has uncertain candidates |


## Examples Fixed Or Downgraded

| query_id | label | reason | message |
| --- | --- | --- | --- |
| apache_q003 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q003 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q003 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q003 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q003 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q003 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q003 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 7 |
| apache_q003 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 7 |
| apache_q003 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 7 |
| apache_q003 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q015 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q015 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q015 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q015 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q015 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q015 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
| apache_q015 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 7 |
| apache_q015 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 7 |
| apache_q015 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 7 |
| apache_q015 | uncertain | uncertain: weak pattern only | mod_jk child workerEnv in error state 6 |
