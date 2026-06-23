# Embedding Benchmark Report: hdfs

This benchmark uses qrels_silver.jsonl as silver labels. Labels have not been fully manual-reviewed.

## Dataset
- Logs: 2000
- Queries evaluated: 22
- Queries skipped because they have no usable positive labels: 8

## Model Comparison
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | 22 | 8 | 0.1818 | 0.1477 | 0.0864 | 1.8951 |
| sentence-transformers/all-MiniLM-L6-v2 | 22 | 8 | 0.0455 | 0.0455 | 0.0023 | 14.5126 |
| intfloat/multilingual-e5-base | 22 | 8 | 0.1364 | 0.1153 | 0.0114 | 49.6658 |
| BAAI/bge-base-en-v1.5 | 22 | 8 | 0.1364 | 0.1364 | 0.0068 | 52.4920 |
| intfloat/multilingual-e5-large | 22 | 8 | 0.2273 | 0.1682 | 0.0591 | 178.9361 |
| BAAI/bge-m3 | 22 | 8 | 0.0455 | 0.0455 | 0.0023 | 146.5466 |
| mixedbread-ai/mxbai-embed-large-v1 | 22 | 8 | 0.0909 | 0.0909 | 0.0045 | 145.5597 |
| nomic-ai/nomic-embed-text-v1.5 | 22 | 8 | 0.1364 | 0.1061 | 0.0136 | 58.6309 |

## Highlights
- Best Hit@5: intfloat/multilingual-e5-large (0.2273)
- Best MRR@10: intfloat/multilingual-e5-large (0.1682)
- Fastest average query latency: bm25 (1.90 ms)

## BM25 vs Semantic Search
Best semantic model beats BM25 by 0.0455 Hit@5 on this silver set.

## Review Subsets
| model_name | subset | num_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | all | 22 | 0.1818 | 0.1477 | 0.0864 | 1.8951 |
| bm25 | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 1.8815 |
| bm25 | needs_review=true | 17 | 0.2353 | 0.1912 | 0.1118 | 1.8990 |
| sentence-transformers/all-MiniLM-L6-v2 | all | 22 | 0.0455 | 0.0455 | 0.0023 | 14.5126 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 16.5419 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=true | 17 | 0.0588 | 0.0588 | 0.0029 | 13.9158 |
| intfloat/multilingual-e5-base | all | 22 | 0.1364 | 0.1153 | 0.0114 | 49.6658 |
| intfloat/multilingual-e5-base | needs_review=false | 5 | 0.0000 | 0.0571 | 0.0200 | 54.7184 |
| intfloat/multilingual-e5-base | needs_review=true | 17 | 0.1765 | 0.1324 | 0.0088 | 48.1798 |
| BAAI/bge-base-en-v1.5 | all | 22 | 0.1364 | 0.1364 | 0.0068 | 52.4920 |
| BAAI/bge-base-en-v1.5 | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 63.6677 |
| BAAI/bge-base-en-v1.5 | needs_review=true | 17 | 0.1765 | 0.1765 | 0.0088 | 49.2050 |
| intfloat/multilingual-e5-large | all | 22 | 0.2273 | 0.1682 | 0.0591 | 178.9361 |
| intfloat/multilingual-e5-large | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 193.0096 |
| intfloat/multilingual-e5-large | needs_review=true | 17 | 0.2941 | 0.2176 | 0.0765 | 174.7968 |
| BAAI/bge-m3 | all | 22 | 0.0455 | 0.0455 | 0.0023 | 146.5466 |
| BAAI/bge-m3 | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 161.5930 |
| BAAI/bge-m3 | needs_review=true | 17 | 0.0588 | 0.0588 | 0.0029 | 142.1212 |
| mixedbread-ai/mxbai-embed-large-v1 | all | 22 | 0.0909 | 0.0909 | 0.0045 | 145.5597 |
| mixedbread-ai/mxbai-embed-large-v1 | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 137.7165 |
| mixedbread-ai/mxbai-embed-large-v1 | needs_review=true | 17 | 0.1176 | 0.1176 | 0.0059 | 147.8665 |
| nomic-ai/nomic-embed-text-v1.5 | all | 22 | 0.1364 | 0.1061 | 0.0136 | 58.6309 |
| nomic-ai/nomic-embed-text-v1.5 | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 58.0702 |
| nomic-ai/nomic-embed-text-v1.5 | needs_review=true | 17 | 0.1765 | 0.1373 | 0.0176 | 58.7958 |

## Skipped Queries
hdfs_q004, hdfs_q009, hdfs_q013, hdfs_q014, hdfs_q018, hdfs_q019, hdfs_q020, hdfs_q026
