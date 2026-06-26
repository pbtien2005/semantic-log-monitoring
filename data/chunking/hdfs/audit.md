# Chunk Audit: hdfs

## Counts

| metric | value |
| --- | --- |
| logs | 2000 |
| line_chunks | 2000 |
| template_chunks | 15 |
| line_chunks_match_logs | PASS |
| unique_line_chunk_ids | PASS (2000) |
| unique_template_chunk_ids | PASS (15) |
| singleton_templates | 2 (13.3%) |

## Filter Field Null Rates

| field | present | missing | missing_rate |
| --- | --- | --- | --- |
| component | 2000 | 0 | 0.0% |
| level | 2000 | 0 | 0.0% |
| timestamp_ms | 2000 | 0 | 0.0% |
| request_id | 0 | 2000 | 100.0% |
| instance_id | 0 | 2000 | 100.0% |
| block_id | 2000 | 0 | 0.0% |
| ip | 1291 | 709 | 35.4% |
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
| 314 | dfs.FSNamesystem | INFO | BLOCK* NameSystem.addStoredBlock: blockMap updated: <ip_port> is added to <block_id> size <num> |
| 311 | dfs.DataNode$PacketResponder | INFO | PacketResponder <num> for block <block_id> terminating |
| 292 | dfs.DataNode$DataXceiver | INFO | Receiving block <block_id> src: /<ip_port> dest: /<ip_port> |
| 292 | dfs.DataNode$PacketResponder | INFO | Received block <block_id> of size <num> from /<ip> |
| 263 | dfs.FSDataset | INFO | Deleting block <block_id> file <path>/<block_id> |
| 224 | dfs.FSNamesystem | INFO | BLOCK* NameSystem.delete: <block_id> is added to invalidSet of <ip_port> |
| 115 | dfs.FSNamesystem | INFO | BLOCK* NameSystem.allocateBlock: <path> <block_id> |
| 80 | dfs.DataNode$DataXceiver | INFO | <ip_port> Served block <block_id> to /<ip> |
| 80 | dfs.DataNode$DataXceiver | WARN | <ip_port>:Got exception while serving <block_id> to /<ip>: |
| 20 | dfs.DataBlockScanner | INFO | Verification succeeded for <block_id> |

## Suspicious Template Samples

| reason | chunk_id | template |
| --- | --- | --- |
| singleton | template::hdfs::9f941364b4f1d9e3 | <ip_port> Starting thread to transfer block <block_id> to <ip_port> |
| too_few_semantic_tokens | template::hdfs::8c814ef5ad0ce9cb | BLOCK* NameSystem.allocateBlock: <path> <block_id> |
| singleton | template::hdfs::842e5b347f6dfa2a | BLOCK* ask <ip_port> to replicate <block_id> to datanode(s) <ip_port> |

## Line Chunk Samples

| chunk_id | embed_text |
| --- | --- |
| line::hdfs:39e541f9d2f9c6cc582f | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>template: PacketResponder <num> for block <block_id> terminating<br>signals: datanode$packetresponder dfs has_block_id hdfs_storage storage |
| line::hdfs:532c93d3257d1eacc5e0 | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>template: PacketResponder <num> for block <block_id> terminating<br>signals: datanode$packetresponder dfs has_block_id hdfs_storage storage |
| line::hdfs:a8f5d6f342124fc3d416 | dataset: hdfs<br>component: dfs.FSNamesystem<br>level: INFO<br>template: BLOCK* NameSystem.addStoredBlock: blockMap updated: <ip_port> is added to <block_id> size <num><br>signals: dfs fsnamesystem has_block_id has_ip hdfs_storage storage |
| line::hdfs:1a72ae8b75722543b9c2 | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>template: PacketResponder <num> for block <block_id> terminating<br>signals: datanode$packetresponder dfs has_block_id hdfs_storage storage |
| line::hdfs:4d4e33be747c08c311cc | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>template: PacketResponder <num> for block <block_id> terminating<br>signals: datanode$packetresponder dfs has_block_id hdfs_storage storage |
| line::hdfs:d42247388ac928be75ee | dataset: hdfs<br>component: dfs.FSNamesystem<br>level: INFO<br>template: BLOCK* NameSystem.addStoredBlock: blockMap updated: <ip_port> is added to <block_id> size <num><br>signals: dfs fsnamesystem has_block_id has_ip hdfs_storage storage |
| line::hdfs:8b63eaef3c6f494c2b40 | dataset: hdfs<br>component: dfs.FSNamesystem<br>level: INFO<br>template: BLOCK* NameSystem.addStoredBlock: blockMap updated: <ip_port> is added to <block_id> size <num><br>signals: dfs fsnamesystem has_block_id has_ip hdfs_storage storage |
| line::hdfs:0edf450a2815ddbe2d0b | dataset: hdfs<br>component: dfs.FSNamesystem<br>level: INFO<br>template: BLOCK* NameSystem.addStoredBlock: blockMap updated: <ip_port> is added to <block_id> size <num><br>signals: dfs fsnamesystem has_block_id has_ip hdfs_storage storage |
| line::hdfs:5759afd800d043cb326d | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>template: PacketResponder <num> for block <block_id> terminating<br>signals: datanode$packetresponder dfs has_block_id hdfs_storage storage |
| line::hdfs:88fff082b83fb4dba555 | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>template: Received block <block_id> of size <num> from /<ip><br>signals: datanode$packetresponder dfs has_block_id has_ip hdfs_storage storage |
