# Final Model Comparison

This report compares the v2 benchmark output with the previous v1 results when available.
The benchmark uses qrels_silver.jsonl as silver labels and does not use pairs.jsonl.

## apache

### v2 Results
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3-Embedding-0.6B | 22 | 8 | 0.5000 | 0.4167 | 0.1250 | 254.0012 |
| jinaai/jina-embeddings-v3 | 22 | 8 | 0.4545 | 0.4369 | 0.1205 | 851.8791 |

### Best Models
- Best Hit@5: Qwen/Qwen3-Embedding-0.6B (0.5000)
- Best MRR@10: jinaai/jina-embeddings-v3 (0.4369)
- Fastest: Qwen/Qwen3-Embedding-0.6B (254.00 ms/query)

### v1 vs v2
| model_name | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- |
| bm25 | 0.0000 | 0.0000 | 0.0000 | 0.3841 |
| sentence-transformers/all-MiniLM-L6-v2 | 0.4545 | 0.2254 | 0.1114 | 17.8390 |
| intfloat/multilingual-e5-base | 0.5455 | 0.4610 | 0.1500 | 71.7373 |
| BAAI/bge-base-en-v1.5 | 0.3182 | 0.2500 | 0.0977 | 61.7312 |

### New Model Check
No new extended model beats multilingual-e5-base v1 on Hit@5; best new model trails by 0.0455: Qwen/Qwen3-Embedding-0.6B.

## openstack

### v2 Results
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3-Embedding-0.6B | 17 | 13 | 0.2353 | 0.1849 | 0.1559 | 236.2383 |
| jinaai/jina-embeddings-v3 | 17 | 13 | 0.3529 | 0.2549 | 0.1647 | 715.3133 |

### Best Models
- Best Hit@5: jinaai/jina-embeddings-v3 (0.3529)
- Best MRR@10: jinaai/jina-embeddings-v3 (0.2549)
- Fastest: Qwen/Qwen3-Embedding-0.6B (236.24 ms/query)

### v1 vs v2
| model_name | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- |
| bm25 | 0.1765 | 0.1471 | 0.1353 | 1.5952 |
| sentence-transformers/all-MiniLM-L6-v2 | 0.0000 | 0.0074 | 0.0588 | 17.4254 |
| intfloat/multilingual-e5-base | 0.2941 | 0.2549 | 0.1647 | 63.5999 |
| BAAI/bge-base-en-v1.5 | 0.0000 | 0.0182 | 0.0088 | 59.7229 |

### New Model Check
New best extended model beats multilingual-e5-base v1 by 0.0588 Hit@5: jinaai/jina-embeddings-v3.

## hdfs

### v2 Results
| model_name | num_queries | num_skipped_queries | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen/Qwen3-Embedding-0.6B | 22 | 8 | 0.1364 | 0.1182 | 0.0159 | 249.6035 |
| jinaai/jina-embeddings-v3 | 22 | 8 | 0.0909 | 0.0909 | 0.0045 | 1070.4247 |

### Best Models
- Best Hit@5: Qwen/Qwen3-Embedding-0.6B (0.1364)
- Best MRR@10: Qwen/Qwen3-Embedding-0.6B (0.1182)
- Fastest: Qwen/Qwen3-Embedding-0.6B (249.60 ms/query)

### v1 vs v2
| model_name | hit@5 | mrr@10 | recall@10 | avg_latency_ms |
| --- | --- | --- | --- | --- |
| bm25 | 0.1818 | 0.1477 | 0.0864 | 2.8790 |
| sentence-transformers/all-MiniLM-L6-v2 | 0.0455 | 0.0455 | 0.0023 | 21.6036 |
| intfloat/multilingual-e5-base | 0.1364 | 0.1153 | 0.0114 | 63.1912 |
| BAAI/bge-base-en-v1.5 | 0.1364 | 0.1364 | 0.0068 | 67.7805 |

### New Model Check
New best extended model beats multilingual-e5-base v1 by 0.0000 Hit@5: Qwen/Qwen3-Embedding-0.6B.
