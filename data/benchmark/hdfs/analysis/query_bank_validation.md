# Query Bank Validation: hdfs

## Summary

- Total queries: 30
- Query levels: easy=6, medium=18, hard=6
- Languages: vi=21, en=9
- Categories: storage=16, service_unavailable=10, unknown=4
- Queries with candidate logs: 28
- Queries without candidate logs: 2
- Queries with filters: 16
- Filters with no matching logs: 0
- Queries needing review: 25
- Broad queries: 21

## Filter Mismatches

| query_id | query | category | filters | suggestion |
| --- | --- | --- | --- | --- |


## Queries Needing Review

| query_id | level | language | category | candidates | matched_patterns | reasons | query | suggestion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hdfs_q002 | easy | vi | storage | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | candidate set is broad | Có block nào được ghi nhận hoặc cập nhật trong HDFS không? | Make the query more specific or add a component/level filter. |
| hdfs_q003 | easy | vi | storage | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | candidate set is broad | Có node nào liên quan đến truyền dữ liệu block không? | Make the query more specific or add a component/level filter. |
| hdfs_q004 | easy | vi | unknown | 80 | exception=160, level=WARN=80, \bwarn(?:ing)?\b=80, warn=80 | unknown category uses ERROR/WARN-only fallback | Cluster HDFS có dấu hiệu bất thường không? | Manually review; unknown queries rely on abnormal-level or anomaly patterns. |
| hdfs_q006 | easy | en | storage | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | candidate set is broad | Are there block metadata updates in NameNode logs? | Make the query more specific or add a component/level filter. |
| hdfs_q007 | medium | vi | service_unavailable | 80 | exception while serving=80, got exception while serving=80, exception=80 | candidate set is broad | Tìm exception khi DataXceiver gửi block cho client hoặc node khác. | Make the query more specific or add a component/level filter. |
| hdfs_q008 | medium | vi | storage | 454 | datanode=454, blk_=454, ~block=374 | candidate set is broad | Có block nào được DataNode nhận hoặc phục vụ không? | Make the query more specific or add a component/level filter. |
| hdfs_q009 | medium | vi | storage | 603 | ~block=603, datanode=603, blk_=603, packetresponder=603 | candidate set is broad | Kiểm tra các log PacketResponder kết thúc xử lý block. | Make the query more specific or add a component/level filter. |
| hdfs_q010 | medium | vi | storage | 659 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | candidate set is broad | Tìm cập nhật blockMap từ FSNamesystem. | Make the query more specific or add a component/level filter. |
| hdfs_q011 | medium | vi | storage | 659 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | candidate set is broad | Có block nào được allocate cho file tạm trong HDFS không? | Make the query more specific or add a component/level filter. |
| hdfs_q012 | medium | vi | service_unavailable | 80 | exception while serving=80, got exception while serving=80, exception=80 | candidate set is broad | Tìm các cảnh báo WARN liên quan đến block serving. | Make the query more specific or add a component/level filter. |
| hdfs_q013 | medium | vi | unknown | 0 |  | unknown category uses ERROR/WARN-only fallback, no candidate logs found | Có quá trình verification block nào thành công không? | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| hdfs_q014 | medium | vi | storage | 263 | ~block=263, ~file=263, blk_=263, fsdataset=263 | candidate set is broad | Kiểm tra FSDataset trong các thao tác lưu trữ block. | Make the query more specific or add a component/level filter. |
| hdfs_q015 | medium | vi | service_unavailable | 80 | exception while serving=80, got exception while serving=80, exception=80 | candidate set is broad | Có node hoặc địa chỉ nào xuất hiện khi block transfer gặp sự cố không? | Make the query more specific or add a component/level filter. |
| hdfs_q016 | medium | en | service_unavailable | 80 | exception while serving=80, got exception while serving=80, exception=80 | candidate set is broad | Find DataXceiver warnings while serving blocks. | Make the query more specific or add a component/level filter. |
| hdfs_q017 | medium | en | storage | 659 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | candidate set is broad | Find FSNamesystem records that update block locations. | Make the query more specific or add a component/level filter. |
| hdfs_q018 | medium | en | storage | 603 | ~block=603, datanode=603, blk_=603, packetresponder=603 | candidate set is broad | Look for PacketResponder block completion events. | Make the query more specific or add a component/level filter. |
| hdfs_q019 | medium | en | unknown | 0 |  | unknown category uses ERROR/WARN-only fallback, no candidate logs found | Show block scanner verification records. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| hdfs_q020 | medium | en | storage | 263 | ~block=263, ~file=263, blk_=263, fsdataset=263 | candidate set is broad | Which logs show storage activity inside HDFS dataset handling? | Make the query more specific or add a component/level filter. |
| hdfs_q022 | medium | vi | storage | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | candidate set is broad | Tìm các log về block replication hoặc vị trí block được cập nhật. | Make the query more specific or add a component/level filter. |
| hdfs_q023 | hard | vi | service_unavailable | 80 | exception while serving=80, got exception while serving=80, exception=80 | candidate set is broad | Node nào có dấu hiệu gặp lỗi lặp lại khi phục vụ block? | Make the query more specific or add a component/level filter. |
| hdfs_q024 | hard | vi | storage | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | candidate set is broad | Có chuỗi sự kiện nào từ nhận block đến responder kết thúc không? | Make the query more specific or add a component/level filter. |
| hdfs_q025 | hard | vi | storage | 659 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | candidate set is broad | Tìm bằng chứng blockMap thay đổi quanh các block có sự cố. | Make the query more specific or add a component/level filter. |
| hdfs_q026 | hard | vi | unknown | 80 | exception=160, level=WARN=80, \bwarn(?:ing)?\b=80, warn=80 | unknown category uses ERROR/WARN-only fallback | Có log nào cho thấy block vẫn được verify dù cluster có cảnh báo không? | Manually review; unknown queries rely on abnormal-level or anomaly patterns. |
| hdfs_q028 | hard | en | storage | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | candidate set is broad | Find evidence of repeated block movement across DataNodes. | Make the query more specific or add a component/level filter. |
| hdfs_q030 | medium | vi | storage | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | candidate set is broad | Có dấu hiệu tổng quan nào cho thấy HDFS storage layer không khỏe không? | Make the query more specific or add a component/level filter. |


