#!/usr/bin/env python3
"""Reproducible local benchmark for CSA05 CO2 SwiftSpan Parcels.

The benchmark uses SQLite as a portable local verification engine. MySQL 8 DDL is
provided separately in SQL/. Results are machine-specific and are not claims about
production throughput.
"""
from __future__ import annotations
import argparse, csv, json, os, random, sqlite3, statistics, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs'
DBDIR = OUT / 'databases'
OUT.mkdir(parents=True, exist_ok=True)
DBDIR.mkdir(parents=True, exist_ok=True)
SEED = 4211
SIZES = [(10_000, 500), (100_000, 5_000), (600_000, 30_000)]
GROUPS = ['RG-A', 'RG-B', 'RG-C', 'RG-D']
SERVICES_PER_GROUP = 5
COORDINATORS = 35
WAVES = [1, 2, 3, 4]


def service_ids_for_group(group: str):
    idx = GROUPS.index(group)
    return list(range(idx * SERVICES_PER_GROUP + 1, (idx + 1) * SERVICES_PER_GROUP + 1))


def service_values(svc_id: int):
    return (svc_id, f'SVC-{svc_id:03d}', f'Service {svc_id:02d}', round(0.50 + (svc_id % 5) * 0.25, 2))


def coordinator_values(cid: int):
    return (cid, f'Coordinator {cid:02d}', f'Hub-{(cid - 1) % 7 + 1:02d}')


def band_values(completion: int):
    if completion < 39:
        return ('LOW', 1.25)
    if completion < 70:
        return ('STANDARD', 1.00)
    return ('HIGH', 0.85)


def sender_values(sender_id: int):
    group = GROUPS[(sender_id - 1) % len(GROUPS)]
    return (sender_id, f'Sender {sender_id:05d}', group)


def observation_values(sender_id: int, svc_id: int, wave: int, random_score: int):
    # Seeded score; a small, documented cohort is deliberately strong for useful
    # positive test cases. Service 5 at wave 4 is bounded above the threshold.
    if sender_id % 20 in (1, 2, 3, 4):
        completion = 60 + (random_score % 41)
    elif svc_id == 5 and wave == 4:
        completion = 39 + (random_score % 62)
    else:
        completion = random_score
    cid = ((sender_id * 7 + svc_id * 3) % COORDINATORS) + 1
    band, factor = band_values(completion)
    svc = service_values(svc_id)
    coord = coordinator_values(cid)
    sender = sender_values(sender_id)
    # Universal 14-attribute observation in assignment order.
    return (sender[0], sender[1], sender[2], svc[0], svc[1], svc[2], svc[3],
            wave, coord[0], coord[1], coord[2], completion, band, factor)


def iter_all_observations(actor_count: int):
    rng = random.Random(SEED)
    for sid in range(1, actor_count + 1):
        group = GROUPS[(sid - 1) % len(GROUPS)]
        for svc_id in service_ids_for_group(group):
            for wave in WAVES:
                yield observation_values(sid, svc_id, wave, rng.randrange(0, 101))


def chunks(iterable, size=10_000):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def create_flat(con):
    con.executescript('''
    PRAGMA foreign_keys=ON;
    CREATE TABLE flat_handover(
      SenderID INTEGER NOT NULL, SenderName TEXT NOT NULL, RouteGroup TEXT NOT NULL,
      ServiceID INTEGER NOT NULL, ServiceCode TEXT NOT NULL, ServiceName TEXT NOT NULL,
      VolumeWeight REAL NOT NULL, DispatchWave INTEGER NOT NULL,
      CoordinatorID INTEGER NOT NULL, CoordinatorName TEXT NOT NULL, Hub TEXT NOT NULL,
      Completion INTEGER NOT NULL CHECK(Completion BETWEEN 0 AND 100),
      ServiceBand TEXT NOT NULL, RouteFactor REAL NOT NULL,
      PRIMARY KEY(SenderID, ServiceID, DispatchWave)
    );
    CREATE INDEX ix_flat_sender_wave ON flat_handover(SenderID, DispatchWave);
    CREATE INDEX ix_flat_service ON flat_handover(ServiceID);
    ''')


