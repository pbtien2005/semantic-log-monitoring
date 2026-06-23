# Embedding Benchmark Report: hdfs

This benchmark uses qrels_silver.jsonl as silver labels. Labels have not been fully manual-reviewed.

## Dataset
- Logs: 2000
- Queries evaluated: 22
- Queries skipped because they have no usable positive labels: 8

## Model Comparison
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | 22 | 8 | 0.1818 | 0.1477 | 0.0864 | 2.8790 |
| sentence-transformers/all-MiniLM-L6-v2 | 22 | 8 | 0.0455 | 0.0455 | 0.0023 | 21.6036 |
| intfloat/multilingual-e5-base | 22 | 8 | 0.1364 | 0.1153 | 0.0114 | 63.1912 |
| BAAI/bge-base-en-v1.5 | 22 | 8 | 0.1364 | 0.1364 | 0.0068 | 67.7805 |

## Highlights
- Best Hit@5: bm25 (0.1818)
- Best MRR@10: bm25 (0.1477)
- Fastest average query latency: bm25 (2.88 ms)

## BM25 vs Semantic Search
BM25 beats the best semantic model by 0.0455 Hit@5 on this silver set.

## Review Subsets
| model_name | subset | num_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | all | 22 | 0.1818 | 0.1477 | 0.0864 | 2.8790 |
| bm25 | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 2.5660 |
| bm25 | needs_review=true | 17 | 0.2353 | 0.1912 | 0.1118 | 2.9711 |
| sentence-transformers/all-MiniLM-L6-v2 | all | 22 | 0.0455 | 0.0455 | 0.0023 | 21.6036 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 20.9140 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=true | 17 | 0.0588 | 0.0588 | 0.0029 | 21.8064 |
| intfloat/multilingual-e5-base | all | 22 | 0.1364 | 0.1153 | 0.0114 | 63.1912 |
| intfloat/multilingual-e5-base | needs_review=false | 5 | 0.0000 | 0.0571 | 0.0200 | 69.1834 |
| intfloat/multilingual-e5-base | needs_review=true | 17 | 0.1765 | 0.1324 | 0.0088 | 61.4288 |
| BAAI/bge-base-en-v1.5 | all | 22 | 0.1364 | 0.1364 | 0.0068 | 67.7805 |
| BAAI/bge-base-en-v1.5 | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 74.3965 |
| BAAI/bge-base-en-v1.5 | needs_review=true | 17 | 0.1765 | 0.1765 | 0.0088 | 65.8347 |

## Skipped Queries
hdfs_q004, hdfs_q009, hdfs_q013, hdfs_q014, hdfs_q018, hdfs_q019, hdfs_q020, hdfs_q026
