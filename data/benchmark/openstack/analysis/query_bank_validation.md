# Query Bank Validation: openstack

## Summary

- Total queries: 30
- Query levels: easy=6, medium=18, hard=6
- Languages: vi=21, en=9
- Categories: storage=9, unknown=8, latency=7, network=4, database=2
- Queries with candidate logs: 26
- Queries without candidate logs: 4
- Queries with filters: 16
- Filters with no matching logs: 0
- Queries needing review: 21
- Broad queries: 7

## Filter Mismatches

| query_id | query | category | filters | suggestion |
| --- | --- | --- | --- | --- |


## Queries Needing Review

| query_id | level | language | category | candidates | matched_patterns | reasons | query | suggestion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| openstack_q002 | easy | vi | storage | 462 | imagecache=336, ~_base=336, ~file=193, base file=142, disk=78 | some weak keyword/pattern matches | Có cảnh báo nào về image cache hoặc base file không? | Candidate logs exist, but inspect weak matches before creating qrels. |
| openstack_q004 | easy | vi | unknown | 52 | level=WARN=31, \bwarn(?:ing)?\b=31, exception=21 | unknown category uses ERROR/WARN-only fallback | Control plane Nova có dấu hiệu bất thường không? | Manually review; unknown queries rely on abnormal-level or anomaly patterns. |
| openstack_q006 | easy | en | storage | 462 | imagecache=336, ~_base=336, ~file=193, base file=142, disk=78 | some weak keyword/pattern matches | Are there storage cache warnings in Nova compute? | Candidate logs exist, but inspect weak matches before creating qrels. |
| openstack_q009 | medium | vi | storage | 30 | ~file=30, imagecache=30, base file=30, ~_base=30 | candidate set is broad | Tìm cảnh báo Unknown base file trong image cache. | Make the query more specific or add a component/level filter. |
| openstack_q010 | medium | vi | storage | 336 | imagecache=336, ~_base=336, ~file=172, base file=142 | candidate set is broad | Có base image nào đang được kiểm tra hoặc đánh dấu in-use không? | Make the query more specific or add a component/level filter. |
| openstack_q011 | medium | vi | network | 22 | network=22, network-vif=22, vif=22 | candidate set is broad | Kiểm tra các event network-vif-plugged của instance. | Make the query more specific or add a component/level filter. |
| openstack_q012 | medium | vi | unknown | 1 | level=WARN=1, \bwarn(?:ing)?\b=1 | unknown category uses ERROR/WARN-only fallback | Có thao tác lifecycle nào của VM đáng chú ý không? | Manually review; unknown queries rely on abnormal-level or anomaly patterns. |
| openstack_q013 | medium | vi | database | 44 | ~hypervisor=44, database=2 | some weak keyword/pattern matches | Tìm dấu hiệu mismatch giữa trạng thái instance trong database và hypervisor. | Candidate logs exist, but inspect weak matches before creating qrels. |
| openstack_q014 | medium | vi | storage | 30 | ~file=30, imagecache=30, base file=30, ~_base=30 | candidate set is broad | Có cảnh báo WARN nào trong nova compute không? | Make the query more specific or add a component/level filter. |
| openstack_q015 | medium | vi | unknown | 0 |  | unknown category uses ERROR/WARN-only fallback, no candidate logs found | Tìm các log về resource claim hoặc tài nguyên instance. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| openstack_q016 | medium | en | storage | 336 | imagecache=336, ~_base=336, ~file=172, base file=142 | candidate set is broad | Find image cache records for active or unknown base files. | Make the query more specific or add a component/level filter. |
| openstack_q017 | medium | en | network | 22 | network=22, network-vif=22, vif=22 | candidate set is broad | Find network VIF events emitted by the compute API. | Make the query more specific or add a component/level filter. |
| openstack_q019 | medium | en | unknown | 0 |  | unknown category uses ERROR/WARN-only fallback, no candidate logs found | Show Nova API request handling records. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| openstack_q020 | medium | en | storage | 462 | imagecache=336, ~_base=336, ~file=193, base file=142, disk=78 | some weak keyword/pattern matches | Which logs indicate storage housekeeping in Nova image cache? | Candidate logs exist, but inspect weak matches before creating qrels. |
| openstack_q021 | medium | vi | unknown | 0 |  | unknown category uses ERROR/WARN-only fallback, no candidate logs found | Có dấu hiệu scheduler hoặc resource tracker thay đổi trạng thái tài nguyên không? | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| openstack_q022 | medium | vi | unknown | 0 |  | unknown category uses ERROR/WARN-only fallback, no candidate logs found | Tìm log metadata API phục vụ request từ instance. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| openstack_q024 | hard | vi | storage | 30 | ~file=30, imagecache=30, base file=30, ~_base=30 | candidate set is broad | Có chuỗi log nào liên kết image cache warning với trạng thái instance không? | Make the query more specific or add a component/level filter. |
| openstack_q025 | hard | vi | unknown | 52 | level=WARN=31, \bwarn(?:ing)?\b=31, exception=21 | unknown category uses ERROR/WARN-only fallback | Tìm bằng chứng control plane đang bận xử lý lifecycle của VM. | Manually review; unknown queries rely on abnormal-level or anomaly patterns. |
| openstack_q028 | hard | en | storage | 462 | imagecache=336, ~_base=336, ~file=193, base file=142, disk=78 | some weak keyword/pattern matches | Find evidence of image cache inconsistency on the compute host. | Candidate logs exist, but inspect weak matches before creating qrels. |
| openstack_q029 | medium | vi | database | 44 | ~hypervisor=44, database=2 | some weak keyword/pattern matches | Có bất thường nào giữa database, hypervisor và trạng thái instance không? | Candidate logs exist, but inspect weak matches before creating qrels. |
| openstack_q030 | medium | vi | unknown | 52 | level=WARN=31, \bwarn(?:ing)?\b=31, exception=21 | unknown category uses ERROR/WARN-only fallback | Có dấu hiệu tổng quan nào cho thấy Nova control plane không khỏe không? | Manually review; unknown queries rely on abnormal-level or anomaly patterns. |


