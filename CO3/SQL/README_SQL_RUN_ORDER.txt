MySQL 8.0 run order
===================
1. Open MySQL Command Line Client or MySQL Workbench.
2. Run the schema script:
   SOURCE C:/full/path/CO3/SQL/01_create_three_designs_mysql.sql;
3. Generate a deterministic CSV from the CO3 folder:
   python Python_Scripts/generate_order_line_csv.py --rows 100000 --output Data/order_line_100000.csv
4. Install the optional connector and run the common CSV loader:
   pip install mysql-connector-python
   python Python_Scripts/load_mysql_from_csv.py --csv Data/order_line_100000.csv --user root --database shopnest_co3
5. Run the Task 12 price-history and paid-price migration script:
   SOURCE C:/full/path/CO3/SQL/02_task12_price_history_mysql.sql;
6. Import verified UnitPricePaid values from the store's invoice/payment history into
   order_item_paid_price_stage. Do not substitute the current PRODUCT price for
   historical paid values. Check lines_missing_verified_paid_price; it must be zero
   before uncommenting the ALTER TABLE ... MODIFY UnitPricePaid NOT NULL command.
7. Run the operational query script (after Task 12 added UnitPricePaid):
   SOURCE C:/full/path/CO3/SQL/03_validation_queries_mysql.sql;

Notes
-----
- Run the schema script before loading data.
- The Task 12 script adds UnitPricePaid as NULL because old transaction prices must
  come from authoritative invoice/payment records. It includes a staging table and
  a missing-value count. Enforce NOT NULL only after verified historical data is loaded.
- The optional MySQL loader is included but has not been tested against a live server here.
- The benchmark / theory / integrity outputs in Execution_Evidence are actual Python/SQLite
  runs, not MySQL screenshots or MySQL query results.
- Capture genuine MySQL terminal or Workbench screenshots on the student laptop if
  live MySQL execution evidence is required by the instructor.