## Suggestions To Revise Or Drop

| query_id | candidate_count | matched_patterns | query | suggestion |
| --- | --- | --- | --- | --- |
| hdfs_q002 | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | Có block nào được ghi nhận hoặc cập nhật trong HDFS không? | Make the query more specific or add a component/level filter. |
| hdfs_q003 | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | Có node nào liên quan đến truyền dữ liệu block không? | Make the query more specific or add a component/level filter. |
| hdfs_q006 | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | Are there block metadata updates in NameNode logs? | Make the query more specific or add a component/level filter. |
| hdfs_q007 | 80 | exception while serving=80, got exception while serving=80, exception=80 | Tìm exception khi DataXceiver gửi block cho client hoặc node khác. | Make the query more specific or add a component/level filter. |
| hdfs_q008 | 454 | datanode=454, blk_=454, ~block=374 | Có block nào được DataNode nhận hoặc phục vụ không? | Make the query more specific or add a component/level filter. |
| hdfs_q009 | 603 | ~block=603, datanode=603, blk_=603, packetresponder=603 | Kiểm tra các log PacketResponder kết thúc xử lý block. | Make the query more specific or add a component/level filter. |
| hdfs_q010 | 659 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | Tìm cập nhật blockMap từ FSNamesystem. | Make the query more specific or add a component/level filter. |
| hdfs_q011 | 659 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | Có block nào được allocate cho file tạm trong HDFS không? | Make the query more specific or add a component/level filter. |
| hdfs_q012 | 80 | exception while serving=80, got exception while serving=80, exception=80 | Tìm các cảnh báo WARN liên quan đến block serving. | Make the query more specific or add a component/level filter. |
| hdfs_q013 | 0 |  | Có quá trình verification block nào thành công không? | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| hdfs_q014 | 263 | ~block=263, ~file=263, blk_=263, fsdataset=263 | Kiểm tra FSDataset trong các thao tác lưu trữ block. | Make the query more specific or add a component/level filter. |
| hdfs_q015 | 80 | exception while serving=80, got exception while serving=80, exception=80 | Có node hoặc địa chỉ nào xuất hiện khi block transfer gặp sự cố không? | Make the query more specific or add a component/level filter. |
| hdfs_q016 | 80 | exception while serving=80, got exception while serving=80, exception=80 | Find DataXceiver warnings while serving blocks. | Make the query more specific or add a component/level filter. |
| hdfs_q017 | 659 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | Find FSNamesystem records that update block locations. | Make the query more specific or add a component/level filter. |
| hdfs_q018 | 603 | ~block=603, datanode=603, blk_=603, packetresponder=603 | Look for PacketResponder block completion events. | Make the query more specific or add a component/level filter. |
| hdfs_q019 | 0 |  | Show block scanner verification records. | Revise the query category or add a dataset-specific keyword rule before using it for qrels. |
| hdfs_q020 | 263 | ~block=263, ~file=263, blk_=263, fsdataset=263 | Which logs show storage activity inside HDFS dataset handling? | Make the query more specific or add a component/level filter. |
| hdfs_q022 | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | Tìm các log về block replication hoặc vị trí block được cập nhật. | Make the query more specific or add a component/level filter. |
| hdfs_q023 | 80 | exception while serving=80, got exception while serving=80, exception=80 | Node nào có dấu hiệu gặp lỗi lặp lại khi phục vụ block? | Make the query more specific or add a component/level filter. |
| hdfs_q024 | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | Có chuỗi sự kiện nào từ nhận block đến responder kết thúc không? | Make the query more specific or add a component/level filter. |
| hdfs_q025 | 659 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | Tìm bằng chứng blockMap thay đổi quanh các block có sự cố. | Make the query more specific or add a component/level filter. |
| hdfs_q028 | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | Find evidence of repeated block movement across DataNodes. | Make the query more specific or add a component/level filter. |
| hdfs_q030 | 2000 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | Có dấu hiệu tổng quan nào cho thấy HDFS storage layer không khỏe không? | Make the query more specific or add a component/level filter. |


