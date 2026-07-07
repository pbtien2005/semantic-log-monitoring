# Chunk Audit: openstack

## Counts

| metric | value |
| --- | --- |
| logs | 2000 |
| line_chunks | 2000 |
| catalog_templates | 43 |
| line_chunks_match_logs | PASS |
| unique_line_chunk_ids | PASS (2000) |
| unique_catalog_template_ids | PASS (43) |
| singleton_templates | 0 (0.0%) |

## Quality Metrics

| metric | value |
| --- | --- |
| total_logs | 2000 |
| total_templates | 43 |
| matched_template_count | 2000 |
| unmatched_template_count | 0 |
| unmatched_template_ratio | 0.0% |
| templates_never_seen | 0 |
| ambiguous_match_count | 0 |
| entity_extraction_coverage | 100.0% |
| unique_template_ratio | 2.1% |
| singleton_template_ratio | 0.0% |
| top_20_template_coverage | 0.0% |
| unknown_signal_ratio | 1.6% |
| weak_signal_ratio | 7.6% |
| avg_embed_text_length | 385.5 |
| templates_with_real_id_leak | 0 |
| templates_over_normalized | 0 |

## Filter Field Null Rates

| field | present | missing | missing_rate |
| --- | --- | --- | --- |
| component | 2000 | 0 | 0.0% |
| level | 2000 | 0 | 0.0% |
| timestamp_ms | 2000 | 0 | 0.0% |
| request_id | 1845 | 155 | 7.8% |
| instance_id | 557 | 1443 | 72.2% |
| block_id | 0 | 2000 | 100.0% |
| ip | 1017 | 983 | 49.1% |
| http_status | 1017 | 983 | 49.1% |
| duration_ms | 1103 | 897 | 44.9% |

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
| openstack::E25 | 931 |
| openstack::E34 | 82 |
| openstack::E35 | 82 |
| openstack::E27 | 82 |
| openstack::E26 | 64 |
| openstack::E21 | 44 |
| openstack::E7 | 43 |
| openstack::E42 | 30 |
| openstack::E36 | 30 |
| openstack::E22 | 22 |

## Top Unmatched Normalized Templates

| count | normalized_template |
| --- | --- |

## Catalog Templates Never Seen

| template_id |
| --- |

## Top Catalog Templates

| priority | template |
| --- | --- |
| 100 | <*> "DELETE <*>" status: <*> len: <*> time: <*>.<*> |
| 100 | <*> "GET <*>" status: <*> len: <*> time: <*>.<*> |
| 100 | <*> "POST <*>" status: <*> len: <*> time: <*>.<*> |
| 100 | Active base files: <*> |
| 100 | Auditing locally available compute resources for node <*> |
| 100 | Base or swap file too young to remove: <*> |
| 100 | Compute_service record updated for <*> |
| 100 | Creating event network-vif-plugged:<*>-<*>-<*>-<*>-<*> for instance <*> |
| 100 | Final resource view: name=<*> phys_ram=<*> used_ram=<*> phys_disk=<*> used_disk=<*> total_vcpus=<*> used_vcpus=<*> pci_stats=[] |
| 100 | HTTP exception thrown: No instances found for any event |

## Suspicious Template Samples

_None._

## Line Chunk Samples

| chunk_id | embed_text |
| --- | --- |
| line::openstack:ce42502a78bda4f03311 | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: <*> "GET <*>" status: <*> len: <*> time: <*>.<*><br>intent: api_get_request http_api_access openstack_api<br>signals: has_ip has_request_id http_request osapi_compute server wsgi<br>message: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: 200 len: 1893 time: 0.2477829 |
| line::openstack:ee3c000d74147e791bdb | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: <*> "GET <*>" status: <*> len: <*> time: <*>.<*><br>intent: api_get_request http_api_access openstack_api<br>signals: has_ip has_request_id http_request osapi_compute server wsgi<br>message: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: 200 len: 1893 time: 0.2577181 |
| line::openstack:319b972344c6f3da3fbe | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: <*> "GET <*>" status: <*> len: <*> time: <*>.<*><br>intent: api_get_request http_api_access openstack_api<br>signals: has_ip has_request_id http_request osapi_compute server wsgi<br>message: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: 200 len: 1893 time: 0.2731631 |
| line::openstack:342db085463108443414 | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: <*> "GET <*>" status: <*> len: <*> time: <*>.<*><br>intent: api_get_request http_api_access openstack_api<br>signals: has_ip has_request_id http_request osapi_compute server wsgi<br>message: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: 200 len: 1893 time: 0.2580249 |
| line::openstack:e61fa138d9196f19888d | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: <*> "GET <*>" status: <*> len: <*> time: <*>.<*><br>intent: api_get_request http_api_access openstack_api<br>signals: has_ip has_request_id http_request osapi_compute server wsgi<br>message: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: 200 len: 1893 time: 0.2727931 |
| line::openstack:256b722736f5fcf9bb66 | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: <*> "GET <*>" status: <*> len: <*> time: <*>.<*><br>intent: api_get_request http_api_access openstack_api<br>signals: has_ip has_request_id http_request osapi_compute server wsgi<br>message: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: 200 len: 1893 time: 0.2642131 |
| line::openstack:2bab0edba84c892299aa | dataset: openstack<br>component: nova.compute.manager<br>level: INFO<br>template: [instance: <*>] VM Started (Lifecycle Event)<br>intent: vm_started vm_lifecycle_event openstack_instance_lifecycle<br>signals: compute has_instance_id has_request_id instance_state manager<br>message: [<req_id> - - - - -] [instance: <instance_id>] VM Started (Lifecycle Event) |
| line::openstack:01e6fcdda9a0f6bb6016 | dataset: openstack<br>component: nova.compute.manager<br>level: INFO<br>template: [instance: <*>] VM Paused (Lifecycle Event)<br>intent: vm_paused vm_lifecycle_event openstack_instance_lifecycle<br>signals: compute has_instance_id has_request_id instance_state manager<br>message: [<req_id> - - - - -] [instance: <instance_id>] VM Paused (Lifecycle Event) |
| line::openstack:c7466a4375561ea19116 | dataset: openstack<br>component: nova.compute.manager<br>level: INFO<br>event_type: sync_power_state<br>event_family: compute_lifecycle<br>template: [instance: <*>] During sync_power_state the instance has a pending task (spawning). Skip.<br>intent: sync_power_state_skipped pending_spawn_task openstack_instance_lifecycle<br>signals: compute compute_lifecycle has_instance_id has_request_id instance_state manager sync_power_state<br>message: [<req_id> - - - - -] [instance: <instance_id>] During sync_power_state the instance has a pending task (spawning). Skip. |
| line::openstack:bacde871a65751d778bd | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: <*> "GET <*>" status: <*> len: <*> time: <*>.<*><br>intent: api_get_request http_api_access openstack_api<br>signals: has_ip has_request_id http_request osapi_compute server wsgi<br>message: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: 200 len: 1893 time: 0.4256971 |