def create_partial(con):
    con.executescript('''
    PRAGMA foreign_keys=ON;
    CREATE TABLE partial_sender(SenderID INTEGER PRIMARY KEY, SenderName TEXT NOT NULL, RouteGroup TEXT NOT NULL);
    CREATE TABLE partial_service(ServiceID INTEGER PRIMARY KEY, ServiceCode TEXT NOT NULL UNIQUE, ServiceName TEXT NOT NULL, VolumeWeight REAL NOT NULL);
    CREATE TABLE partial_observation(
      SenderID INTEGER NOT NULL, ServiceID INTEGER NOT NULL, DispatchWave INTEGER NOT NULL,
      CoordinatorID INTEGER NOT NULL, CoordinatorName TEXT NOT NULL, Hub TEXT NOT NULL,
      Completion INTEGER NOT NULL CHECK(Completion BETWEEN 0 AND 100),
      ServiceBand TEXT NOT NULL, RouteFactor REAL NOT NULL,
      PRIMARY KEY(SenderID, ServiceID, DispatchWave),
      FOREIGN KEY(SenderID) REFERENCES partial_sender(SenderID),
      FOREIGN KEY(ServiceID) REFERENCES partial_service(ServiceID)
    );
    CREATE INDEX ix_partial_sender_wave ON partial_observation(SenderID, DispatchWave);
    CREATE INDEX ix_partial_service ON partial_observation(ServiceID);
    ''')


def create_bcnf(con):
    con.executescript('''
    PRAGMA foreign_keys=ON;
    CREATE TABLE sender(SenderID INTEGER PRIMARY KEY, SenderName TEXT NOT NULL, RouteGroup TEXT NOT NULL);
    CREATE TABLE service(ServiceID INTEGER PRIMARY KEY, ServiceCode TEXT NOT NULL UNIQUE, ServiceName TEXT NOT NULL, VolumeWeight REAL NOT NULL CHECK(VolumeWeight > 0));
    CREATE TABLE coordinator(CoordinatorID INTEGER PRIMARY KEY, CoordinatorName TEXT NOT NULL, Hub TEXT NOT NULL);
    CREATE TABLE assignment(SenderID INTEGER NOT NULL, ServiceID INTEGER NOT NULL, CoordinatorID INTEGER NOT NULL,
      PRIMARY KEY(SenderID, ServiceID),
      FOREIGN KEY(SenderID) REFERENCES sender(SenderID),
      FOREIGN KEY(ServiceID) REFERENCES service(ServiceID),
      FOREIGN KEY(CoordinatorID) REFERENCES coordinator(CoordinatorID));
    CREATE TABLE observation(SenderID INTEGER NOT NULL, ServiceID INTEGER NOT NULL, DispatchWave INTEGER NOT NULL,
      Completion INTEGER NOT NULL CHECK(Completion BETWEEN 0 AND 100),
      PRIMARY KEY(SenderID, ServiceID, DispatchWave),
      FOREIGN KEY(SenderID, ServiceID) REFERENCES assignment(SenderID, ServiceID));
    CREATE TABLE completion_policy(Completion INTEGER PRIMARY KEY CHECK(Completion BETWEEN 0 AND 100), ServiceBand TEXT NOT NULL);
    CREATE TABLE service_band_policy(ServiceBand TEXT PRIMARY KEY, RouteFactor REAL NOT NULL CHECK(RouteFactor > 0));
    CREATE TABLE group_required_service(RouteGroup TEXT NOT NULL, ServiceID INTEGER NOT NULL,
      PRIMARY KEY(RouteGroup, ServiceID), FOREIGN KEY(ServiceID) REFERENCES service(ServiceID));
    CREATE INDEX ix_obs_sender_wave ON observation(SenderID, DispatchWave);
    CREATE INDEX ix_obs_service_wave_completion ON observation(ServiceID, DispatchWave, Completion);
    CREATE INDEX ix_assignment_coord ON assignment(CoordinatorID);
    ''')


