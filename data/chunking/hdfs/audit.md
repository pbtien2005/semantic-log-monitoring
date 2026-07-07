# Chunk Audit: hdfs

## Counts

| metric | value |
| --- | --- |
| logs | 2000 |
| line_chunks | 2000 |
| catalog_templates | 30 |
| line_chunks_match_logs | PASS |
| unique_line_chunk_ids | PASS (2000) |
| unique_catalog_template_ids | PASS (30) |
| singleton_templates | 0 (0.0%) |

## Quality Metrics

| metric | value |
| --- | --- |
| total_logs | 2000 |
| total_templates | 30 |
| matched_template_count | 2000 |
| unmatched_template_count | 0 |
| unmatched_template_ratio | 0.0% |
| templates_never_seen | 16 |
| ambiguous_match_count | 0 |
| entity_extraction_coverage | 100.0% |
| unique_template_ratio | 1.5% |
| singleton_template_ratio | 0.0% |
| top_20_template_coverage | 0.0% |
| unknown_signal_ratio | 4.0% |
| weak_signal_ratio | 99.0% |
| avg_embed_text_length | 393.3 |
| templates_with_real_id_leak | 0 |
| templates_over_normalized | 9 |

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

## Match Count By Template

| template_id | match_count |
| --- | --- |
| hdfs::E26 | 314 |
| hdfs::E11 | 311 |
| hdfs::E9 | 292 |
| hdfs::E5 | 292 |
| hdfs::E21 | 263 |
| hdfs::E23 | 224 |
| hdfs::E22 | 115 |
| hdfs::E3 | 80 |
| hdfs::E4 | 80 |
| hdfs::E2 | 20 |

## Top Unmatched Normalized Templates

| count | normalized_template |
| --- | --- |

## Catalog Templates Never Seen

| template_id |
| --- |
| hdfs::E1 |
| hdfs::E7 |
| hdfs::E8 |
| hdfs::E10 |
| hdfs::E12 |
| hdfs::E13 |
| hdfs::E14 |
| hdfs::E15 |
| hdfs::E16 |
| hdfs::E17 |

## Top Catalog Templates

| priority | template |
| --- | --- |
| 100 | <*>:Exception writing block<*>to mirror<*> |
| 100 | <*>:Failed to transfer<*>to<*>got<*> |
| 100 | <*>:Transmitted block<*>to<*> |
| 100 | <*>Adding an already existing block<*> |
| 100 | <*>BLOCK* NameSystem<*>addStoredBlock: Redundant addStoredBlock request received for<*>on<*>size<*> |
| 100 | <*>BLOCK* NameSystem<*>addStoredBlock: addStoredBlock request received for<*>on<*>size<*>But it does not belong to any file. |
| 100 | <*>BLOCK* NameSystem<*>addStoredBlock: blockMap updated:<*>is added to<*>size<*> |
| 100 | <*>BLOCK* NameSystem<*>allocateBlock:<*> |
| 100 | <*>BLOCK* NameSystem<*>delete:<*>is added to invalidSet of<*> |
| 100 | <*>BLOCK* Removing block<*>from neededReplications as it does not belong to any file<*> |

## Suspicious Template Samples

| reason | chunk_id | template |
| --- | --- | --- |
| too_few_semantic_tokens | hdfs::E3 | <*>Served block<*>to<*> |
| too_few_semantic_tokens | hdfs::E5 | <*>Receiving block<*>src:<*>dest:<*> |
| too_few_semantic_tokens | hdfs::E7 | <*>writeBlock<*>received exception<*> |
| too_few_semantic_tokens | hdfs::E8 | <*>PacketResponder<*>for block<*>Interrupted<*> |
| too_few_semantic_tokens | hdfs::E10 | <*>PacketResponder<*>Exception<*> |
| too_few_semantic_tokens | hdfs::E16 | <*>:Transmitted block<*>to<*> |
| too_few_semantic_tokens | hdfs::E19 | <*>Reopen Block<*> |
| too_few_semantic_tokens | hdfs::E21 | <*>Deleting block<*>file<*> |
| too_few_semantic_tokens | hdfs::E22 | <*>BLOCK* NameSystem<*>allocateBlock:<*> |

## Line Chunk Samples

