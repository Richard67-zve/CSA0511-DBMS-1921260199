# DBMS Assignment 3 - CO3 | ShopNest Order Management

**Student:** M. Richard  
**Register number:** 1921260199  
**Course:** Database Management Systems (CSA05)  
**Course Outcome:** CO3 - Functional dependencies, normalisation and key constraints

This folder is intended to be uploaded as `CO3/` inside the common GitHub repository that also contains `CO1/` and `CO2/`.

## Contents

```text
CO3/
├── Assignment/
│   ├── M_Richard_DBMS_Assignment_CO3_FINAL.docx
│   └── M_Richard_DBMS_Assignment_CO3_FINAL.pdf
├── SQL/
│   ├── 01_create_three_designs_mysql.sql
│   ├── 02_task12_price_history_mysql.sql
│   ├── 03_validation_queries_mysql.sql
│   └── README_SQL_RUN_ORDER.txt
├── Python_Scripts/
│   ├── run_experiments.py
│   ├── verify_normalization_theory.py
│   ├── edge_case_tests.py
│   ├── generate_order_line_csv.py
│   ├── load_mysql_from_csv.py
│   └── plot_results.py
├── Data/
│   ├── order_line_sample_12.csv
│   └── order_line_generated_12.csv
├── Diagrams/
│   ├── dependency_diagram.png
│   ├── normalization_roadmap.png
│   ├── mvd_4nf.png
│   └── join_dependency_5nf.png
├── outputs/
│   ├── benchmark_results.csv
│   ├── relation_row_counts_1m.csv
│   ├── integrity_tests.csv
│   ├── edge_case_tests.csv / .txt
│   ├── theory_verification.json / .txt
│   ├── execution_summary.json
│   ├── shopnest_demo.sqlite
│   └── charts
└── Execution_Evidence/
    ├── Output_Captures/
    └── Text_Logs/
```

## What was executed

The Python/SQLite experiments were actually run in this environment using **Python 3.13.5** and **SQLite 3.46.1**. The 4NF tuple-swap verification uses an eight-tuple 2 × 4 tag/colour instance, satisfying the brief minimum; the separate benchmark generator uses three tags and two colours per product. The benchmark creates identical deterministic logical data for the unnormalised, 3NF and BCNF/4NF/5NF designs at 1,000, 10,000, 100,000 and 1,000,000 order-line rows. It records storage, load time, supplier-fact update rows/time and order-history query time. It also executes closure/MVD/5NF reconstruction checks and anomaly/boundary tests.

The PNG captures in `Execution_Evidence/Output_Captures/` are terminal-style images rendered from saved execution logs and CSV outputs. They are **not** photographs or screenshots of a student laptop screen.

## MySQL files

MySQL 8.0-oriented schema, Task 12 price-history changes and sample validation queries are supplied in `SQL/`. `Python_Scripts/generate_order_line_csv.py` can generate a larger source CSV. `Python_Scripts/load_mysql_from_csv.py` is an optional loader and requires:

```bash
pip install mysql-connector-python
```

Example commands (after running the schema script in MySQL):

```bash
python Python_Scripts/generate_order_line_csv.py --rows 100000 --output ../Data/order_line_100000.csv
python Python_Scripts/load_mysql_from_csv.py --csv Data/order_line_100000.csv --host localhost --user root --database shopnest_co3
```

**Important:** The MySQL DDL and optional loader were not executed against a live MySQL server in this authoring environment. The actual recorded measurements are from SQLite, and must not be described as MySQL execution results. To provide MySQL-specific execution proof, run the SQL files on your own MySQL client and add genuine screenshots to `Execution_Evidence/`.

## Re-run the portable experiments

From inside the `CO3/` folder:

```bash
python Python_Scripts/run_experiments.py
python Python_Scripts/verify_normalization_theory.py
python Python_Scripts/edge_case_tests.py
python Python_Scripts/plot_results.py
```

The outputs are regenerated under `outputs/`, `Diagrams/` and `Execution_Evidence/Output_Captures/`.

## Submission reminder

Replace the GitHub placeholder on the cover page with the URL of the common repository. Upload this entire `CO3/` folder beside `CO1/` and `CO2/`. Keep the report's SQLite/MySQL evidence distinction intact.
