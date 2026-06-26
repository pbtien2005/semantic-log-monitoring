# Semantic Log Retrieval Benchmark

Benchmark skeleton for Semantic Log Retrieval on three LogHub datasets:
Apache, OpenStack, and HDFS. The first phase keeps datasets separated and
prepares raw logs, corpus schema, queries, qrels, and retrieval pairs. It does
not run RAG or LLM answering.

## Project Layout

```text
data/                 # Raw LogHub files, parsed corpora, chunks, and benchmark artifacts
scripts/ingestion/    # Data download, checks, and corpus building CLIs
scripts/chunking/     # Chunk artifact building CLIs
scripts/benchmark/    # Query, qrels, and benchmark validation CLIs
src/core/             # Shared schema, IO, and text utilities
src/chunking/         # Chunk normalization, entity extraction, and builders
src/rules/            # Rule-based log category scoring
src/benchmark/        # Shared benchmark definitions
```

## LogHub Data

The source dataset repository is [logpai/loghub](https://github.com/logpai/loghub).
This project expects raw files under:

```text
data/raw/apache/
data/raw/openstack/
data/raw/hdfs/
```

The helper script downloads the LogHub 2k sample raw log files when the direct
GitHub raw URLs are available:

```powershell
python scripts/ingestion/download_loghub_data.py --dataset apache
python scripts/ingestion/download_loghub_data.py --dataset openstack
python scripts/ingestion/download_loghub_data.py --dataset hdfs
python scripts/ingestion/download_loghub_data.py --dataset all
```

By default, existing files are not overwritten. To refresh a downloaded sample:

```powershell
python scripts/ingestion/download_loghub_data.py --dataset apache --force
```

If automatic download fails, download the files manually from:

```text
https://github.com/logpai/loghub/tree/master/Apache
https://github.com/logpai/loghub/tree/master/OpenStack
https://github.com/logpai/loghub/tree/master/HDFS
```

Place each raw log file in its matching directory, for example:

```text
data/raw/apache/Apache_2k.log
data/raw/openstack/OpenStack_2k.log
data/raw/hdfs/HDFS_2k.log
```

## Check Raw Data

Before building `logs.jsonl`, verify that raw data is ready:

```powershell
python scripts/ingestion/check_raw_data.py
python scripts/ingestion/check_raw_data.py --dataset apache
```

The check prints each dataset, destination folder, file names, file sizes, and
`ready` or `not ready`.

## Build Corpus

Raw data preparation is separate from parsing. After raw data is ready, build
the per-dataset corpus:

```powershell
python scripts/ingestion/build_log_corpus.py --dataset apache
python scripts/ingestion/build_log_corpus.py --dataset openstack
python scripts/ingestion/build_log_corpus.py --dataset hdfs
python scripts/ingestion/build_log_corpus.py --dataset all
```

## Build Chunks

Chunking reads parsed corpus files from `data/benchmark/{dataset}/logs.jsonl`
and writes retrieval-ready artifacts to `data/chunking/{dataset}/`:

```powershell
python scripts/chunking/build_chunks.py --dataset apache
python scripts/chunking/build_chunks.py --dataset openstack
python scripts/chunking/build_chunks.py --dataset hdfs
python scripts/chunking/build_chunks.py --dataset all
```

Each dataset receives:

```text
data/chunking/{dataset}/log_lines.jsonl
data/chunking/{dataset}/templates.jsonl
```