def seed_static(con, design):
    if design == 'partial':
        con.executemany('INSERT INTO partial_service VALUES(?,?,?,?)', [service_values(i) for i in range(1, 21)])
        # Coordinator identity is deliberately not factored out in this partial design.
        for group in GROUPS:
            for svc in service_ids_for_group(group):
                # no separate group relation in partial baseline; cohort rules are documented in generator.
                pass
    elif design == 'bcnf':
        con.executemany('INSERT INTO service VALUES(?,?,?,?)', [service_values(i) for i in range(1, 21)])
        con.executemany('INSERT INTO coordinator VALUES(?,?,?)', [coordinator_values(i) for i in range(1, COORDINATORS + 1)])
        con.executemany('INSERT INTO completion_policy VALUES(?,?)', [(v, band_values(v)[0]) for v in range(101)])
        con.executemany('INSERT INTO service_band_policy VALUES(?,?)', [('LOW',1.25),('STANDARD',1.0),('HIGH',0.85)])
        con.executemany('INSERT INTO group_required_service VALUES(?,?)', [(g, s) for g in GROUPS for s in service_ids_for_group(g)])


def populate_design(db_path: Path, design: str, actors: int):
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute('PRAGMA journal_mode=DELETE')
    con.execute('PRAGMA synchronous=NORMAL')
    con.execute('PRAGMA temp_store=MEMORY')
    if design == 'flat':
        create_flat(con)
    elif design == 'partial':
        create_partial(con)
    else:
        create_bcnf(con)
    seed_static(con, design)

    if design == 'flat':
        sql = 'INSERT INTO flat_handover VALUES(' + ','.join(['?'] * 14) + ')'
        for batch in chunks(iter_all_observations(actors)):
            con.executemany(sql, batch)
    elif design == 'partial':
        con.executemany('INSERT INTO partial_sender VALUES(?,?,?)', [sender_values(i) for i in range(1, actors + 1)])
        sql = 'INSERT INTO partial_observation VALUES(' + ','.join(['?'] * 9) + ')'
        for batch in chunks(iter_all_observations(actors)):
            compact = [(r[0],r[3],r[7],r[8],r[9],r[10],r[11],r[12],r[13]) for r in batch]
            con.executemany(sql, compact)
    else:
        con.executemany('INSERT INTO sender VALUES(?,?,?)', [sender_values(i) for i in range(1, actors + 1)])
        # one coordinator per sender/service scope; deterministic and stable across waves.
        assn = []
        for sid in range(1, actors + 1):
            group = GROUPS[(sid - 1) % 4]
            for svc_id in service_ids_for_group(group):
                cid = ((sid * 7 + svc_id * 3) % COORDINATORS) + 1
                assn.append((sid, svc_id, cid))
        con.executemany('INSERT INTO assignment VALUES(?,?,?)', assn)
        obs_gen = ((r[0],r[3],r[7],r[11]) for r in iter_all_observations(actors))
        for batch in chunks(obs_gen):
            con.executemany('INSERT INTO observation VALUES(?,?,?,?)', batch)
        # Read projection is created below after normalized source is committed.
    con.commit()
    source_storage = db_bytes(con)

    if design == 'bcnf':
        # Transactional, denormalised tracking read card for Task 12.
        con.executescript('''
        CREATE TABLE tracking_read_card(
          SenderID INTEGER NOT NULL, ServiceID INTEGER NOT NULL, DispatchWave INTEGER NOT NULL,
          SenderName TEXT NOT NULL, RouteGroup TEXT NOT NULL, ServiceCode TEXT NOT NULL,
          ServiceName TEXT NOT NULL, VolumeWeight REAL NOT NULL,
          CoordinatorID INTEGER NOT NULL, CoordinatorName TEXT NOT NULL, Hub TEXT NOT NULL,
          Completion INTEGER NOT NULL, ServiceBand TEXT NOT NULL, RouteFactor REAL NOT NULL,
          AdjustedIndex REAL NOT NULL,
          PRIMARY KEY(SenderID, ServiceID, DispatchWave));
        INSERT INTO tracking_read_card
        SELECT s.SenderID, sv.ServiceID, o.DispatchWave, s.SenderName, s.RouteGroup,
               sv.ServiceCode, sv.ServiceName, sv.VolumeWeight,
               c.CoordinatorID, c.CoordinatorName, c.Hub, o.Completion,
               cp.ServiceBand, bp.RouteFactor,
               ROUND(o.Completion * sv.VolumeWeight * bp.RouteFactor, 4)
        FROM observation o JOIN sender s USING(SenderID)
        JOIN service sv USING(ServiceID)
        JOIN assignment a USING(SenderID, ServiceID)
        JOIN coordinator c USING(CoordinatorID)
        JOIN completion_policy cp USING(Completion)
        JOIN service_band_policy bp USING(ServiceBand);
        CREATE INDEX ix_card_sender_wave ON tracking_read_card(SenderID, DispatchWave);
        ''')
        con.commit()
    # Analyze / optimize after index creation for comparable query tests.
    con.execute('ANALYZE')
    con.commit()
    return con, source_storage


