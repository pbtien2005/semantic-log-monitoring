# Embedding Benchmark Report: openstack

This benchmark uses qrels_silver.jsonl as silver labels. Labels have not been fully manual-reviewed.

## Dataset
- Logs: 2000
- Queries evaluated: 17
- Queries skipped because they have no usable positive labels: 13

## Model Comparison
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3-Embedding-0.6B | 17 | 13 | 0.2353 | 0.1849 | 0.1559 | 236.2383 |
| jinaai/jina-embeddings-v3 | 17 | 13 | 0.3529 | 0.2549 | 0.1647 | 715.3133 |

## Highlights
- Best Hit@5: jinaai/jina-embeddings-v3 (0.3529)
- Best MRR@10: jinaai/jina-embeddings-v3 (0.2549)
- Fastest average query latency: Qwen/Qwen3-Embedding-0.6B (236.24 ms)

## Review Subsets
| model_name | subset | num_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3-Embedding-0.6B | all | 17 | 0.2353 | 0.1849 | 0.1559 | 236.2383 |
| Qwen/Qwen3-Embedding-0.6B | needs_review=false | 6 | 0.3333 | 0.1667 | 0.0833 | 232.8417 |
| Qwen/Qwen3-Embedding-0.6B | needs_review=true | 11 | 0.1818 | 0.1948 | 0.1955 | 238.0911 |
| jinaai/jina-embeddings-v3 | all | 17 | 0.3529 | 0.2549 | 0.1647 | 715.3133 |
| jinaai/jina-embeddings-v3 | needs_review=false | 6 | 0.3333 | 0.2222 | 0.0750 | 704.3171 |
| jinaai/jina-embeddings-v3 | needs_review=true | 11 | 0.3636 | 0.2727 | 0.2136 | 721.3112 |

## Skipped Queries
openstack_q003, openstack_q004, openstack_q008, openstack_q011, openstack_q012, openstack_q015, openstack_q017, openstack_q019, openstack_q021, openstack_q022, openstack_q025, openstack_q026, openstack_q030

## Skipped Models
- Alibaba-NLP/gte-Qwen2-1.5B-instruct: AttributeError: 'DynamicCache' object has no attribute 'get_usable_length'