## Suggestions To Revise Or Drop

| query_id | candidate_count | matched_patterns | query | suggestion |
| --- | --- | --- | --- | --- |
| openstack_q009 | 30 | ~file=30, imagecache=30, base file=30, ~_base=30 | Tìm cảnh báo Unknown base file trong image cache. | Make the query more specific or add a component/level filter. |
| openstack_q010 | 336 | imagecache=336, ~_base=336, ~file=172, base file=142 | Có base image nào đang được kiểm tra hoặc đánh dấu in-use không? | Make the query more specific or add a component/level filter. |
| openstack_q011 | 22 | network=22, network-vif=22, vif=22 | Kiểm tra các event network-vif-plugged của instance. | Make the query more specific or add a component/level filter. |
| openstack_q014 | 30 | ~file=30, imagecache=30, base file=30, ~_base=30 | Có cảnh báo WARN nào trong nova compute không? | Make the query more specific or add a component/level filter. |
| openstack_q015 | 0 |  | Tìm các log về resource claim hoặc tài nguyên instance. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| openstack_q016 | 336 | imagecache=336, ~_base=336, ~file=172, base file=142 | Find image cache records for active or unknown base files. | Make the query more specific or add a component/level filter. |
| openstack_q017 | 22 | network=22, network-vif=22, vif=22 | Find network VIF events emitted by the compute API. | Make the query more specific or add a component/level filter. |
| openstack_q019 | 0 |  | Show Nova API request handling records. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| openstack_q021 | 0 |  | Có dấu hiệu scheduler hoặc resource tracker thay đổi trạng thái tài nguyên không? | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| openstack_q022 | 0 |  | Tìm log metadata API phục vụ request từ instance. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| openstack_q024 | 30 | ~file=30, imagecache=30, base file=30, ~_base=30 | Có chuỗi log nào liên kết image cache warning với trạng thái instance không? | Make the query more specific or add a component/level filter. |


## Per-Query Candidate Counts