| chunk_id | embed_text |
| --- | --- |
| line::hdfs:39e541f9d2f9c6cc582f | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>event_type: packet_responder_block_lifecycle<br>event_family: hdfs_block_lifecycle<br>template: <*>PacketResponder <*> for block <*> terminating<*><br>intent: packet_responder_terminating block_pipeline_closed hdfs_block_lifecycle<br>signals: datanode$packetresponder datanode_storage dfs has_block_id hdfs_block_lifecycle hdfs_storage<br>message: PacketResponder 1 for block <block_id> terminating |
| line::hdfs:532c93d3257d1eacc5e0 | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>event_type: packet_responder_block_lifecycle<br>event_family: hdfs_block_lifecycle<br>template: <*>PacketResponder <*> for block <*> terminating<*><br>intent: packet_responder_terminating block_pipeline_closed hdfs_block_lifecycle<br>signals: datanode$packetresponder datanode_storage dfs has_block_id hdfs_block_lifecycle hdfs_storage<br>message: PacketResponder 0 for block <block_id> terminating |
| line::hdfs:a8f5d6f342124fc3d416 | dataset: hdfs<br>component: dfs.FSNamesystem<br>level: INFO<br>event_family: hdfs_block_lifecycle<br>template: <*>BLOCK* NameSystem<*>addStoredBlock: blockMap updated:<*>is added to<*>size<*><br>intent: namenode_blockmap_updated stored_block_registered hdfs_namespace_lifecycle<br>signals: dfs fsnamesystem has_block_id has_ip hdfs_block_lifecycle hdfs_storage<br>message: BLOCK* NameSystem.addStoredBlock: blockMap updated: <ip_port> is added to <block_id> size 67108864 |
| line::hdfs:1a72ae8b75722543b9c2 | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>event_type: packet_responder_block_lifecycle<br>event_family: hdfs_block_lifecycle<br>template: <*>PacketResponder <*> for block <*> terminating<*><br>intent: packet_responder_terminating block_pipeline_closed hdfs_block_lifecycle<br>signals: datanode$packetresponder datanode_storage dfs has_block_id hdfs_block_lifecycle hdfs_storage<br>message: PacketResponder 2 for block <block_id> terminating |
| line::hdfs:4d4e33be747c08c311cc | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>event_type: packet_responder_block_lifecycle<br>event_family: hdfs_block_lifecycle<br>template: <*>PacketResponder <*> for block <*> terminating<*><br>intent: packet_responder_terminating block_pipeline_closed hdfs_block_lifecycle<br>signals: datanode$packetresponder datanode_storage dfs has_block_id hdfs_block_lifecycle hdfs_storage<br>message: PacketResponder 2 for block <block_id> terminating |
| line::hdfs:d42247388ac928be75ee | dataset: hdfs<br>component: dfs.FSNamesystem<br>level: INFO<br>event_family: hdfs_block_lifecycle<br>template: <*>BLOCK* NameSystem<*>addStoredBlock: blockMap updated:<*>is added to<*>size<*><br>intent: namenode_blockmap_updated stored_block_registered hdfs_namespace_lifecycle<br>signals: dfs fsnamesystem has_block_id has_ip hdfs_block_lifecycle hdfs_storage<br>message: BLOCK* NameSystem.addStoredBlock: blockMap updated: <ip_port> is added to <block_id> size 67108864 |
| line::hdfs:8b63eaef3c6f494c2b40 | dataset: hdfs<br>component: dfs.FSNamesystem<br>level: INFO<br>event_family: hdfs_block_lifecycle<br>template: <*>BLOCK* NameSystem<*>addStoredBlock: blockMap updated:<*>is added to<*>size<*><br>intent: namenode_blockmap_updated stored_block_registered hdfs_namespace_lifecycle<br>signals: dfs fsnamesystem has_block_id has_ip hdfs_block_lifecycle hdfs_storage<br>message: BLOCK* NameSystem.addStoredBlock: blockMap updated: <ip_port> is added to <block_id> size 67108864 |
| line::hdfs:0edf450a2815ddbe2d0b | dataset: hdfs<br>component: dfs.FSNamesystem<br>level: INFO<br>event_family: hdfs_block_lifecycle<br>template: <*>BLOCK* NameSystem<*>addStoredBlock: blockMap updated:<*>is added to<*>size<*><br>intent: namenode_blockmap_updated stored_block_registered hdfs_namespace_lifecycle<br>signals: dfs fsnamesystem has_block_id has_ip hdfs_block_lifecycle hdfs_storage<br>message: BLOCK* NameSystem.addStoredBlock: blockMap updated: <ip_port> is added to <block_id> size 67108864 |
| line::hdfs:5759afd800d043cb326d | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>event_type: packet_responder_block_lifecycle<br>event_family: hdfs_block_lifecycle<br>template: <*>PacketResponder <*> for block <*> terminating<*><br>intent: packet_responder_terminating block_pipeline_closed hdfs_block_lifecycle<br>signals: datanode$packetresponder datanode_storage dfs has_block_id hdfs_block_lifecycle hdfs_storage<br>message: PacketResponder 2 for block <block_id> terminating |
| line::hdfs:88fff082b83fb4dba555 | dataset: hdfs<br>component: dfs.DataNode$PacketResponder<br>level: INFO<br>event_type: packet_responder_block_lifecycle<br>event_family: hdfs_block_lifecycle<br>template: <*>Received block<*>of size<*>from<*><br>intent: received_block block_receive_completed hdfs_block_lifecycle<br>signals: datanode$packetresponder datanode_storage dfs has_block_id has_ip hdfs_block_lifecycle hdfs_storage<br>message: Received block <block_id> of size 67108864 from /<ip> |
