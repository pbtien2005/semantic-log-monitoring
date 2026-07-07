# Chunk Audit: apache

## Counts

| metric | value |
| --- | --- |
| logs | 2000 |
| line_chunks | 2000 |
| catalog_templates | 6 |
| line_chunks_match_logs | PASS |
| unique_line_chunk_ids | PASS (2000) |
| unique_catalog_template_ids | PASS (6) |
| singleton_templates | 0 (0.0%) |

## Quality Metrics

| metric | value |
| --- | --- |
| total_logs | 2000 |
| total_templates | 6 |
| matched_template_count | 2000 |
| unmatched_template_count | 0 |
| unmatched_template_ratio | 0.0% |
| templates_never_seen | 0 |
| ambiguous_match_count | 0 |
| entity_extraction_coverage | 100.0% |
| unique_template_ratio | 0.3% |
| singleton_template_ratio | 0.0% |
| top_20_template_coverage | 0.0% |
| unknown_signal_ratio | 29.8% |
| weak_signal_ratio | 29.8% |
| avg_embed_text_length | 298.4 |
| templates_with_real_id_leak | 0 |
| templates_over_normalized | 0 |

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

## Match Count By Template

| template_id | match_count |
| --- | --- |
| apache::E1 | 836 |
| apache::E2 | 569 |
| apache::E3 | 539 |
| apache::E4 | 32 |
| apache::E5 | 12 |
| apache::E6 | 12 |

## Top Unmatched Normalized Templates

| count | normalized_template |
| --- | --- |

## Catalog Templates Never Seen

| template_id |
| --- |

## Top Catalog Templates

| priority | template |
| --- | --- |
| 100 | [client <*>] Directory index forbidden by rule: <*> |
| 100 | jk2_init() Can't find child <*> in scoreboard |
| 100 | jk2_init() Found child <*> in scoreboard slot <*> |
| 100 | mod_jk child init <*> <*> |
| 100 | mod_jk child workerEnv in error state <*> |
| 100 | workerEnv.init() ok <*> |

## Suspicious Template Samples

_None._

## Line Chunk Samples

| chunk_id | embed_text |
| --- | --- |
| line::apache:16df03d8e0807b9110d5 | dataset: apache<br>level: NOTICE<br>event_type: worker_env_initialized<br>event_family: apache_backend<br>template: workerEnv.init() ok <*><br>intent: worker_env_initialized apache_worker_initialization apache_backend<br>signals: config_loaded initialization_success level_notice worker_environment<br>message: workerEnv.init() ok <path> |
| line::apache:1edb10524df78ed1511b | dataset: apache<br>level: ERROR<br>event_type: backend_worker_error<br>event_family: apache_backend<br>template: mod_jk child workerEnv in error state <*><br>intent: backend_worker_error worker_env_error_state apache_backend<br>signals: backend_down backend_worker_error level_error service_unavailable worker_environment worker_error<br>message: mod_jk child workerEnv in error state 6 |
| line::apache:d09de38e2e37e8bbe94a | dataset: apache<br>level: NOTICE<br>template: jk2_init() Found child <*> in scoreboard slot <*><br>intent: scoreboard_child_found apache_worker_initialization apache_mod_jk<br>signals: level_notice<br>message: jk2_init() Found child 6725 in scoreboard slot 10 |
| line::apache:67f51a298be2cccc6f36 | dataset: apache<br>level: NOTICE<br>template: jk2_init() Found child <*> in scoreboard slot <*><br>intent: scoreboard_child_found apache_worker_initialization apache_mod_jk<br>signals: level_notice<br>message: jk2_init() Found child 6726 in scoreboard slot 8 |
| line::apache:f42787d58ffca55c949f | dataset: apache<br>level: NOTICE<br>template: jk2_init() Found child <*> in scoreboard slot <*><br>intent: scoreboard_child_found apache_worker_initialization apache_mod_jk<br>signals: level_notice<br>message: jk2_init() Found child 6728 in scoreboard slot 6 |
| line::apache:568f50ef68b22c504512 | dataset: apache<br>level: NOTICE<br>event_type: worker_env_initialized<br>event_family: apache_backend<br>template: workerEnv.init() ok <*><br>intent: worker_env_initialized apache_worker_initialization apache_backend<br>signals: config_loaded initialization_success level_notice worker_environment<br>message: workerEnv.init() ok <path> |
| line::apache:1b011b7f7cfd98e2b182 | dataset: apache<br>level: NOTICE<br>event_type: worker_env_initialized<br>event_family: apache_backend<br>template: workerEnv.init() ok <*><br>intent: worker_env_initialized apache_worker_initialization apache_backend<br>signals: config_loaded initialization_success level_notice worker_environment<br>message: workerEnv.init() ok <path> |
| line::apache:940a8aa98ae46a886ca3 | dataset: apache<br>level: NOTICE<br>event_type: worker_env_initialized<br>event_family: apache_backend<br>template: workerEnv.init() ok <*><br>intent: worker_env_initialized apache_worker_initialization apache_backend<br>signals: config_loaded initialization_success level_notice worker_environment<br>message: workerEnv.init() ok <path> |
| line::apache:53f2517fbacf0e705a9c | dataset: apache<br>level: ERROR<br>event_type: backend_worker_error<br>event_family: apache_backend<br>template: mod_jk child workerEnv in error state <*><br>intent: backend_worker_error worker_env_error_state apache_backend<br>signals: backend_down backend_worker_error level_error service_unavailable worker_environment worker_error<br>message: mod_jk child workerEnv in error state 6 |
| line::apache:8e4b76c71ceb0d4486aa | dataset: apache<br>level: ERROR<br>event_type: backend_worker_error<br>event_family: apache_backend<br>template: mod_jk child workerEnv in error state <*><br>intent: backend_worker_error worker_env_error_state apache_backend<br>signals: backend_down backend_worker_error level_error service_unavailable worker_environment worker_error<br>message: mod_jk child workerEnv in error state 6 |
