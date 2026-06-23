# Qrels Quality Audit: hdfs

- Review rows: 797
- Positive rows suspected: 200

## Per Query Label Counts

| query_id | positive | hard_negative | uncertain | patterns |
| --- | --- | --- | --- | --- |
| hdfs_q001 | 20 | 10 | 0 | exception while serving=20, got exception while serving=20, ~exception=20 |
| hdfs_q002 | 20 | 0 | 5 | datanode=20, block+issue=20, ~blk_=20 |
| hdfs_q003 | 20 | 0 | 5 | datanode=20, block+issue=20, ~blk_=20 |
| hdfs_q004 | 20 | 10 | 5 | ~warn=20, ~exception=20 |
| hdfs_q005 | 20 | 10 | 0 | exception while serving=20, got exception while serving=20, ~exception=20 |
| hdfs_q006 | 20 | 0 | 5 | datanode=20, block+issue=20, ~blk_=20 |
| hdfs_q007 | 20 | 10 | 5 | exception while serving=20, got exception while serving=20, ~exception=20 |
| hdfs_q008 | 20 | 0 | 5 | datanode=20, block+issue=20, ~blk_=20 |
| hdfs_q009 | 20 | 0 | 5 | datanode=20, packetresponder=20, ~block=20, ~blk_=20, ~block-only=20 |
| hdfs_q010 | 20 | 0 | 5 | blockmap=20, addstoredblock=20, ~block=20, ~blk_=20, ~block-only=20 |
| hdfs_q011 | 20 | 0 | 5 | blockmap=20, addstoredblock=20, ~block=20, ~blk_=20, ~block-only=20 |
| hdfs_q012 | 20 | 10 | 0 | exception while serving=20, got exception while serving=20, ~exception=20 |
| hdfs_q013 | 0 | 0 | 0 |  |
| hdfs_q014 | 20 | 0 | 5 | fsdataset=20, ~block=20, ~blk_=20, ~file=20, ~block-only=20 |
| hdfs_q015 | 20 | 10 | 5 | exception while serving=20, got exception while serving=20, ~exception=20 |
| hdfs_q016 | 20 | 10 | 0 | exception while serving=20, got exception while serving=20, ~exception=20 |
| hdfs_q017 | 20 | 0 | 5 | blockmap=20, addstoredblock=20, ~block=20, ~blk_=20, ~block-only=20 |
| hdfs_q018 | 20 | 0 | 5 | datanode=20, packetresponder=20, ~block=20, ~blk_=20, ~block-only=20 |
| hdfs_q019 | 0 | 0 | 0 |  |
| hdfs_q020 | 20 | 0 | 5 | fsdataset=20, ~block=20, ~blk_=20, ~file=20, ~block-only=20 |
| hdfs_q021 | 20 | 10 | 0 | exception while serving=20, got exception while serving=20, ~exception=20 |
| hdfs_q022 | 20 | 0 | 5 | datanode=20, block+issue=20, ~blk_=20 |
| hdfs_q023 | 20 | 10 | 5 | exception while serving=20, got exception while serving=20, ~exception=20 |
| hdfs_q024 | 20 | 0 | 5 | datanode=20, block+issue=20, ~blk_=20 |
| hdfs_q025 | 20 | 0 | 5 | blockmap=20, addstoredblock=20, ~block=20, ~blk_=20, ~block-only=20 |
| hdfs_q026 | 20 | 10 | 5 | ~warn=20, ~exception=20 |
| hdfs_q027 | 20 | 10 | 5 | exception while serving=20, got exception while serving=20, ~exception=20 |
| hdfs_q028 | 20 | 0 | 5 | datanode=20, block+issue=20, ~blk_=20 |
| hdfs_q029 | 20 | 10 | 5 | exception while serving=20, got exception while serving=20, ~exception=20 |
| hdfs_q030 | 20 | 0 | 5 | datanode=20, block+issue=20, ~blk_=20 |


## Top Suspected False Positives