def timed_query(con, sql, params, repeats=9):
    con.execute(sql, params).fetchall()  # warm-up
    vals = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        con.execute(sql, params).fetchall()
        vals.append((time.perf_counter() - t0) * 1000.0)
    return round(statistics.median(vals), 4)


def update_trial(con, sql, params):
    con.execute('BEGIN')
    con.execute(sql, params)
    n = con.execute('SELECT changes()').fetchone()[0]
    con.rollback()
    return n


def integrity_tests(con, design):
    results = []
    try:
        if design == 'flat':
            con.execute('INSERT INTO flat_handover VALUES(1,"x","RG-A",1,"SVC-001","x",1,1,1,"x","Hub",101,"HIGH",0.8)')
        elif design == 'partial':
            con.execute('INSERT INTO partial_observation VALUES(1,1,1,1,"x","Hub",101,"HIGH",0.8)')
        else:
            con.execute('INSERT INTO observation VALUES(1,1,99,101)')
        results.append('CHECK constraint: unexpected pass')
    except sqlite3.IntegrityError as e:
        results.append(f'CHECK constraint rejected invalid Completion: {e}')
        con.rollback()
    try:
        if design == 'flat':
            con.execute('INSERT INTO flat_handover SELECT * FROM flat_handover LIMIT 1')
        elif design == 'partial':
            row = con.execute('SELECT * FROM partial_observation LIMIT 1').fetchone()
            con.execute('INSERT INTO partial_observation VALUES(?,?,?,?,?,?,?,?,?)', row)
        else:
            row = con.execute('SELECT * FROM observation LIMIT 1').fetchone()
            con.execute('INSERT INTO observation VALUES(?,?,?,?)', row)
        results.append('PRIMARY KEY: unexpected pass')
    except sqlite3.IntegrityError as e:
        results.append(f'PRIMARY KEY rejected duplicate observation: {e}')
        con.rollback()
    if design == 'bcnf':
        try:
            con.execute('INSERT INTO assignment VALUES(999999,1,1)')
            results.append('FOREIGN KEY: unexpected pass')
        except sqlite3.IntegrityError as e:
            results.append(f'FOREIGN KEY rejected orphan sender: {e}')
            con.rollback()
    return results


def db_bytes(con):
    page_size = con.execute('PRAGMA page_size').fetchone()[0]
    page_count = con.execute('PRAGMA page_count').fetchone()[0]
    return int(page_count), int(page_size), int(page_count * page_size)


def count_rows(con, table):
    return con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]


