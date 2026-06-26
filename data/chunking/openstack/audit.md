# Chunk Audit: openstack

## Counts

| metric | value |
| --- | --- |
| logs | 2000 |
| line_chunks | 2000 |
| template_chunks | 81 |
| line_chunks_match_logs | PASS |
| unique_line_chunk_ids | PASS (2000) |
| unique_template_chunk_ids | PASS (81) |
| singleton_templates | 14 (17.3%) |

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

## Top Templates

| count | component | level | template |
| --- | --- | --- | --- |
| 698 | nova.osapi_compute.wsgi.server | INFO | [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: <status> len: <len> time: <duration> |
| 82 | nova.virt.libvirt.imagecache | INFO | [<req_id> - - - - -] Active base files: <path> |
| 82 | nova.virt.libvirt.imagecache | INFO | [<req_id> - - - - -] image <uuid> at (<path>): checking |
| 82 | nova.virt.libvirt.imagecache | INFO | [<req_id> - - - - -] image <uuid> at (<path>): in use: on this node <num> local, <num> on other nodes sharing this instance storage |
| 44 | nova.compute.manager | INFO | [<req_id> - - - - -] [instance: <instance_id>] VM Resumed (Lifecycle Event) |
| 43 | nova.osapi_compute.wsgi.server | INFO | [<req_id> <hex_id> <hex_id> - - -] <ip> "POST route:v2 <hex_id> os-server-external-events HTTP/<version>" status: <status> len: <len> time: <duration> |
| 42 | nova.compute.manager | INFO | [<req_id> - - - - -] [instance: <instance_id>] During sync_power_state the instance has a pending task (spawning). Skip. |
| 42 | nova.metadata.wsgi.server | INFO | [<req_id> - - - - -] <ip>,<ip> "GET route:openstack <num>-<num>-<num> meta_data.json HTTP/<version>" status: <status> len: <len> time: <duration> |
| 31 | nova.metadata.wsgi.server | INFO | [<req_id> - - - - -] <ip>,<ip> "GET route:openstack <num>-<num>-<num> vendor_data.json HTTP/<version>" status: <status> len: <len> time: <duration> |
| 30 | nova.virt.libvirt.imagecache | INFO | [<req_id> - - - - -] Removable base files: <path> |

## Suspicious Template Samples

| reason | chunk_id | template |
| --- | --- | --- |
| singleton | template::openstack::c02c616b04f470a5 | [-] [instance: <instance_id>] During sync_power_state the instance has a pending task (spawning). Skip. |
| singleton | template::openstack::99616bb6fca7bd74 | [<req_id> - - - - -] Running instance usage audit for host cp-1.slowvm1.tcloud-pg0.utah.cloudlab.us from <num>-<num>-<num> <num>:<num>:<num> to <num>-<num>-<num> <num>:<num>:00. <num> instances. |
| singleton | template::openstack::2bc6785e891e3842 | [<req_id> - - - - -] While synchronizing instance power states, found <num> instances in the database and <num> instances on the hypervisor. |
| singleton | template::openstack::445de1728a8241ae | [-] <ip>,<ip> "GET route:latest meta-data ami-launch-index HTTP/<version>" status: <status> len: <len> time: <duration> |
| singleton | template::openstack::d4053efeef6730af | [-] <ip>,<ip> "GET route:latest meta-data hostname HTTP/<version>" status: <status> len: <len> time: <duration> |
| singleton | template::openstack::b58f130b981d89db | [<req_id> - - - - -] <ip>,<ip> "GET route:latest meta-data ami-id HTTP/<version>" status: <status> len: <len> time: <duration> |
| singleton | template::openstack::773e041f34a6440f | [<req_id> - - - - -] <ip>,<ip> "GET route:latest meta-data ami-launch-index HTTP/<version>" status: <status> len: <len> time: <duration> |
| singleton | template::openstack::3cab7659e99390ae | [<req_id> - - - - -] <ip>,<ip> "GET route:latest meta-data placement availability-zone HTTP/<version>" status: <status> len: <len> time: <duration> |
| singleton | template::openstack::47d4ba7efb4505e2 | [<req_id> - - - - -] <ip>,<ip> "GET route:latest meta-data public-hostname HTTP/<version>" status: <status> len: <len> time: <duration> |
| singleton | template::openstack::b80604d0da49d037 | [<req_id> - - - - -] <ip>,<ip> "GET route:latest meta-data reservation-id HTTP/<version>" status: <status> len: <len> time: <duration> |

## Line Chunk Samples

| chunk_id | embed_text |
| --- | --- |
| line::openstack:ce42502a78bda4f03311 | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: <status> len: <len> time: <duration><br>signals: has_ip has_request_id http_request osapi_compute server wsgi |
| line::openstack:ee3c000d74147e791bdb | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: <status> len: <len> time: <duration><br>signals: has_ip has_request_id http_request osapi_compute server wsgi |
| line::openstack:319b972344c6f3da3fbe | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: <status> len: <len> time: <duration><br>signals: has_ip has_request_id http_request osapi_compute server wsgi |
| line::openstack:342db085463108443414 | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: <status> len: <len> time: <duration><br>signals: has_ip has_request_id http_request osapi_compute server wsgi |
| line::openstack:e61fa138d9196f19888d | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: <status> len: <len> time: <duration><br>signals: has_ip has_request_id http_request osapi_compute server wsgi |
| line::openstack:256b722736f5fcf9bb66 | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: <status> len: <len> time: <duration><br>signals: has_ip has_request_id http_request osapi_compute server wsgi |
| line::openstack:2bab0edba84c892299aa | dataset: openstack<br>component: nova.compute.manager<br>level: INFO<br>template: [<req_id> - - - - -] [instance: <instance_id>] VM Started (Lifecycle Event)<br>signals: compute has_instance_id has_request_id instance_state manager |
| line::openstack:01e6fcdda9a0f6bb6016 | dataset: openstack<br>component: nova.compute.manager<br>level: INFO<br>template: [<req_id> - - - - -] [instance: <instance_id>] VM Paused (Lifecycle Event)<br>signals: compute has_instance_id has_request_id instance_state manager |
| line::openstack:c7466a4375561ea19116 | dataset: openstack<br>component: nova.compute.manager<br>level: INFO<br>template: [<req_id> - - - - -] [instance: <instance_id>] During sync_power_state the instance has a pending task (spawning). Skip.<br>signals: compute has_instance_id has_request_id instance_state manager sync_power_state |
| line::openstack:bacde871a65751d778bd | dataset: openstack<br>component: nova.osapi_compute.wsgi.server<br>level: INFO<br>template: [<req_id> <hex_id> <hex_id> - - -] <ip> "GET route:v2 <hex_id> servers detail HTTP/<version>" status: <status> len: <len> time: <duration><br>signals: has_ip has_request_id http_request osapi_compute server wsgi |
