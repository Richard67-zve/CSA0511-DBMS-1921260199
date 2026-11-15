#!/usr/bin/env python3
"""Demonstrate Task 12 ownership migration and a share change during active custody.
Uses the reproducible SQLite validation schema only as a local logic test.
"""
import sqlite3, json
from pathlib import Path
from run_validation import build_db, OUT

DB=OUT/'task12_migration_demo.sqlite'
if DB.exists(): DB.unlink()
con, counts=build_db(100,DB)
con.execute('''CREATE TABLE artifact_owner (
 artifact_id INTEGER NOT NULL REFERENCES artifact(artifact_id),
 party_id INTEGER NOT NULL REFERENCES party(party_id),
 share_percent REAL NOT NULL CHECK(share_percent>0 AND share_percent<=100),
 valid_from TEXT NOT NULL, valid_to TEXT,
 source_quality TEXT NOT NULL,
 PRIMARY KEY(artifact_id,party_id,valid_from),
 CHECK(valid_to IS NULL OR valid_to>=valid_from))''')
con.execute('''INSERT INTO artifact_owner
 SELECT artifact_id, owner_party_id, 100.0,
        COALESCE(ownership_known_from,'2026-11-13'), NULL,
        CASE WHEN ownership_known_from IS NULL THEN 'MIGRATION_BASELINE_UNKNOWN_START'
             ELSE 'MIGRATED_KNOWN_START' END
 FROM artifact''')
# Artifact 3 is currently in the successive loan beginning 2026-06-01.
# Legal owners split shares on 2026-12-01. Custody row is not changed.
con.execute("UPDATE artifact_owner SET valid_to='2026-11-30' WHERE artifact_id=3")
ownership_rows_before = con.execute('SELECT COUNT(*) FROM artifact_owner').fetchone()[0]
loan_objects_before = con.execute('SELECT COUNT(*) FROM loan_object').fetchone()[0]
reports_before = con.execute('SELECT COUNT(*) FROM condition_report').fetchone()[0]
con.executemany('INSERT INTO artifact_owner VALUES (?,?,?,?,?,?)',[
 (3,41,50.0,'2026-12-01',None,'VERIFIED_HISTORY'),
 (3,141,50.0,'2026-12-01',None,'VERIFIED_HISTORY'),
])
con.commit()
ownership_rows_after = con.execute('SELECT COUNT(*) FROM artifact_owner').fetchone()[0]
loan_objects_after = con.execute('SELECT COUNT(*) FROM loan_object').fetchone()[0]
reports_after = con.execute('SELECT COUNT(*) FROM condition_report').fetchone()[0]

def owners(asof):
 return [list(r) for r in con.execute('''SELECT party_id,share_percent,valid_from,valid_to,source_quality
 FROM artifact_owner WHERE artifact_id=3 AND valid_from<=?
 AND (valid_to IS NULL OR valid_to>=?) ORDER BY party_id''',(asof,asof))]

before=owners('2026-11-30'); after=owners('2026-12-01')
loan=con.execute('''SELECT l.loan_no,l.loan_status,lo.custody_start,lo.custody_end
 FROM loan_object lo JOIN loan l USING(loan_id)
 WHERE lo.artifact_id=3 AND lo.loan_id=101''').fetchone()
share_sums={d:con.execute('''SELECT COALESCE(SUM(share_percent),0) FROM artifact_owner
 WHERE artifact_id=3 AND valid_from<=? AND (valid_to IS NULL OR valid_to>=?)''',(d,d)).fetchone()[0]
 for d in ['2026-11-30','2026-12-01']}
invalid_total=con.execute('''SELECT artifact_id,SUM(share_percent) total_share
 FROM artifact_owner WHERE artifact_id=3 AND valid_from<='2026-12-01'
 AND (valid_to IS NULL OR valid_to>='2026-12-01') GROUP BY artifact_id
 HAVING ABS(SUM(share_percent)-100)>0.01''').fetchall()
result={"baseline_single_owner_at_2026_11_30":before,"new_shared_owners_at_2026_12_01":after,
 "active_custody_unchanged":list(loan),"share_totals":share_sums,
 "invalid_share_sum_rows":invalid_total,
 "migration_rows_with_unknown_start":con.execute("SELECT COUNT(*) FROM artifact_owner WHERE source_quality='MIGRATION_BASELINE_UNKNOWN_START'").fetchone()[0],
 "relationship_counts": {
   "artifact_owner_rows_before_transition": ownership_rows_before,
   "artifact_owner_rows_after_transition": ownership_rows_after,
   "loan_object_rows_before_after": [loan_objects_before, loan_objects_after],
   "condition_report_rows_before_after": [reports_before, reports_after]
 }}
(OUT/'task12_ownership_demo.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
con.close()