def run_all():
    summary = []
    update_rows = []
    integrity = {}
    equivalence = []
    for obs_count, actors in SIZES:
        print(f'\n=== DATASET {obs_count:,} observations / {actors:,} senders ===')
        size_metrics = {}
        for design in ['flat','partial','bcnf']:
            db = DBDIR / f'{design}_{obs_count}.sqlite'
            t0 = time.perf_counter()
            con, source_storage = populate_design(db, design, actors)
            load_s = time.perf_counter() - t0
            if design == 'flat':
                table = 'flat_handover'
                actor_sql = 'SELECT * FROM flat_handover WHERE SenderID=? AND DispatchWave=4 ORDER BY ServiceID'
                update_sql = 'UPDATE flat_handover SET ServiceName=? WHERE ServiceID=?'
                join_count = 0
                row_count = count_rows(con, table)
                updates = update_trial(con, update_sql, ('Service 01 - changed',1))
                coord_updates = update_trial(con, 'UPDATE flat_handover SET CoordinatorName=? WHERE CoordinatorID=?', ('Temporary coordinator',1))
                qms = timed_query(con, actor_sql, (1,))
                chk = integrity_tests(con, design)
                agg = con.execute('SELECT COUNT(*), SUM(Completion), SUM(ServiceID) FROM flat_handover').fetchone()
            elif design == 'partial':
                table = 'partial_observation'
                actor_sql = '''SELECT s.SenderID,s.SenderName,s.RouteGroup,sv.ServiceID,sv.ServiceCode,sv.ServiceName,sv.VolumeWeight,
                       o.DispatchWave,o.CoordinatorID,o.CoordinatorName,o.Hub,o.Completion,o.ServiceBand,o.RouteFactor
                       FROM partial_observation o JOIN partial_sender s USING(SenderID)
                       JOIN partial_service sv USING(ServiceID)
                       WHERE o.SenderID=? AND o.DispatchWave=4 ORDER BY o.ServiceID'''
                update_sql = 'UPDATE partial_service SET ServiceName=? WHERE ServiceID=?'
                join_count = 2
                row_count = count_rows(con, table)
                updates = update_trial(con, update_sql, ('Service 01 - changed',1))
                coord_updates = update_trial(con, 'UPDATE partial_observation SET CoordinatorName=? WHERE CoordinatorID=?', ('Temporary coordinator',1))
                qms = timed_query(con, actor_sql, (1,))
                chk = integrity_tests(con, design)
                agg = con.execute('SELECT COUNT(*), SUM(Completion), SUM(ServiceID) FROM partial_observation').fetchone()
            else:
                table = 'observation'
                actor_sql = '''SELECT s.SenderID,s.SenderName,s.RouteGroup,sv.ServiceID,sv.ServiceCode,sv.ServiceName,sv.VolumeWeight,
                       o.DispatchWave,c.CoordinatorID,c.CoordinatorName,c.Hub,o.Completion,cp.ServiceBand,bp.RouteFactor
                       FROM observation o JOIN sender s USING(SenderID)
                       JOIN service sv USING(ServiceID)
                       JOIN assignment a USING(SenderID,ServiceID)
                       JOIN coordinator c USING(CoordinatorID)
                       JOIN completion_policy cp USING(Completion)
                       JOIN service_band_policy bp USING(ServiceBand)
                       WHERE o.SenderID=? AND o.DispatchWave=4 ORDER BY o.ServiceID'''
                update_sql = 'UPDATE service SET ServiceName=? WHERE ServiceID=?'
                join_count = 6
                row_count = count_rows(con, table)
                updates = update_trial(con, update_sql, ('Service 01 - changed',1))
                coord_updates = update_trial(con, 'UPDATE coordinator SET CoordinatorName=? WHERE CoordinatorID=?', ('Temporary coordinator',1))
                qms = timed_query(con, actor_sql, (1,))
                chk = integrity_tests(con, design)
                agg = con.execute('SELECT COUNT(*), SUM(Completion), SUM(ServiceID) FROM observation').fetchone()
                card_sql = 'SELECT * FROM tracking_read_card WHERE SenderID=? AND DispatchWave=4 ORDER BY ServiceID'
                card_ms = timed_query(con, card_sql, (1,))
                card_rows = count_rows(con,'tracking_read_card')
                # Refresh timing: rebuild contents inside a transaction, preserving snapshot consistency.
                t0 = time.perf_counter()
                con.execute('BEGIN')
                con.execute('DELETE FROM tracking_read_card')
                con.execute('''INSERT INTO tracking_read_card
                    SELECT s.SenderID, sv.ServiceID, o.DispatchWave, s.SenderName, s.RouteGroup,
                    sv.ServiceCode, sv.ServiceName, sv.VolumeWeight, c.CoordinatorID, c.CoordinatorName, c.Hub,
                    o.Completion, cp.ServiceBand, bp.RouteFactor,
                    ROUND(o.Completion * sv.VolumeWeight * bp.RouteFactor,4)
                    FROM observation o JOIN sender s USING(SenderID)
                    JOIN service sv USING(ServiceID) JOIN assignment a USING(SenderID,ServiceID)
                    JOIN coordinator c USING(CoordinatorID) JOIN completion_policy cp USING(Completion)
                    JOIN service_band_policy bp USING(ServiceBand)''')
                con.commit()
                refresh_s = time.perf_counter() - t0
            pages, page_size, bytes_used = db_bytes(con)
            size_metrics[design] = {'rows':row_count,'load_s':round(load_s,4),'query_ms':qms,
                                    'joins':join_count,'pages':pages,'page_size':page_size,
                                    'allocated_bytes':bytes_used,'allocated_mib':round(bytes_used/1048576,3),
                                    'source_pages':source_storage[0], 'source_allocated_bytes':source_storage[2],
                                    'source_allocated_mib':round(source_storage[2]/1048576,3),
                                    'aggregate':list(agg)}
            update_rows.append({'observations':obs_count,'design':design,'rows_updated_for_ServiceID_1':updates,'rows_updated_for_CoordinatorID_1':coord_updates})
            integrity[f'{obs_count}_{design}'] = chk
            print(f'{design:7s}: load={load_s:.3f}s query={qms:.4f}ms joins={join_count} allocated={bytes_used/1048576:.2f}MiB rowsUpdated={updates}')
            if design == 'bcnf':
                size_metrics[design]['read_card_query_ms'] = card_ms
                size_metrics[design]['read_card_rows'] = card_rows
                size_metrics[design]['read_card_refresh_s'] = round(refresh_s,4)
                print(f'        read-card query={card_ms:.4f}ms refresh={refresh_s:.3f}s')
            con.close()
        # All 3 schemas must return same count/sum checksum from logically identical seed.
        a = size_metrics['flat']['aggregate']
        b = size_metrics['partial']['aggregate']
        c = size_metrics['bcnf']['aggregate']
        same = (a == b == c)
        equivalence.append({'observations':obs_count,'flat_checksum':a,'partial_checksum':b,'bcnf_checksum':c,'equivalent':same})
        summary.append({'observations':obs_count,'actors':actors,**size_metrics})
        print('equivalence:', 'PASS' if same else 'FAIL', a, b, c)
    with open(OUT/'benchmark_summary.json','w') as f: json.dump(summary,f,indent=2)
    with open(OUT/'update_rows.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(update_rows[0]));w.writeheader();w.writerows(update_rows)
    with open(OUT/'integrity_messages.json','w') as f: json.dump(integrity,f,indent=2)
    with open(OUT/'equivalence_checks.json','w') as f: json.dump(equivalence,f,indent=2)
    with open(OUT/'benchmark_summary.csv','w',newline='') as f:
        fields=['observations','actors','design','rows','load_s','query_ms','joins','pages','page_size','allocated_bytes','allocated_mib','source_pages','source_allocated_bytes','source_allocated_mib','read_card_query_ms','read_card_refresh_s']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in summary:
            for design in ['flat','partial','bcnf']:
                d=row[design]
                w.writerow({'observations':row['observations'],'actors':row['actors'],'design':design,
                            'rows':d['rows'],'load_s':d['load_s'],'query_ms':d['query_ms'],'joins':d['joins'],
                            'pages':d['pages'],'page_size':d['page_size'],'allocated_bytes':d['allocated_bytes'],
                            'allocated_mib':d['allocated_mib'],'source_pages':d['source_pages'],
                            'source_allocated_bytes':d['source_allocated_bytes'],'source_allocated_mib':d['source_allocated_mib'],
                            'read_card_query_ms':d.get('read_card_query_ms',''),
                            'read_card_refresh_s':d.get('read_card_refresh_s','')})
    last_integrity_key = f'{SIZES[-1][0]}_bcnf'
    print(f'\n=== INTEGRITY TEST MESSAGES ({SIZES[-1][0]:,} BCNF) ===')
    for m in integrity[last_integrity_key]: print(m)
    print('\n=== RESULT FILES ===')
    print(OUT/'benchmark_summary.csv')
    print(OUT/'integrity_messages.json')
    print(OUT/'equivalence_checks.json')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--quick', action='store_true', help='run only 10k + 100k')
    args = p.parse_args()
    if args.quick:
        SIZES = SIZES[:2]
    run_all()
