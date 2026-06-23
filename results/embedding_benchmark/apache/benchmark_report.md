# Embedding Benchmark Report: apache

This benchmark uses qrels_silver.jsonl as silver labels. Labels have not been fully manual-reviewed.

## Dataset
- Logs: 2000
- Queries evaluated: 22
- Queries skipped because they have no usable positive labels: 8

## Model Comparison
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | 22 | 8 | 0.0000 | 0.0000 | 0.0000 | 0.3841 |
| sentence-transformers/all-MiniLM-L6-v2 | 22 | 8 | 0.4545 | 0.2254 | 0.1114 | 17.8390 |
| intfloat/multilingual-e5-base | 22 | 8 | 0.5455 | 0.4610 | 0.1500 | 71.7373 |
| BAAI/bge-base-en-v1.5 | 22 | 8 | 0.3182 | 0.2500 | 0.0977 | 61.7312 |

## Highlights
- Best Hit@5: intfloat/multilingual-e5-base (0.5455)
- Best MRR@10: intfloat/multilingual-e5-base (0.4610)
- Fastest average query latency: bm25 (0.38 ms)

## BM25 vs Semantic Search
Best semantic model beats BM25 by 0.5455 Hit@5 on this silver set.

## Review Subsets
| model_name | subset | num_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| bm25 | all | 22 | 0.0000 | 0.0000 | 0.0000 | 0.3841 |
| bm25 | needs_review=false | 16 | 0.0000 | 0.0000 | 0.0000 | 0.2899 |
| bm25 | needs_review=true | 6 | 0.0000 | 0.0000 | 0.0000 | 0.6352 |
| sentence-transformers/all-MiniLM-L6-v2 | all | 22 | 0.4545 | 0.2254 | 0.1114 | 17.8390 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=false | 16 | 0.4375 | 0.2266 | 0.1156 | 17.7034 |
| sentence-transformers/all-MiniLM-L6-v2 | needs_review=true | 6 | 0.5000 | 0.2222 | 0.1000 | 18.2004 |
| intfloat/multilingual-e5-base | all | 22 | 0.5455 | 0.4610 | 0.1500 | 71.7373 |
| intfloat/multilingual-e5-base | needs_review=false | 16 | 0.5625 | 0.5000 | 0.1594 | 74.5006 |
| intfloat/multilingual-e5-base | needs_review=true | 6 | 0.5000 | 0.3571 | 0.1250 | 64.3686 |
| BAAI/bge-base-en-v1.5 | all | 22 | 0.3182 | 0.2500 | 0.0977 | 61.7312 |
| BAAI/bge-base-en-v1.5 | needs_review=false | 16 | 0.3125 | 0.2500 | 0.0938 | 62.0022 |
| BAAI/bge-base-en-v1.5 | needs_review=true | 6 | 0.3333 | 0.2500 | 0.1083 | 61.0087 |

## Skipped Queries
apache_q003, apache_q011, apache_q012, apache_q015, apache_q018, apache_q019, apache_q026, apache_q030
