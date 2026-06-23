# Unsupported Query Analysis: hdfs

- Query bank entries: 30
- Unsupported queries under current rules: 2
- Existing validation report found: yes

## Unsupported Queries

| query_id | category | filters | filtered_logs | candidate_patterns | frequent_terms | sample_messages | suggestion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hdfs_q013 | unknown | {'component': 'dfs.DataBlockScanner', 'level': None, 'time_range': None} | 20 | verification succeeded=20 | dfs.datablockscanner=40, verification=40, succeeded=40, blk_-4980916519894289629=2, blk_-2827716238972737794=2, blk_-1547954353065580372=2, blk_6996194389878584395=2, blk_3141363517520802396=2 | Verification succeeded for blk_-4980916519894289629 / Verification succeeded for blk_-2827716238972737794 / Verification succeeded for blk_-1547954353065580372 | Review adding or strengthening pattern(s): verification succeeded. |
| hdfs_q019 | unknown | {'component': 'dfs.DataBlockScanner', 'level': None, 'time_range': None} | 20 | verification succeeded=20 | dfs.datablockscanner=40, verification=40, succeeded=40, blk_-4980916519894289629=2, blk_-2827716238972737794=2, blk_-1547954353065580372=2, blk_6996194389878584395=2, blk_3141363517520802396=2 | Verification succeeded for blk_-4980916519894289629 / Verification succeeded for blk_-2827716238972737794 / Verification succeeded for blk_-1547954353065580372 | Review adding or strengthening pattern(s): verification succeeded. |