| query_id | category | reason | message | suggestion |
| --- | --- | --- | --- | --- |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.30.85:50010:Got exception while serving blk_-2918118818249673980 to /10.251.90.64: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.126.255:50010:Got exception while serving blk_8376667364205250596 to /10.251.91.159: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.123.132:50010:Got exception while serving blk_3763728533434719668 to /10.251.38.214: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.250.13.188:50010:Got exception while serving blk_6241141267506413726 to /10.251.194.245: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.199.19:50010:Got exception while serving blk_8466246428293623262 to /10.251.106.37: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.250.9.207:50010:Got exception while serving blk_-3140754468249228022 to /10.250.9.207: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.202.134:50010:Got exception while serving blk_3441699978641526775 to /10.251.126.5: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.250.14.196:50010:Got exception while serving blk_-305633040016166849 to /10.251.38.53: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.107.227:50010:Got exception while serving blk_-6290631608800952376 to /10.251.109.209: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.90.64:50010:Got exception while serving blk_-4841792440390267307 to /10.251.90.239: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.250.10.144:50010:Got exception while serving blk_5126469776250053435 to /10.250.11.100: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.71.146:50010:Got exception while serving blk_-2032740670708110312 to /10.251.197.161: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.67.113:50010:Got exception while serving blk_-62891505109755100 to /10.250.7.96: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.74.79:50010:Got exception while serving blk_2244903517044280975 to /10.251.74.134: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.214.112:50010:Got exception while serving blk_5905933788014151041 to /10.251.214.112: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.43.210:50010:Got exception while serving blk_2969087638814291714 to /10.251.199.86: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.126.255:50010:Got exception while serving blk_2879780987351022871 to /10.251.39.144: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.73.220:50010:Got exception while serving blk_4934527196392001803 to /10.251.203.246: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.73.188:50010:Got exception while serving blk_7517964792804498202 to /10.250.6.191: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q004 | unknown | broad unknown positive: generic error/warn/exception requires review | 10.251.35.1:50010:Got exception while serving blk_7940316270494947483 to /10.251.122.38: | Keep needs_review=true; avoid confident positives from generic error/warn only. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | PacketResponder 1 for block blk_38865049064139660 terminating | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | PacketResponder 0 for block blk_-6952295868487656571 terminating | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | PacketResponder 2 for block blk_8229193803249955061 terminating | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | PacketResponder 2 for block blk_-6670958622368987959 terminating | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | PacketResponder 2 for block blk_572492839287299681 terminating | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_3587508140051953248 of size 67108864 from /10.251.42.84 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_5402003568334525940 of size 67108864 from /10.251.214.112 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | PacketResponder 1 for block blk_5017373558217225674 terminating | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_9212264480425680329 of size 67108864 from /10.251.123.1 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_-5704899712662113150 of size 67108864 from /10.251.91.229 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_-5861636720645142679 of size 67108864 from /10.251.70.211 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_8291449241650212794 of size 67108864 from /10.251.89.155 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_-5974833545991408899 of size 67108864 from /10.251.31.180 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_6921674711959888070 of size 67108864 from /10.251.65.203 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_-7526945448667194862 of size 67108864 from /10.251.203.80 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_-2094397855762091248 of size 67108864 from /10.251.126.83 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_-8523968015014407246 of size 67108864 from /10.251.214.225 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_4755566011267050000 of size 67108864 from /10.251.75.79 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_-3909548841543565741 of size 3542967 from /10.251.195.33 | Require storage issue context, not block-only matches. |
| hdfs_q009 | storage | storage false positive risk: block-only or normal storage event | Received block blk_8829027411458566099 of size 67108864 from /10.251.38.214 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.73.220:50010 is added to blk_7128370237687728475 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.43.115:50010 is added to blk_3050920587428079149 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.203.80:50010 is added to blk_7888946331804732825 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.250.11.85:50010 is added to blk_2377150260128098806 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.110.8:50010 is added to blk_8015913224713045110 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.111.130:50010 is added to blk_4568434182693165548 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.74.79:50010 is added to blk_-4794867979917102672 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.38.197:50010 is added to blk_8763662564934652249 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.74.134:50010 is added to blk_7453815855294711849 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.250.7.244:50010 is added to blk_5165786360127153975 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.250.6.191:50010 is added to blk_673825774073966710 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.89.155:50010 is added to blk_8181993091797661153 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.106.50:50010 is added to blk_-29548654251973735 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.111.228:50010 is added to blk_-2480595760294717232 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.202.134:50010 is added to blk_2113880130496815041 size 3549917 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.110.8:50010 is added to blk_-1661553043410372067 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.106.50:50010 is added to blk_-2530087534157630851 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.198.196:50010 is added to blk_427714267500527780 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.107.19:50010 is added to blk_6093743385844975689 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q010 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.110.68:50010 is added to blk_1636660629634995787 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.73.220:50010 is added to blk_7128370237687728475 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.43.115:50010 is added to blk_3050920587428079149 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.203.80:50010 is added to blk_7888946331804732825 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.250.11.85:50010 is added to blk_2377150260128098806 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.110.8:50010 is added to blk_8015913224713045110 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.111.130:50010 is added to blk_4568434182693165548 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.74.79:50010 is added to blk_-4794867979917102672 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.38.197:50010 is added to blk_8763662564934652249 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.74.134:50010 is added to blk_7453815855294711849 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.250.7.244:50010 is added to blk_5165786360127153975 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.250.6.191:50010 is added to blk_673825774073966710 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.89.155:50010 is added to blk_8181993091797661153 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.106.50:50010 is added to blk_-29548654251973735 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.111.228:50010 is added to blk_-2480595760294717232 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.202.134:50010 is added to blk_2113880130496815041 size 3549917 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.110.8:50010 is added to blk_-1661553043410372067 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.106.50:50010 is added to blk_-2530087534157630851 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.198.196:50010 is added to blk_427714267500527780 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.107.19:50010 is added to blk_6093743385844975689 size 67108864 | Require storage issue context, not block-only matches. |
| hdfs_q011 | storage | storage false positive risk: block-only or normal storage event | BLOCK* NameSystem.addStoredBlock: blockMap updated: 10.251.110.68:50010 is added to blk_1636660629634995787 size 67108864 | Require storage issue context, not block-only matches. |
