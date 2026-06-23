# Qrels Generation Report: openstack

## Summary

- Total queries: 30
- Queries with positive logs: 26
- Queries with empty positive_log_ids: 4
- Queries needing review: 19
- Avg positives/query: 16.07
- Avg hard negatives/query: 10.00
- Query levels: easy=6, medium=18, hard=6
- Categories: storage=9, unknown=8, latency=7, network=4, database=2

## Unsupported Queries

| query_id | category | query | reason |
| --- | --- | --- | --- |
| openstack_q015 | unknown | Tìm các log về resource claim hoặc tài nguyên instance. | no candidate log matched category/filter rules |
| openstack_q019 | unknown | Show Nova API request handling records. | no candidate log matched category/filter rules |
| openstack_q021 | unknown | Có dấu hiệu scheduler hoặc resource tracker thay đổi trạng thái tài nguyên không? | no candidate log matched category/filter rules |
| openstack_q022 | unknown | Tìm log metadata API phục vụ request từ instance. | no candidate log matched category/filter rules |


## Queries Needing Most Review

| query_id | positive_count | negative_count | reasons | query |
| --- | --- | --- | --- | --- |
| openstack_q015 | 0 | 10 | category unknown requires manual review, unsupported by category/filter rules, query contains multiple intents or clauses | Tìm các log về resource claim hoặc tài nguyên instance. |
| openstack_q021 | 0 | 10 | category unknown requires manual review, unsupported by category/filter rules, query contains multiple intents or clauses | Có dấu hiệu scheduler hoặc resource tracker thay đổi trạng thái tài nguyên không? |
| openstack_q012 | 1 | 10 | category unknown requires manual review, too few positive candidates | Có thao tác lifecycle nào của VM đáng chú ý không? |
| openstack_q013 | 20 | 10 | some positive candidates rely on weak patterns, query contains multiple intents or clauses | Tìm dấu hiệu mismatch giữa trạng thái instance trong database và hypervisor. |
| openstack_q019 | 0 | 10 | category unknown requires manual review, unsupported by category/filter rules | Show Nova API request handling records. |
| openstack_q022 | 0 | 10 | category unknown requires manual review, unsupported by category/filter rules | Tìm log metadata API phục vụ request từ instance. |
| openstack_q025 | 20 | 10 | category unknown requires manual review, hard query requires manual review | Tìm bằng chứng control plane đang bận xử lý lifecycle của VM. |
| openstack_q026 | 20 | 10 | hard query requires manual review, query contains multiple intents or clauses | Có dấu hiệu network event ảnh hưởng đến tiến trình spawn hoặc resume instance không? |
| openstack_q029 | 20 | 10 | some positive candidates rely on weak patterns, query contains multiple intents or clauses | Có bất thường nào giữa database, hypervisor và trạng thái instance không? |
| openstack_q002 | 20 | 10 | query contains multiple intents or clauses | Có cảnh báo nào về image cache hoặc base file không? |
| openstack_q004 | 20 | 10 | category unknown requires manual review | Control plane Nova có dấu hiệu bất thường không? |
| openstack_q008 | 1 | 10 | too few positive candidates | Có API call nào trả về bình thường nhưng thời gian xử lý cao không? |
| openstack_q010 | 20 | 10 | query contains multiple intents or clauses | Có base image nào đang được kiểm tra hoặc đánh dấu in-use không? |
| openstack_q016 | 20 | 10 | query contains multiple intents or clauses | Find image cache records for active or unknown base files. |
| openstack_q023 | 20 | 10 | hard query requires manual review | Vì sao thao tác instance bị chậm dù request API vẫn thành công? |
| openstack_q024 | 20 | 10 | hard query requires manual review | Có chuỗi log nào liên kết image cache warning với trạng thái instance không? |
| openstack_q027 | 20 | 10 | hard query requires manual review | Which logs suggest Nova compute is doing slow backend work? |
| openstack_q028 | 20 | 10 | hard query requires manual review | Find evidence of image cache inconsistency on the compute host. |
| openstack_q030 | 20 | 10 | category unknown requires manual review | Có dấu hiệu tổng quan nào cho thấy Nova control plane không khỏe không? |
