# Embedding Benchmark Report: apache

This benchmark uses qrels_silver.jsonl as silver labels. Labels have not been fully manual-reviewed.

## Dataset
- Logs: 2000
- Queries evaluated: 22
- Queries skipped because they have no usable positive labels: 8

## Model Comparison
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | 22 | 8 | 0.0000 | 0.0000 | 0.0000 | 0.2959 |
| sentence-transformers/all-MiniLM-L6-v2 | 22 | 8 | 0.4545 | 0.2254 | 0.1114 | 13.0502 |
| intfloat/multilingual-e5-base | 22 | 8 | 0.5455 | 0.4610 | 0.1500 | 60.7354 |
| BAAI/bge-base-en-v1.5 | 22 | 8 | 0.3182 | 0.2500 | 0.0977 | 60.4610 |
| intfloat/multilingual-e5-large | 22 | 8 | 0.5000 | 0.3505 | 0.1364 | 190.4563 |
| BAAI/bge-m3 | 22 | 8 | 0.4545 | 0.3674 | 0.1295 | 155.1058 |
| mixedbread-ai/mxbai-embed-large-v1 | 22 | 8 | 0.4545 | 0.3220 | 0.1273 | 162.4446 |
| nomic-ai/nomic-embed-text-v1.5 | 22 | 8 | 0.3636 | 0.2924 | 0.1091 | 58.3773 |

## Highlights
- Best Hit@5: intfloat/multilingual-e5-base (0.5455)
- Best MRR@10: intfloat/multilingual-e5-base (0.4610)
- Fastest average query latency: bm25 (0.30 ms)

## BM25 vs Semantic Search
Best semantic model beats BM25 by 0.5455 Hit@5 on this silver set.

## Review Subsets
| model_name | subset | num_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | all | 22 | 0.0000 | 0.0000 | 0.0000 | 0.2959 |
| bm25 | needs_review=false | 16 | 0.0000 | 0.0000 | 0.0000 | 0.2831 |
| bm25 | needs_review=true | 6 | 0.0000 | 0.0000 | 0.0000 | 0.3302 |
| sentence-transformers/all-MiniLM-L6-v2 | all | 22 | 0.4545 | 0.2254 | 0.1114 | 13.0502 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=false | 16 | 0.4375 | 0.2266 | 0.1156 | 13.8363 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=true | 6 | 0.5000 | 0.2222 | 0.1000 | 10.9538 |
| intfloat/multilingual-e5-base | all | 22 | 0.5455 | 0.4610 | 0.1500 | 60.7354 |
| intfloat/multilingual-e5-base | needs_review=false | 16 | 0.5625 | 0.5000 | 0.1594 | 64.8314 |
| intfloat/multilingual-e5-base | needs_review=true | 6 | 0.5000 | 0.3571 | 0.1250 | 49.8127 |
| BAAI/bge-base-en-v1.5 | all | 22 | 0.3182 | 0.2500 | 0.0977 | 60.4610 |
| BAAI/bge-base-en-v1.5 | needs_review=false | 16 | 0.3125 | 0.2500 | 0.0938 | 64.5576 |
| BAAI/bge-base-en-v1.5 | needs_review=true | 6 | 0.3333 | 0.2500 | 0.1083 | 49.5368 |
| intfloat/multilingual-e5-large | all | 22 | 0.5000 | 0.3505 | 0.1364 | 190.4563 |
| intfloat/multilingual-e5-large | needs_review=false | 16 | 0.5625 | 0.3882 | 0.1500 | 190.6456 |
| intfloat/multilingual-e5-large | needs_review=true | 6 | 0.3333 | 0.2500 | 0.1000 | 189.9514 |
| BAAI/bge-m3 | all | 22 | 0.4545 | 0.3674 | 0.1295 | 155.1058 |
| BAAI/bge-m3 | needs_review=false | 16 | 0.4375 | 0.3177 | 0.1312 | 158.9184 |
| BAAI/bge-m3 | needs_review=true | 6 | 0.5000 | 0.5000 | 0.1250 | 144.9389 |
| mixedbread-ai/mxbai-embed-large-v1 | all | 22 | 0.4545 | 0.3220 | 0.1273 | 162.4446 |
| mixedbread-ai/mxbai-embed-large-v1 | needs_review=false | 16 | 0.4375 | 0.2865 | 0.1250 | 157.3294 |
| mixedbread-ai/mxbai-embed-large-v1 | needs_review=true | 6 | 0.5000 | 0.4167 | 0.1333 | 176.0851 |
| nomic-ai/nomic-embed-text-v1.5 | all | 22 | 0.3636 | 0.2924 | 0.1091 | 58.3773 |
| nomic-ai/nomic-embed-text-v1.5 | needs_review=false | 16 | 0.3125 | 0.2396 | 0.0969 | 57.6850 |
| nomic-ai/nomic-embed-text-v1.5 | needs_review=true | 6 | 0.5000 | 0.4333 | 0.1417 | 60.2234 |

## Skipped Queries
apache_q003, apache_q011, apache_q012, apache_q015, apache_q018, apache_q019, apache_q026, apache_q030