## Per-Query Candidate Counts

| query_id | level | language | category | filters | filtered_logs | candidate_logs | weak_candidates | matched_patterns | supported |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hdfs_q001 | easy | vi | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 80 | 0 | exception while serving=80, got exception while serving=80, exception=80 | yes |
| hdfs_q002 | easy | vi | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 2000 | 0 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | yes |
| hdfs_q003 | easy | vi | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 2000 | 0 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | yes |
| hdfs_q004 | easy | vi | unknown | {'component': None, 'level': None, 'time_range': None} | 2000 | 80 | 0 | exception=160, level=WARN=80, \bwarn(?:ing)?\b=80, warn=80 | yes |
| hdfs_q005 | easy | en | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 80 | 0 | exception while serving=80, got exception while serving=80, exception=80 | yes |
| hdfs_q006 | easy | en | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 2000 | 0 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | yes |
| hdfs_q007 | medium | vi | service_unavailable | {'component': 'dfs.DataNode$DataXceiver', 'level': 'WARN', 'time_range': None} | 80 | 80 | 0 | exception while serving=80, got exception while serving=80, exception=80 | yes |
| hdfs_q008 | medium | vi | storage | {'component': 'dfs.DataNode$DataXceiver', 'level': None, 'time_range': None} | 454 | 454 | 0 | datanode=454, blk_=454, ~block=374 | yes |
| hdfs_q009 | medium | vi | storage | {'component': 'dfs.DataNode$PacketResponder', 'level': None, 'time_range': None} | 603 | 603 | 0 | ~block=603, datanode=603, blk_=603, packetresponder=603 | yes |
| hdfs_q010 | medium | vi | storage | {'component': 'dfs.FSNamesystem', 'level': None, 'time_range': None} | 659 | 659 | 0 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | yes |
| hdfs_q011 | medium | vi | storage | {'component': 'dfs.FSNamesystem', 'level': None, 'time_range': None} | 659 | 659 | 0 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | yes |
| hdfs_q012 | medium | vi | service_unavailable | {'component': None, 'level': 'WARN', 'time_range': None} | 80 | 80 | 0 | exception while serving=80, got exception while serving=80, exception=80 | yes |
| hdfs_q013 | medium | vi | unknown | {'component': 'dfs.DataBlockScanner', 'level': None, 'time_range': None} | 20 | 0 | 0 |  | no |
| hdfs_q014 | medium | vi | storage | {'component': 'dfs.FSDataset', 'level': None, 'time_range': None} | 263 | 263 | 0 | ~block=263, ~file=263, blk_=263, fsdataset=263 | yes |
| hdfs_q015 | medium | vi | service_unavailable | {'component': None, 'level': 'WARN', 'time_range': None} | 80 | 80 | 0 | exception while serving=80, got exception while serving=80, exception=80 | yes |
| hdfs_q016 | medium | en | service_unavailable | {'component': 'dfs.DataNode$DataXceiver', 'level': 'WARN', 'time_range': None} | 80 | 80 | 0 | exception while serving=80, got exception while serving=80, exception=80 | yes |
| hdfs_q017 | medium | en | storage | {'component': 'dfs.FSNamesystem', 'level': None, 'time_range': None} | 659 | 659 | 0 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | yes |
| hdfs_q018 | medium | en | storage | {'component': 'dfs.DataNode$PacketResponder', 'level': None, 'time_range': None} | 603 | 603 | 0 | ~block=603, datanode=603, blk_=603, packetresponder=603 | yes |
| hdfs_q019 | medium | en | unknown | {'component': 'dfs.DataBlockScanner', 'level': None, 'time_range': None} | 20 | 0 | 0 |  | no |
| hdfs_q020 | medium | en | storage | {'component': 'dfs.FSDataset', 'level': None, 'time_range': None} | 263 | 263 | 0 | ~block=263, ~file=263, blk_=263, fsdataset=263 | yes |
| hdfs_q021 | medium | vi | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 80 | 0 | exception while serving=80, got exception while serving=80, exception=80 | yes |
| hdfs_q022 | medium | vi | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 2000 | 0 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | yes |
| hdfs_q023 | hard | vi | service_unavailable | {'component': None, 'level': 'WARN', 'time_range': None} | 80 | 80 | 0 | exception while serving=80, got exception while serving=80, exception=80 | yes |
| hdfs_q024 | hard | vi | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 2000 | 0 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | yes |
| hdfs_q025 | hard | vi | storage | {'component': 'dfs.FSNamesystem', 'level': None, 'time_range': None} | 659 | 659 | 0 | ~block=659, blk_=659, blockmap=314, addstoredblock=314, replica=1 | yes |
| hdfs_q026 | hard | vi | unknown | {'component': None, 'level': None, 'time_range': None} | 2000 | 80 | 0 | exception=160, level=WARN=80, \bwarn(?:ing)?\b=80, warn=80 | yes |
| hdfs_q027 | hard | en | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 80 | 0 | exception while serving=80, got exception while serving=80, exception=80 | yes |
| hdfs_q028 | hard | en | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 2000 | 0 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | yes |
| hdfs_q029 | medium | vi | service_unavailable | {'component': None, 'level': None, 'time_range': None} | 2000 | 80 | 0 | exception while serving=80, got exception while serving=80, exception=80 | yes |
| hdfs_q030 | medium | vi | storage | {'component': None, 'level': None, 'time_range': None} | 2000 | 2000 | 0 | blk_=2000, ~block=1920, datanode=1059, packetresponder=603, blockmap=314 | yes |
