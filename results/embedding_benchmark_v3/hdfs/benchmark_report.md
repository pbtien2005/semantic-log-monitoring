# Embedding Benchmark Report: hdfs

This benchmark uses qrels_silver.jsonl as silver labels. Labels have not been fully manual-reviewed.

## Dataset
- Logs: 2000
- Queries evaluated: 22
- Queries skipped because they have no usable positive labels: 8

## Model Comparison
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3-Embedding-0.6B | 22 | 8 | 0.1364 | 0.1182 | 0.0159 | 249.6035 |
| jinaai/jina-embeddings-v3 | 22 | 8 | 0.0909 | 0.0909 | 0.0045 | 1070.4247 |

## Highlights
- Best Hit@5: Qwen/Qwen3-Embedding-0.6B (0.1364)
- Best MRR@10: Qwen/Qwen3-Embedding-0.6B (0.1182)
- Fastest average query latency: Qwen/Qwen3-Embedding-0.6B (249.60 ms)

## Review Subsets
| model_name | subset | num_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3-Embedding-0.6B | all | 22 | 0.1364 | 0.1182 | 0.0159 | 249.6035 |
| Qwen/Qwen3-Embedding-0.6B | needs_review=false | 5 | 0.2000 | 0.1200 | 0.0500 | 269.0414 |
| Qwen/Qwen3-Embedding-0.6B | needs_review=true | 17 | 0.1176 | 0.1176 | 0.0059 | 243.8865 |
| jinaai/jina-embeddings-v3 | all | 22 | 0.0909 | 0.0909 | 0.0045 | 1070.4247 |
| jinaai/jina-embeddings-v3 | needs_review=false | 5 | 0.0000 | 0.0000 | 0.0000 | 1411.7237 |
| jinaai/jina-embeddings-v3 | needs_review=true | 17 | 0.1176 | 0.1176 | 0.0059 | 970.0426 |

## Skipped Queries
hdfs_q004, hdfs_q009, hdfs_q013, hdfs_q014, hdfs_q018, hdfs_q019, hdfs_q020, hdfs_q026

## Skipped Models
- Alibaba-NLP/gte-Qwen2-1.5B-instruct: AttributeError: 'DynamicCache' object has no attribute 'get_usable_length'
