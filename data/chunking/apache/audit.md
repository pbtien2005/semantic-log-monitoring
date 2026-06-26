# Chunk Audit: apache

## Counts

| metric | value |
| --- | --- |
| logs | 2000 |
| line_chunks | 2000 |
| template_chunks | 6 |
| line_chunks_match_logs | PASS |
| unique_line_chunk_ids | PASS (2000) |
| unique_template_chunk_ids | PASS (6) |
| singleton_templates | 0 (0.0%) |

## Filter Field Null Rates

| field | present | missing | missing_rate |
| --- | --- | --- | --- |
| component | 0 | 2000 | 100.0% |
| level | 2000 | 0 | 0.0% |
| timestamp_ms | 2000 | 0 | 0.0% |
| request_id | 0 | 2000 | 100.0% |
| instance_id | 0 | 2000 | 100.0% |
| block_id | 0 | 2000 | 100.0% |
| ip | 32 | 1968 | 98.4% |
| http_status | 0 | 2000 | 100.0% |
| duration_ms | 0 | 2000 | 100.0% |

## Raw Pattern Leakage In Templates

| pattern | template_count |
| --- | --- |
| request_id | 0 |
| uuid | 0 |
| hex_id | 0 |
| block_id | 0 |
| ip | 0 |

## Top Templates

| count | component | level | template |
| --- | --- | --- | --- |
| 836 | None | NOTICE | jk2_init() Found child <num> in scoreboard slot <num> |
| 569 | None | NOTICE | workerEnv.init() ok <path> |
| 539 | None | ERROR | mod_jk child workerEnv in error state <num> |
| 32 | None | ERROR | [client <ip>] Directory index forbidden by rule: <path>/ |
| 12 | None | ERROR | jk2_init() Can't find child <num> in scoreboard |
| 12 | None | ERROR | mod_jk child init <num> <num> |

## Suspicious Template Samples

| reason | chunk_id | template |
| --- | --- | --- |
| too_few_semantic_tokens | template::apache::7e47c8771ae979d4 | workerEnv.init() ok <path> |

## Line Chunk Samples

| chunk_id | embed_text |
| --- | --- |
| line::apache:16df03d8e0807b9110d5 | dataset: apache<br>component: none<br>level: NOTICE<br>template: workerEnv.init() ok <path><br>signals: level_notice |
| line::apache:1edb10524df78ed1511b | dataset: apache<br>component: none<br>level: ERROR<br>template: mod_jk child workerEnv in error state <num><br>signals: level_error service_unavailable unknown |
| line::apache:d09de38e2e37e8bbe94a | dataset: apache<br>component: none<br>level: NOTICE<br>template: jk2_init() Found child <num> in scoreboard slot <num><br>signals: level_notice |
| line::apache:67f51a298be2cccc6f36 | dataset: apache<br>component: none<br>level: NOTICE<br>template: jk2_init() Found child <num> in scoreboard slot <num><br>signals: level_notice |
| line::apache:f42787d58ffca55c949f | dataset: apache<br>component: none<br>level: NOTICE<br>template: jk2_init() Found child <num> in scoreboard slot <num><br>signals: level_notice |
| line::apache:568f50ef68b22c504512 | dataset: apache<br>component: none<br>level: NOTICE<br>template: workerEnv.init() ok <path><br>signals: level_notice |
| line::apache:1b011b7f7cfd98e2b182 | dataset: apache<br>component: none<br>level: NOTICE<br>template: workerEnv.init() ok <path><br>signals: level_notice |
| line::apache:940a8aa98ae46a886ca3 | dataset: apache<br>component: none<br>level: NOTICE<br>template: workerEnv.init() ok <path><br>signals: level_notice |
| line::apache:53f2517fbacf0e705a9c | dataset: apache<br>component: none<br>level: ERROR<br>template: mod_jk child workerEnv in error state <num><br>signals: level_error service_unavailable unknown |
| line::apache:8e4b76c71ceb0d4486aa | dataset: apache<br>component: none<br>level: ERROR<br>template: mod_jk child workerEnv in error state <num><br>signals: level_error service_unavailable unknown |
