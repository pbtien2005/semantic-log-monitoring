# Final Model Comparison

This report compares the v2 benchmark output with the previous v1 results when available.
The benchmark uses qrels_silver.jsonl as silver labels and does not use pairs.jsonl.

## apache

### v2 Results
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

### Best Models
- Best Hit@5: intfloat/multilingual-e5-base (0.5455)
- Best MRR@10: intfloat/multilingual-e5-base (0.4610)
- Fastest: bm25 (0.30 ms/query)

### v1 vs v2
| model_name | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- |
| bm25 | 0.0000 | 0.0000 | 0.0000 | 0.3841 |
| sentence-transformers/all-MiniLM-L6-v2 | 0.4545 | 0.2254 | 0.1114 | 17.8390 |
| intfloat/multilingual-e5-base | 0.5455 | 0.4610 | 0.1500 | 71.7373 |
| BAAI/bge-base-en-v1.5 | 0.3182 | 0.2500 | 0.0977 | 61.7312 |

### New Model Check
No new extended model beats multilingual-e5-base v1 on Hit@5; best new model trails by 0.0455: intfloat/multilingual-e5-large.

### BM25 Status
Semantic search wins Hit@5 over BM25 (0.5455 vs 0.0000).

## openstack

### v2 Results
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

### Best Models
- Best Hit@5: BAAI/bge-m3 (0.3529)
- Best MRR@10: BAAI/bge-m3 (0.2794)
- Fastest: bm25 (1.21 ms/query)

### v1 vs v2
| model_name | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- |
| bm25 | 0.1765 | 0.1471 | 0.1353 | 1.5952 |
| sentence-transformers/all-MiniLM-L6-v2 | 0.0000 | 0.0074 | 0.0588 | 17.4254 |
| intfloat/multilingual-e5-base | 0.2941 | 0.2549 | 0.1647 | 63.5999 |
| BAAI/bge-base-en-v1.5 | 0.0000 | 0.0182 | 0.0088 | 59.7229 |

### New Model Check
New best extended model beats multilingual-e5-base v1 by 0.0588 Hit@5: BAAI/bge-m3.

### BM25 Status
Semantic search wins Hit@5 over BM25 (0.3529 vs 0.1765).

## hdfs

### v2 Results
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

### Best Models
- Best Hit@5: intfloat/multilingual-e5-large (0.2273)
- Best MRR@10: intfloat/multilingual-e5-large (0.1682)
- Fastest: bm25 (1.90 ms/query)

### v1 vs v2
| model_name | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- |
| bm25 | 0.1818 | 0.1477 | 0.0864 | 2.8790 |
| sentence-transformers/all-MiniLM-L6-v2 | 0.0455 | 0.0455 | 0.0023 | 21.6036 |
| intfloat/multilingual-e5-base | 0.1364 | 0.1153 | 0.0114 | 63.1912 |
| BAAI/bge-base-en-v1.5 | 0.1364 | 0.1364 | 0.0068 | 67.7805 |

### New Model Check
New best extended model beats multilingual-e5-base v1 by 0.0909 Hit@5: intfloat/multilingual-e5-large.

### BM25 Status
Semantic search wins Hit@5 over BM25 (0.2273 vs 0.1818).
