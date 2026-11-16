USE swiftspan_co2;

-- Run each expected-failure statement separately (or within a client savepoint),
-- record the exact MySQL error, then ROLLBACK. Do not include in bulk-load run.
START TRANSACTION;
-- Expected CHECK failure (8.0.16+):
-- INSERT INTO bcnf_observation VALUES (1,1,99,101);
ROLLBACK;

START TRANSACTION;
-- Expected duplicate primary key failure (requires sender 1/service 1/wave 1 to exist):
-- INSERT INTO bcnf_observation VALUES (1,1,1,50);
ROLLBACK;

START TRANSACTION;
-- Expected FK failure (non-existing SenderID):
-- INSERT INTO bcnf_assignment VALUES (999999,1,1);
ROLLBACK;

-- Update-anomaly trial in flat design: expected multiple rows for ServiceID=1.
START TRANSACTION;
-- UPDATE flat_handover SET ServiceName='Temporary test label' WHERE ServiceID=1;
-- SELECT ROW_COUNT() AS affected_flat_rows;
ROLLBACK;

-- Normalized catalog update trial: one service row is updated once.
START TRANSACTION;
-- UPDATE bcnf_service SET ServiceName='Temporary test label' WHERE ServiceID=1;
-- SELECT ROW_COUNT() AS affected_catalog_rows;
ROLLBACK;
