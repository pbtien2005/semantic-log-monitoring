# Embedding Benchmark Report: apache

This benchmark uses qrels_silver.jsonl as silver labels. Labels have not been fully manual-reviewed.

## Dataset
- Logs: 2000
- Queries evaluated: 22
- Queries skipped because they have no usable positive labels: 8

## Model Comparison
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3-Embedding-0.6B | 22 | 8 | 0.5000 | 0.4167 | 0.1250 | 254.0012 |
| jinaai/jina-embeddings-v3 | 22 | 8 | 0.4545 | 0.4369 | 0.1205 | 851.8791 |

## Highlights
- Best Hit@5: Qwen/Qwen3-Embedding-0.6B (0.5000)
- Best MRR@10: jinaai/jina-embeddings-v3 (0.4369)
- Fastest average query latency: Qwen/Qwen3-Embedding-0.6B (254.00 ms)

## Review Subsets
| model_name | subset | num_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3-Embedding-0.6B | all | 22 | 0.5000 | 0.4167 | 0.1250 | 254.0012 |
| Qwen/Qwen3-Embedding-0.6B | needs_review=false | 16 | 0.5625 | 0.4792 | 0.1250 | 254.2626 |
| Qwen/Qwen3-Embedding-0.6B | needs_review=true | 6 | 0.3333 | 0.2500 | 0.1250 | 253.3040 |
| jinaai/jina-embeddings-v3 | all | 22 | 0.4545 | 0.4369 | 0.1205 | 851.8791 |
| jinaai/jina-embeddings-v3 | needs_review=false | 16 | 0.4375 | 0.4132 | 0.1156 | 883.2525 |
| jinaai/jina-embeddings-v3 | needs_review=true | 6 | 0.5000 | 0.5000 | 0.1333 | 768.2168 |

## Skipped Queries
apache_q003, apache_q011, apache_q012, apache_q015, apache_q018, apache_q019, apache_q026, apache_q030

## Skipped Models
- Alibaba-NLP/gte-Qwen2-1.5B-instruct: AttributeError: 'DynamicCache' object has no attribute 'get_usable_length'
