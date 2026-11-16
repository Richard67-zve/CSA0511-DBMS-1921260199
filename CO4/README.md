# DBMS Assignment 4 - CO4 | Bank Transaction Log

**Student:** M. Richard  
**Register number:** 1921260199  
**Course:** Database Management Systems (CSA05)  
**Outcome:** CO4 - File organisation, indexing and hashing

## What is in this folder?

- `Documentation/` - run order and implementation notes.
- `Python_Scripts/` - runnable block-level simulation, correctness checks, B-tree/B+ tree and hashing traces, data generator and chart/evidence builders.
- `Data/transactions_preview.csv` - 100-row synthetic full-record preview generated with seed 4211.
- `Results/benchmark.csv` - measured results for 1,000, 10,000, 100,000 and 1,000,000 transaction keys.
- `Results/tree_hash_traces.json` - order-4 tree insertion/deletion traces.
- `Results/hash_traces.json` - static, extendible and linear hashing traces.
- `Diagrams/` - storage architecture and benchmark charts.
- `Execution_Evidence/Output_Captures/` - rendered captures of actual script output.
- `Execution_Evidence/Text_Logs/` - raw text execution logs.
- `Documentation/Assignment_Report.docx` and `.pdf` - written submission.

## Run the work

From this folder:

```bash
python -m pip install -r requirements.txt
python Python_Scripts/run_all.py
```

The run script executes the block simulator, boundary/correctness tests, tree and hashing traces, sample data generation and chart/evidence generation in order.

## Simulation scope and honesty notes

The uploaded assignment explicitly permits a Python 3 block-level simulation. The implementation models 4,096-byte blocks containing up to 20 fixed-size 200-byte transaction records. The compared organisations are heap, sorted sequential with a sparse-index descent model, static hash with overflow pages, and clustered B+ tree. Each dataset size uses deterministic increasing TxnID keys and the same 25 equality probes and five range queries.

The counters are **logical block reads/writes produced by the simulator**, not physical HDD/SSD measurements. Python elapsed times are in-memory implementation timings and must not be interpreted as disk throughput or production capacity. The B+ tree implementation stores leaf pages as key lists and models internal-page fan-out/height logically. The order-4 tree traces show the mechanics of splits, redistribution and merging separately.

Output captures are generated from recorded program output; they are not screenshots from a physical laptop or MySQL client. This assignment uses the Python simulation option, so no MySQL execution is claimed.

## Main observed result (one million records)

- Heap: approximately 25,001 logical reads per equality lookup and 50,000 for a full-scan range query.
- Sorted sequential + sparse index: approximately 3 equality reads and 104 range reads for the tested 2,000-key range.
- Static hash: 1 equality bucket read in the controlled uniform sequential-key benchmark, but all 62,500 bucket pages are inspected for range queries.
- Clustered B+ tree: 3 equality reads and about 103 reads for the tested 2,000-key range.

See `Results/benchmark.csv` for all measured columns, including build time, query elapsed time, insert/delete counters, splits and tree height.
