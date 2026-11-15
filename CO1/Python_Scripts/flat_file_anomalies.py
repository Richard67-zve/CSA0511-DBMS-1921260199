#!/usr/bin/env python3
"""Demonstrate insertion, update and deletion anomalies in a denormalised LOAN file."""
import csv, tempfile
from pathlib import Path

rows=[
 ['loan_no','lender_name','lender_email','artifact_accession','artifact_title','loan_date'],
 ['LN-01','Anita Rao','anita@example.test','MM-01','Bronze lamp','2026-02-01'],
 ['LN-02','Anita Rao','anita@example.test','MM-02','Temple bell','2026-03-01'],
 ['LN-03','B. Kumar','bk@example.test','MM-03','Silk panel','2026-04-01'],
]
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'flat_loan.csv'
    with p.open('w',newline='',encoding='utf-8') as f: csv.writer(f).writerows(rows)
    print('BASE FLAT FILE:'); print(p.read_text(encoding='utf-8'))
    data=list(csv.DictReader(p.open(encoding='utf-8')))
    print('INSERTION ANOMALY: lender C. Das with no loan cannot be stored in this row structure; no row exists for that lender.')
    # Update only one occurrence of duplicated lender information.
    data[0]['lender_email']='new-anita@example.test'
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(data)
    after=list(csv.DictReader(p.open(encoding='utf-8')))
    print('UPDATE ANOMALY: after correcting only first row, Anita email values =', [r['lender_email'] for r in after if r['lender_name']=='Anita Rao'])
    # Delete the only loan line for B. Kumar; lender details disappear with it.
    after=[r for r in after if r['lender_name']!='B. Kumar']
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(after)
    print('DELETION ANOMALY: after deleting B. Kumar\'s only loan row, B. Kumar has no remaining lender record.')
