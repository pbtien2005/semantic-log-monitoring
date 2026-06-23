# Qrels V2 Generation Report: hdfs

## Summary

- Positive labels v1 vs v2: 560 vs 364
- Hard negative labels v1 vs v2: 120 vs 300
- Uncertain labels v1 vs v2: 115 vs 180
- Queries with no positive: 8
- Queries needs_review: 25
- Avg positives/query v2: 12.13

## Top Positive Count Reductions

| query_id | v1_positive_count | v2_positive_count | delta |
| --- | --- | --- | --- |
| hdfs_q004 | 20 | 0 | -20 |
| hdfs_q009 | 20 | 0 | -20 |
| hdfs_q014 | 20 | 0 | -20 |
| hdfs_q018 | 20 | 0 | -20 |
| hdfs_q020 | 20 | 0 | -20 |
| hdfs_q026 | 20 | 0 | -20 |
| hdfs_q010 | 20 | 1 | -19 |
| hdfs_q011 | 20 | 1 | -19 |
| hdfs_q017 | 20 | 1 | -19 |
| hdfs_q025 | 20 | 1 | -19 |
| hdfs_q001 | 20 | 20 | 0 |
| hdfs_q002 | 20 | 20 | 0 |
| hdfs_q003 | 20 | 20 | 0 |
| hdfs_q005 | 20 | 20 | 0 |
| hdfs_q006 | 20 | 20 | 0 |


## Queries With No Positive

| query_id | category | query | review_reasons |
| --- | --- | --- | --- |
| hdfs_q004 | unknown | Cluster HDFS có dấu hiệu bất thường không? | category unknown, no positive above v2 threshold, has uncertain candidates |
| hdfs_q009 | storage | Kiểm tra các log PacketResponder kết thúc xử lý block. | no positive above v2 threshold, has uncertain candidates |
| hdfs_q013 | unknown | Có quá trình verification block nào thành công không? | category unknown, no positive above v2 threshold |
| hdfs_q014 | storage | Kiểm tra FSDataset trong các thao tác lưu trữ block. | no positive above v2 threshold, has uncertain candidates |
| hdfs_q018 | storage | Look for PacketResponder block completion events. | no positive above v2 threshold, has uncertain candidates |
| hdfs_q019 | unknown | Show block scanner verification records. | category unknown, no positive above v2 threshold |
| hdfs_q020 | storage | Which logs show storage activity inside HDFS dataset handling? | no positive above v2 threshold, has uncertain candidates |
| hdfs_q026 | unknown | Có log nào cho thấy block vẫn được verify dù cluster có cảnh báo không? | category unknown, hard query, no positive above v2 threshold, has uncertain candidates |


## Examples Fixed Or Downgraded

| query_id | label | reason | message |
| --- | --- | --- | --- |
| hdfs_q004 | uncertain | uncertain: weak pattern only | 10.251.30.85:50010:Got exception while serving blk_-2918118818249673980 to /10.251.90.64: |
| hdfs_q004 | uncertain | uncertain: weak pattern only | 10.251.126.255:50010:Got exception while serving blk_8376667364205250596 to /10.251.91.159: |
| hdfs_q004 | uncertain | uncertain: weak pattern only | 10.251.123.132:50010:Got exception while serving blk_3763728533434719668 to /10.251.38.214: |
| hdfs_q004 | uncertain | uncertain: weak pattern only | 10.250.13.188:50010:Got exception while serving blk_6241141267506413726 to /10.251.194.245: |
| hdfs_q004 | uncertain | uncertain: weak pattern only | 10.251.199.19:50010:Got exception while serving blk_8466246428293623262 to /10.251.106.37: |
| hdfs_q004 | uncertain | uncertain: weak pattern only | 10.250.9.207:50010:Got exception while serving blk_-3140754468249228022 to /10.250.9.207: |
| hdfs_q004 | uncertain | uncertain: weak pattern only | 10.251.202.134:50010:Got exception while serving blk_3441699978641526775 to /10.251.126.5: |
| hdfs_q004 | uncertain | uncertain: weak pattern only | 10.250.14.196:50010:Got exception while serving blk_-305633040016166849 to /10.251.38.53: |
| hdfs_q004 | uncertain | uncertain: weak pattern only | 10.251.107.227:50010:Got exception while serving blk_-6290631608800952376 to /10.251.109.209: |
| hdfs_q004 | uncertain | uncertain: weak pattern only | 10.251.90.64:50010:Got exception while serving blk_-4841792440390267307 to /10.251.90.239: |
| hdfs_q009 | uncertain | uncertain: HDFS block-only signal without failure context | PacketResponder 1 for block blk_38865049064139660 terminating |
| hdfs_q009 | uncertain | uncertain: HDFS block-only signal without failure context | PacketResponder 0 for block blk_-6952295868487656571 terminating |
| hdfs_q009 | uncertain | uncertain: HDFS block-only signal without failure context | PacketResponder 2 for block blk_8229193803249955061 terminating |
| hdfs_q009 | uncertain | uncertain: HDFS block-only signal without failure context | PacketResponder 2 for block blk_-6670958622368987959 terminating |
| hdfs_q009 | uncertain | uncertain: HDFS block-only signal without failure context | PacketResponder 2 for block blk_572492839287299681 terminating |
| hdfs_q009 | uncertain | uncertain: HDFS block-only signal without failure context | Received block blk_3587508140051953248 of size 67108864 from /10.251.42.84 |
| hdfs_q009 | uncertain | uncertain: HDFS block-only signal without failure context | Received block blk_5402003568334525940 of size 67108864 from /10.251.214.112 |
| hdfs_q009 | uncertain | uncertain: HDFS block-only signal without failure context | PacketResponder 1 for block blk_5017373558217225674 terminating |
| hdfs_q009 | uncertain | uncertain: HDFS block-only signal without failure context | Received block blk_9212264480425680329 of size 67108864 from /10.251.123.1 |
| hdfs_q009 | uncertain | uncertain: HDFS block-only signal without failure context | Received block blk_-5704899712662113150 of size 67108864 from /10.251.91.229 |
