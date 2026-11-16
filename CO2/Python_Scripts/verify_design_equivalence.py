#!/usr/bin/env python3
"""Compare complete logical observation streams and sample reconstructed rows."""
import hashlib,sqlite3,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DB=ROOT/'outputs'/'databases'; OUT=ROOT/'outputs'
checks=[]
for n in (10000,100000,600000):
    digests={}
    for design in ('flat','partial','bcnf'):
        con=sqlite3.connect(DB/f'{design}_{n}.sqlite')
        table={'flat':'flat_handover','partial':'partial_observation','bcnf':'observation'}[design]
        cur=con.execute(f'SELECT SenderID,ServiceID,DispatchWave,Completion FROM {table} ORDER BY SenderID,ServiceID,DispatchWave')
        h=hashlib.sha256(); count=0
        for row in cur:
            h.update(('|'.join(map(str,row))+'\n').encode());count+=1
        digests[design]={'rows':count,'sha256':h.hexdigest()}
        con.close()
    checks.append({'observations':n,'designs':digests,'all_identical':len({x['sha256'] for x in digests.values()})==1})
with open(OUT/'full_observation_equivalence.json','w') as f: json.dump(checks,f,indent=2)
for x in checks: print(x['observations'], 'PASS' if x['all_identical'] else 'FAIL', {k:v['sha256'][:16] for k,v in x['designs'].items()})
