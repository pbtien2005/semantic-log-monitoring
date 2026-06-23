# Qrels V2 Generation Report: openstack

## Summary

- Positive labels v1 vs v2: 482 vs 302
- Hard negative labels v1 vs v2: 260 vs 300
- Uncertain labels v1 vs v2: 65 vs 91
- Queries with no positive: 13
- Queries needs_review: 24
- Avg positives/query v2: 10.07

## Top Positive Count Reductions

| query_id | v1_positive_count | v2_positive_count | delta |
| --- | --- | --- | --- |
| openstack_q003 | 20 | 0 | -20 |
| openstack_q004 | 20 | 0 | -20 |
| openstack_q011 | 20 | 0 | -20 |
| openstack_q017 | 20 | 0 | -20 |
| openstack_q025 | 20 | 0 | -20 |
| openstack_q026 | 20 | 0 | -20 |
| openstack_q030 | 20 | 0 | -20 |
| openstack_q013 | 20 | 1 | -19 |
| openstack_q029 | 20 | 1 | -19 |
| openstack_q008 | 1 | 0 | -1 |
| openstack_q012 | 1 | 0 | -1 |
| openstack_q001 | 20 | 20 | 0 |
| openstack_q002 | 20 | 20 | 0 |
| openstack_q005 | 20 | 20 | 0 |
| openstack_q006 | 20 | 20 | 0 |


## Queries With No Positive

| query_id | category | query | review_reasons |
| --- | --- | --- | --- |
| openstack_q003 | network | Có sự kiện mạng liên quan đến VIF của instance không? | no positive above v2 threshold |
| openstack_q004 | unknown | Control plane Nova có dấu hiệu bất thường không? | category unknown, no positive above v2 threshold, has uncertain candidates |
| openstack_q008 | latency | Có API call nào trả về bình thường nhưng thời gian xử lý cao không? | no positive above v2 threshold |
| openstack_q011 | network | Kiểm tra các event network-vif-plugged của instance. | no positive above v2 threshold |
| openstack_q012 | unknown | Có thao tác lifecycle nào của VM đáng chú ý không? | category unknown, no positive above v2 threshold, has uncertain candidates |
| openstack_q015 | unknown | Tìm các log về resource claim hoặc tài nguyên instance. | category unknown, no positive above v2 threshold, multi-clause query |
| openstack_q017 | network | Find network VIF events emitted by the compute API. | no positive above v2 threshold |
| openstack_q019 | unknown | Show Nova API request handling records. | category unknown, no positive above v2 threshold |
| openstack_q021 | unknown | Có dấu hiệu scheduler hoặc resource tracker thay đổi trạng thái tài nguyên không? | category unknown, no positive above v2 threshold, multi-clause query |
| openstack_q022 | unknown | Tìm log metadata API phục vụ request từ instance. | category unknown, no positive above v2 threshold |
| openstack_q025 | unknown | Tìm bằng chứng control plane đang bận xử lý lifecycle của VM. | category unknown, hard query, no positive above v2 threshold, has uncertain candidates |
| openstack_q026 | network | Có dấu hiệu network event ảnh hưởng đến tiến trình spawn hoặc resume instance không? | hard query, no positive above v2 threshold, multi-clause query |
| openstack_q030 | unknown | Có dấu hiệu tổng quan nào cho thấy Nova control plane không khỏe không? | category unknown, no positive above v2 threshold, has uncertain candidates |


## Examples Fixed Or Downgraded