| query_id | level | language | category | filters | filtered_logs | candidate_logs | weak_candidates | matched_patterns | supported |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| openstack_q001 | easy | vi | latency | {'component': None, 'level': None, 'time_range': None} | 2000 | 140 | 0 | took=172, slow=54 | yes |
| openstack_q002 | easy | vi | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 462 | 48 | imagecache=336, ~_base=336, ~file=193, base file=142, disk=78 | yes |
| openstack_q003 | easy | vi | network | {'component': None, 'level': None, 'time_range': None} | 2000 | 43 | 0 | network=43, network-vif=22, vif=22 | yes |
| openstack_q004 | easy | vi | unknown | {'component': None, 'level': None, 'time_range': None} | 2000 | 52 | 0 | level=WARN=31, \bwarn(?:ing)?\b=31, exception=21 | yes |
| openstack_q005 | easy | en | latency | {'component': None, 'level': None, 'time_range': None} | 2000 | 140 | 0 | took=172, slow=54 | yes |
| openstack_q006 | easy | en | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 462 | 48 | imagecache=336, ~_base=336, ~file=193, base file=142, disk=78 | yes |
| openstack_q007 | medium | vi | latency | {'component': 'nova.compute.manager', 'level': None, 'time_range': None} | 262 | 87 | 0 | took=172, slow=1 | yes |
| openstack_q008 | medium | vi | latency | {'component': 'nova.osapi_compute.wsgi.server', 'level': None, 'time_range': None} | 809 | 1 | 0 | slow=1 | yes |
| openstack_q009 | medium | vi | storage | {'component': 'nova.virt.libvirt.imagecache', 'level': 'WARN', 'time_range': None} | 30 | 30 | 0 | ~file=30, imagecache=30, base file=30, ~_base=30 | yes |
| openstack_q010 | medium | vi | storage | {'component': 'nova.virt.libvirt.imagecache', 'level': None, 'time_range': None} | 336 | 336 | 0 | imagecache=336, ~_base=336, ~file=172, base file=142 | yes |
| openstack_q011 | medium | vi | network | {'component': 'nova.api.openstack.compute.server_external_events', 'level': None, 'time_range': None} | 22 | 22 | 0 | network=22, network-vif=22, vif=22 | yes |
| openstack_q012 | medium | vi | unknown | {'component': 'nova.compute.manager', 'level': None, 'time_range': None} | 262 | 1 | 0 | level=WARN=1, \bwarn(?:ing)?\b=1 | yes |
| openstack_q013 | medium | vi | database | {'component': 'nova.compute.manager', 'level': None, 'time_range': None} | 262 | 44 | 43 | ~hypervisor=44, database=2 | yes |
| openstack_q014 | medium | vi | storage | {'component': None, 'level': 'WARN', 'time_range': None} | 31 | 30 | 0 | ~file=30, imagecache=30, base file=30, ~_base=30 | yes |
| openstack_q015 | medium | vi | unknown | {'component': 'nova.compute.claims', 'level': None, 'time_range': None} | 168 | 0 | 0 |  | no |
| openstack_q016 | medium | en | storage | {'component': 'nova.virt.libvirt.imagecache', 'level': None, 'time_range': None} | 336 | 336 | 0 | imagecache=336, ~_base=336, ~file=172, base file=142 | yes |
| openstack_q017 | medium | en | network | {'component': 'nova.api.openstack.compute.server_external_events', 'level': None, 'time_range': None} | 22 | 22 | 0 | network=22, network-vif=22, vif=22 | yes |
| openstack_q018 | medium | en | latency | {'component': 'nova.compute.manager', 'level': None, 'time_range': None} | 262 | 87 | 0 | took=172, slow=1 | yes |
| openstack_q019 | medium | en | unknown | {'component': 'nova.osapi_compute.wsgi.server', 'level': None, 'time_range': None} | 809 | 0 | 0 |  | no |
| openstack_q020 | medium | en | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 462 | 48 | imagecache=336, ~_base=336, ~file=193, base file=142, disk=78 | yes |
| openstack_q021 | medium | vi | unknown | {'component': 'nova.compute.resource_tracker', 'level': None, 'time_range': None} | 60 | 0 | 0 |  | no |
| openstack_q022 | medium | vi | unknown | {'component': 'nova.metadata.wsgi.server', 'level': None, 'time_range': None} | 208 | 0 | 0 |  | no |
| openstack_q023 | hard | vi | latency | {'component': None, 'level': None, 'time_range': None} | 2000 | 140 | 0 | took=172, slow=54 | yes |
| openstack_q024 | hard | vi | storage | {'component': None, 'level': 'WARN', 'time_range': None} | 31 | 30 | 0 | ~file=30, imagecache=30, base file=30, ~_base=30 | yes |
| openstack_q025 | hard | vi | unknown | {'component': None, 'level': None, 'time_range': None} | 2000 | 52 | 0 | level=WARN=31, \bwarn(?:ing)?\b=31, exception=21 | yes |
| openstack_q026 | hard | vi | network | {'component': None, 'level': None, 'time_range': None} | 2000 | 43 | 0 | network=43, network-vif=22, vif=22 | yes |
| openstack_q027 | hard | en | latency | {'component': None, 'level': None, 'time_range': None} | 2000 | 140 | 0 | took=172, slow=54 | yes |
| openstack_q028 | hard | en | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 462 | 48 | imagecache=336, ~_base=336, ~file=193, base file=142, disk=78 | yes |
| openstack_q029 | medium | vi | database | {'component': None, 'level': None, 'time_range': None} | 2000 | 44 | 43 | ~hypervisor=44, database=2 | yes |
| openstack_q030 | medium | vi | unknown | {'component': None, 'level': None, 'time_range': None} | 2000 | 52 | 0 | level=WARN=31, \bwarn(?:ing)?\b=31, exception=21 | yes |
