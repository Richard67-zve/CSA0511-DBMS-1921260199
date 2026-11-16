#!/usr/bin/env python3
"""Optional MySQL loader for the SwiftSpan CO2 assignment.

Install mysql-connector-python and set MYSQL_HOST, MYSQL_PORT, MYSQL_USER,
MYSQL_PASSWORD, MYSQL_DATABASE. The database and DDL must exist first.
"""
from __future__ import annotations
import os, argparse, random
try:
    import mysql.connector
except ImportError as exc:
    raise SystemExit('Install with: pip install mysql-connector-python') from exc

GROUPS=['RG-A','RG-B','RG-C','RG-D']; WAVES=(1,2,3,4); COORDINATORS=35; SEED=4211

def service_ids(group):
    i=GROUPS.index(group)
    return range(i*5+1, i*5+6)

def service(sid):
    return (sid,f'SVC-{sid:03d}',f'Service {sid:02d}',round(0.5+(sid%5)*0.25,3))

def sender(sid):
    return (sid,f'Sender {sid:05d}',GROUPS[(sid-1)%4])

def coord(cid):
    return (cid,f'Coordinator {cid:02d}',f'Hub-{(cid-1)%7+1:02d}')

def band(v):
    return 'LOW' if v<39 else ('STANDARD' if v<70 else 'HIGH')

def values(sid, svcid, wave, random_score):
    if sid % 20 in (1,2,3,4): completion=60+(random_score%41)
    elif svcid==5 and wave==4: completion=39+(random_score%62)
    else: completion=random_score
    cid=((sid*7+svcid*3)%COORDINATORS)+1
    b=band(completion)
    factor={'LOW':1.25,'STANDARD':1.0,'HIGH':0.85}[b]
    sv=service(svcid); sd=sender(sid); cd=coord(cid)
    return (sd[0],sd[1],sd[2],sv[0],sv[1],sv[2],sv[3],wave,cd[0],cd[1],cd[2],completion,b,factor)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--observations',type=int,choices=[10000,100000,600000],default=10000)
    ap.add_argument('--append',action='store_true',help='do not clear existing data tables')
    args=ap.parse_args()
    actors=args.observations//20
    con=mysql.connector.connect(host=os.getenv('MYSQL_HOST','127.0.0.1'),port=int(os.getenv('MYSQL_PORT','3306')),
      user=os.getenv('MYSQL_USER','root'),password=os.getenv('MYSQL_PASSWORD',''),database=os.getenv('MYSQL_DATABASE','swiftspan_co2'))
    cur=con.cursor()
    if not args.append:
      cur.execute('SET FOREIGN_KEY_CHECKS=0')
      # tracking_read_card is created by SQL/04 after the loader's normal run order.
      # If it already exists from an earlier attempt, clear it safely; otherwise skip it.
      cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s",
                  (os.getenv('MYSQL_DATABASE','swiftspan_co2'), 'tracking_read_card'))
      if cur.fetchone()[0]:
          cur.execute('TRUNCATE TABLE tracking_read_card')
      for table in ['bcnf_observation','bcnf_assignment','bcnf_sender','bcnf_service','bcnf_group_required_service',
                    'bcnf_coordinator','partial_observation','partial_sender','partial_service','flat_handover']:
          cur.execute(f'TRUNCATE TABLE {table}')
      cur.execute('SET FOREIGN_KEY_CHECKS=1')
    # Catalog rows are small and loaded once.
    cur.executemany('INSERT INTO bcnf_service VALUES (%s,%s,%s,%s)',[service(i) for i in range(1,21)])
    cur.executemany('INSERT INTO partial_service VALUES (%s,%s,%s,%s)',[service(i) for i in range(1,21)])
    cur.executemany('INSERT INTO bcnf_coordinator VALUES (%s,%s,%s)',[coord(i) for i in range(1,COORDINATORS+1)])
    cur.executemany('INSERT INTO bcnf_group_required_service VALUES (%s,%s)',[(g,s) for g in GROUPS for s in service_ids(g)])
    cur.executemany('INSERT INTO bcnf_sender VALUES (%s,%s,%s)',[sender(i) for i in range(1,actors+1)])
    cur.executemany('INSERT INTO partial_sender VALUES (%s,%s,%s)',[sender(i) for i in range(1,actors+1)])
    assignments=[]
    for sid in range(1,actors+1):
      for svcid in service_ids(GROUPS[(sid-1)%4]):
        cid=((sid*7+svcid*3)%COORDINATORS)+1
        assignments.append((sid,svcid,cid))
    cur.executemany('INSERT INTO bcnf_assignment VALUES (%s,%s,%s)',assignments)
    rng=random.Random(SEED)
    batch_flat=[]; batch_partial=[]; batch_obs=[]
    for sid in range(1,actors+1):
      for svcid in service_ids(GROUPS[(sid-1)%4]):
        for wave in WAVES:
          r=values(sid,svcid,wave,rng.randrange(0,101))
          batch_flat.append(r)
          batch_partial.append((r[0],r[3],r[7],r[8],r[9],r[10],r[11],r[12],r[13]))
          batch_obs.append((r[0],r[3],r[7],r[11]))
          if len(batch_flat)>=5000:
            cur.executemany('INSERT INTO flat_handover VALUES ('+','.join(['%s']*14)+')',batch_flat)
            cur.executemany('INSERT INTO partial_observation VALUES ('+','.join(['%s']*9)+')',batch_partial)
            cur.executemany('INSERT INTO bcnf_observation VALUES (%s,%s,%s,%s)',batch_obs)
            batch_flat=[];batch_partial=[];batch_obs=[]
    if batch_flat:
      cur.executemany('INSERT INTO flat_handover VALUES ('+','.join(['%s']*14)+')',batch_flat)
      cur.executemany('INSERT INTO partial_observation VALUES ('+','.join(['%s']*9)+')',batch_partial)
      cur.executemany('INSERT INTO bcnf_observation VALUES (%s,%s,%s,%s)',batch_obs)
    con.commit()
    print(f'Loaded {args.observations:,} observations for {actors:,} senders (seed 4211).')
    for table in ['flat_handover','partial_observation','bcnf_observation']:
      cur.execute(f'SELECT COUNT(*) FROM {table}')
      print(f'{table}: {cur.fetchone()[0]:,} rows')
    cur.close(); con.close()

if __name__=='__main__': main()