| query_id | label | reason | message |
| --- | --- | --- | --- |
| openstack_q001 | hard_negative | hard_negative: took<5s | [req-c53a921a-16c7-422e-8c9d-c922a720d047 113d3a99c3da401fbd62cc2caa5b96d2 54fadb412c4e40cdbaed9335e4c35a9e - - -] [instance: b9000564-fe1a-409b-b8cc-1e88b294cd1d] Took 1.03 seconds to destroy the instance on the hypervi |
| openstack_q001 | hard_negative | hard_negative: took<5s | [req-d473bea3-588a-441a-8b2a-a137806f8786 113d3a99c3da401fbd62cc2caa5b96d2 54fadb412c4e40cdbaed9335e4c35a9e - - -] [instance: 96abccce-8d1f-4e07-b6d1-4b2ab87e23b4] Took 1.11 seconds to destroy the instance on the hypervi |
| openstack_q001 | hard_negative | hard_negative: took<5s | [req-31d09752-6f82-4fc5-ac97-416b9c865af4 113d3a99c3da401fbd62cc2caa5b96d2 54fadb412c4e40cdbaed9335e4c35a9e - - -] [instance: b562ef10-ba2d-48ae-bf4a-18666cba4a51] Took 1.05 seconds to destroy the instance on the hypervi |
| openstack_q001 | hard_negative | hard_negative: took<5s | [req-06631678-1e19-4e4e-bddf-a588d8ea6217 113d3a99c3da401fbd62cc2caa5b96d2 54fadb412c4e40cdbaed9335e4c35a9e - - -] [instance: 78dc1847-8848-49cc-933e-9239b12c9dcf] Took 1.02 seconds to destroy the instance on the hypervi |
| openstack_q001 | hard_negative | hard_negative: took<5s | [req-a6b9779d-b384-4e84-b3d0-bac079760244 113d3a99c3da401fbd62cc2caa5b96d2 54fadb412c4e40cdbaed9335e4c35a9e - - -] [instance: 95960536-049b-41f6-9049-05fc479b6a7c] Took 1.00 seconds to destroy the instance on the hypervi |
| openstack_q003 | hard_negative | hard_negative: plugged | [req-ab451068-9756-4ad9-9d18-5ceaa6424627 f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] Creating event network-vif-plugged:e3871ffd-5cd5-4287-bddd-3529f7b59515 for instance b9000564-fe1a-409b-b |
| openstack_q003 | hard_negative | hard_negative: plugged | [req-3e22b75e-1c4f-4579-8a73-7ede40d3f955 f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] Creating event network-vif-plugged:a208479c-c0e3-4730-a5a0-d75e8afd0252 for instance 96abccce-8d1f-4e07-b |
| openstack_q003 | hard_negative | hard_negative: plugged | [req-01451338-4c87-48c4-9dbc-a9831f8f6d41 f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] Creating event network-vif-plugged:d1ce4c5a-2811-41c3-8a5a-39f9e6defcb8 for instance b562ef10-ba2d-48ae-b |
| openstack_q003 | hard_negative | hard_negative: plugged | [req-74354c38-3eb0-4bde-a63d-5a53b008030c f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] Creating event network-vif-plugged:b26c4935-6377-4e96-9ba1-ec6985d42d5d for instance 78dc1847-8848-49cc-9 |
| openstack_q003 | hard_negative | hard_negative: plugged | [req-e265ea4c-ba4b-44f0-b086-7420e34e17cb f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] Creating event network-vif-plugged:1cf11429-1563-4f6c-823c-91ba6e0f6675 for instance 95960536-049b-41f6-9 |
| openstack_q003 | hard_negative | hard_negative: plugged | [req-3be0ba1e-d96d-483e-b14d-e3c6c34f36f7 f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] Creating event network-vif-plugged:85754923-baff-45ad-9e35-a3055c898234 for instance 7e7cc42f-3cb9-4d91-8 |
| openstack_q003 | hard_negative | hard_negative: plugged | [req-0b7fefce-6f00-464a-969a-d6799e8bba35 f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] Creating event network-vif-plugged:7bdba89d-dd80-489c-ab06-11d494c5c478 for instance af5f7392-f7d4-4298-b |
| openstack_q003 | hard_negative | hard_negative: plugged | [req-7159484f-4b91-464c-a6f6-c7820ded6511 f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] Creating event network-vif-plugged:98dbd0a6-013e-4cd9-9986-fa32e5d6dd32 for instance ae3a1b5d-eec1-45bb-b |
| openstack_q003 | hard_negative | hard_negative: plugged | [req-297ec716-683d-434e-8b23-eb29cdd762cb f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] Creating event network-vif-plugged:60df1c66-a513-4973-aeed-095809a52794 for instance 43204226-2f87-4da7-b |
| openstack_q003 | hard_negative | hard_negative: plugged | [req-5825bf9a-4201-4b20-a68a-f3a7e1addf40 f7b8d1f1d4d44643b07fa10ca7d021fb e9746973ac574c6b8a9e8857f56a7608 - - -] Creating event network-vif-plugged:8b683414-2896-4251-aa05-980752c9b9b3 for instance fecdd5a9-3ca0-4c82-9 |
| openstack_q004 | uncertain | uncertain: weak pattern only | [req-addc1839-2ed5-4778-b57e-5854eb7b8b09 - - - - -] Unknown base file: /var/lib/nova/instances/_base/a489c868f0c37da93b76227c91bb03908ac0e742 |
| openstack_q004 | uncertain | uncertain: weak pattern only | [req-addc1839-2ed5-4778-b57e-5854eb7b8b09 - - - - -] Unknown base file: /var/lib/nova/instances/_base/a489c868f0c37da93b76227c91bb03908ac0e742 |
| openstack_q004 | uncertain | uncertain: weak pattern only | [req-addc1839-2ed5-4778-b57e-5854eb7b8b09 - - - - -] Unknown base file: /var/lib/nova/instances/_base/a489c868f0c37da93b76227c91bb03908ac0e742 |
| openstack_q004 | uncertain | uncertain: weak pattern only | [req-addc1839-2ed5-4778-b57e-5854eb7b8b09 - - - - -] Unknown base file: /var/lib/nova/instances/_base/a489c868f0c37da93b76227c91bb03908ac0e742 |
| openstack_q004 | uncertain | uncertain: weak pattern only | [req-addc1839-2ed5-4778-b57e-5854eb7b8b09 - - - - -] Unknown base file: /var/lib/nova/instances/_base/a489c868f0c37da93b76227c91bb03908ac0e742 |
