"""Generate deterministic synthetic bank transaction data for CO4.

The full million-record run can create a large CSV; use --sample for a small
inspection file. The block simulation uses TxnID keys directly to avoid a
needless 200 MB text file when only block counts are being studied.
"""
import argparse, csv, random, os
from datetime import datetime, timedelta

def rows(n, seed=4211):
    rng=random.Random(seed); base=datetime(2026,1,1)
    accounts=[f'{i:012d}' for i in range(1,50001)]
    branches=[f'BR-{i:03d}' for i in range(1,26)]
    channels=['ATM','UPI','WEB','MOBILE','BRANCH']
    types=['CR','DR']
    for txn in range(1,n+1):
        dt=base+timedelta(seconds=txn*37)
        yield {
            'TxnID':txn,'AccountNo':rng.choice(accounts),'TxnTime':dt.isoformat(sep=' '),
            'Type':rng.choice(types),'Amount':f'{rng.uniform(10,75000):.2f}',
            'Branch':rng.choice(branches),'Channel':rng.choice(channels),
            'Narration':f'Synthetic transaction {txn:08d}','Balance':f'{rng.uniform(100,500000):.2f}'
        }

def main():
    p=argparse.ArgumentParser(); p.add_argument('--size',type=int,default=100); p.add_argument('--out',default='Data/transactions_preview.csv'); p.add_argument('--seed',type=int,default=4211); a=p.parse_args()
    os.makedirs(os.path.dirname(a.out) or '.',exist_ok=True)
    with open(a.out,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['TxnID','AccountNo','TxnTime','Type','Amount','Branch','Channel','Narration','Balance']); w.writeheader(); w.writerows(rows(a.size,a.seed))
    print(f'Generated {a.size:,} synthetic records at {a.out} (seed={a.seed}).')
if __name__=='__main__': main()
