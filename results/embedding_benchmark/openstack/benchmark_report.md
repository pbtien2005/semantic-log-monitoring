# Embedding Benchmark Report: openstack

This benchmark uses qrels_silver.jsonl as silver labels. Labels have not been fully manual-reviewed.

## Dataset
- Logs: 2000
- Queries evaluated: 17
- Queries skipped because they have no usable positive labels: 13

## Model Comparison
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | 17 | 13 | 0.1765 | 0.1471 | 0.1353 | 1.5952 |
| sentence-transformers/all-MiniLM-L6-v2 | 17 | 13 | 0.0000 | 0.0074 | 0.0588 | 17.4254 |
| intfloat/multilingual-e5-base | 17 | 13 | 0.2941 | 0.2549 | 0.1647 | 63.5999 |
| BAAI/bge-base-en-v1.5 | 17 | 13 | 0.0000 | 0.0182 | 0.0088 | 59.7229 |

## Highlights
- Best Hit@5: intfloat/multilingual-e5-base (0.2941)
- Best MRR@10: intfloat/multilingual-e5-base (0.2549)
- Fastest average query latency: bm25 (1.60 ms)

## BM25 vs Semantic Search
Best semantic model beats BM25 by 0.1176 Hit@5 on this silver set.

## Review Subsets
| model_name | subset | num_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | all | 17 | 0.1765 | 0.1471 | 0.1353 | 1.5952 |
| bm25 | needs_review=false | 6 | 0.1667 | 0.0833 | 0.0500 | 1.0267 |
| bm25 | needs_review=true | 11 | 0.1818 | 0.1818 | 0.1818 | 1.9054 |
| sentence-transformers/all-MiniLM-L6-v2 | all | 17 | 0.0000 | 0.0074 | 0.0588 | 17.4254 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=false | 6 | 0.0000 | 0.0000 | 0.0000 | 18.0470 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=true | 11 | 0.0000 | 0.0114 | 0.0909 | 17.0863 |
| intfloat/multilingual-e5-base | all | 17 | 0.2941 | 0.2549 | 0.1647 | 63.5999 |
| intfloat/multilingual-e5-base | needs_review=false | 6 | 0.1667 | 0.1667 | 0.0417 | 63.5484 |
| intfloat/multilingual-e5-base | needs_review=true | 11 | 0.3636 | 0.3030 | 0.2318 | 63.6279 |
| BAAI/bge-base-en-v1.5 | all | 17 | 0.0000 | 0.0182 | 0.0088 | 59.7229 |
| BAAI/bge-base-en-v1.5 | needs_review=false | 6 | 0.0000 | 0.0278 | 0.0083 | 57.8844 |
| BAAI/bge-base-en-v1.5 | needs_review=true | 11 | 0.0000 | 0.0130 | 0.0091 | 60.7258 |

## Skipped Queries
openstack_q003, openstack_q004, openstack_q008, openstack_q011, openstack_q012, openstack_q015, openstack_q017, openstack_q019, openstack_q021, openstack_q022, openstack_q025, openstack_q026, openstack_q030
