# Embedding Benchmark Report: openstack

This benchmark uses qrels_silver.jsonl as silver labels. Labels have not been fully manual-reviewed.

## Dataset
- Logs: 2000
- Queries evaluated: 17
- Queries skipped because they have no usable positive labels: 13

## Model Comparison
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | 17 | 13 | 0.1765 | 0.1471 | 0.1353 | 1.2146 |
| sentence-transformers/all-MiniLM-L6-v2 | 17 | 13 | 0.0000 | 0.0074 | 0.0588 | 13.2072 |
| intfloat/multilingual-e5-base | 17 | 13 | 0.2941 | 0.2549 | 0.1647 | 52.0466 |
| BAAI/bge-base-en-v1.5 | 17 | 13 | 0.0000 | 0.0182 | 0.0088 | 53.0029 |
| intfloat/multilingual-e5-large | 17 | 13 | 0.2941 | 0.2176 | 0.1618 | 179.6141 |
| BAAI/bge-m3 | 17 | 13 | 0.3529 | 0.2794 | 0.1765 | 155.3714 |
| mixedbread-ai/mxbai-embed-large-v1 | 17 | 13 | 0.1765 | 0.1765 | 0.0735 | 139.1709 |
| nomic-ai/nomic-embed-text-v1.5 | 17 | 13 | 0.1176 | 0.0882 | 0.1294 | 64.0071 |

## Highlights
- Best Hit@5: BAAI/bge-m3 (0.3529)
- Best MRR@10: BAAI/bge-m3 (0.2794)
- Fastest average query latency: bm25 (1.21 ms)

## BM25 vs Semantic Search
Best semantic model beats BM25 by 0.1765 Hit@5 on this silver set.

## Review Subsets
| model_name | subset | num_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | all | 17 | 0.1765 | 0.1471 | 0.1353 | 1.2146 |
| bm25 | needs_review=false | 6 | 0.1667 | 0.0833 | 0.0500 | 0.6056 |
| bm25 | needs_review=true | 11 | 0.1818 | 0.1818 | 0.1818 | 1.5468 |
| sentence-transformers/all-MiniLM-L6-v2 | all | 17 | 0.0000 | 0.0074 | 0.0588 | 13.2072 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=false | 6 | 0.0000 | 0.0000 | 0.0000 | 13.4176 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=true | 11 | 0.0000 | 0.0114 | 0.0909 | 13.0925 |
| intfloat/multilingual-e5-base | all | 17 | 0.2941 | 0.2549 | 0.1647 | 52.0466 |
| intfloat/multilingual-e5-base | needs_review=false | 6 | 0.1667 | 0.1667 | 0.0417 | 55.1203 |
| intfloat/multilingual-e5-base | needs_review=true | 11 | 0.3636 | 0.3030 | 0.2318 | 50.3700 |
| BAAI/bge-base-en-v1.5 | all | 17 | 0.0000 | 0.0182 | 0.0088 | 53.0029 |
| BAAI/bge-base-en-v1.5 | needs_review=false | 6 | 0.0000 | 0.0278 | 0.0083 | 55.2157 |
| BAAI/bge-base-en-v1.5 | needs_review=true | 11 | 0.0000 | 0.0130 | 0.0091 | 51.7959 |
| intfloat/multilingual-e5-large | all | 17 | 0.2941 | 0.2176 | 0.1618 | 179.6141 |
| intfloat/multilingual-e5-large | needs_review=false | 6 | 0.3333 | 0.2000 | 0.0917 | 192.9363 |
| intfloat/multilingual-e5-large | needs_review=true | 11 | 0.2727 | 0.2273 | 0.2000 | 172.3474 |
| BAAI/bge-m3 | all | 17 | 0.3529 | 0.2794 | 0.1765 | 155.3714 |
| BAAI/bge-m3 | needs_review=false | 6 | 0.3333 | 0.2500 | 0.0917 | 174.4200 |
| BAAI/bge-m3 | needs_review=true | 11 | 0.3636 | 0.2955 | 0.2227 | 144.9812 |
| mixedbread-ai/mxbai-embed-large-v1 | all | 17 | 0.1765 | 0.1765 | 0.0735 | 139.1709 |
| mixedbread-ai/mxbai-embed-large-v1 | needs_review=false | 6 | 0.1667 | 0.1667 | 0.0333 | 136.3582 |
| mixedbread-ai/mxbai-embed-large-v1 | needs_review=true | 11 | 0.1818 | 0.1818 | 0.0955 | 140.7051 |
| nomic-ai/nomic-embed-text-v1.5 | all | 17 | 0.1176 | 0.0882 | 0.1294 | 64.0071 |
| nomic-ai/nomic-embed-text-v1.5 | needs_review=false | 6 | 0.1667 | 0.1667 | 0.0333 | 67.0335 |
| nomic-ai/nomic-embed-text-v1.5 | needs_review=true | 11 | 0.0909 | 0.0455 | 0.1818 | 62.3563 |

## Skipped Queries
openstack_q003, openstack_q004, openstack_q008, openstack_q011, openstack_q012, openstack_q015, openstack_q017, openstack_q019, openstack_q021, openstack_q022, openstack_q025, openstack_q026, openstack_q030
