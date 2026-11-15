#!/usr/bin/env python3
"""Reproducible SQLite validation harness for the Meridian Museum model.

MySQL 8.0 DDL and a MySQL loader are supplied separately. This harness is a
portable local validation path and does NOT claim to be a MySQL execution.
It uses a fixed seed (4211), tests constraints, runs eight use-case queries,
and measures median query time for 100, 1,000, 10,000 and 100,000 lenders.
"""
from __future__ import annotations
import argparse, json, random, sqlite3, statistics, time
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

SCHEMA = r"""
PRAGMA foreign_keys = ON;
CREATE TABLE party(party_id INTEGER PRIMARY KEY, party_kind TEXT NOT NULL CHECK(party_kind IN ('PERSON','ORGANIZATION')));
CREATE TABLE person(party_id INTEGER PRIMARY KEY REFERENCES party(party_id), first_name TEXT NOT NULL, last_name TEXT NOT NULL, email TEXT);
CREATE TABLE organization(party_id INTEGER PRIMARY KEY REFERENCES party(party_id), legal_name TEXT NOT NULL);
CREATE TABLE person_phone(party_id INTEGER NOT NULL REFERENCES person(party_id), phone_type TEXT NOT NULL, phone_number TEXT NOT NULL, PRIMARY KEY(party_id,phone_type,phone_number));
CREATE TABLE lender(party_id INTEGER PRIMARY KEY REFERENCES party(party_id), lender_code TEXT NOT NULL UNIQUE, joined_on TEXT NOT NULL);
CREATE TABLE employee(person_id INTEGER PRIMARY KEY REFERENCES person(party_id), employee_no TEXT NOT NULL UNIQUE, role TEXT NOT NULL CHECK(role IN ('CURATOR','REGISTRAR')));
CREATE TABLE curator(person_id INTEGER PRIMARY KEY REFERENCES employee(person_id), specialisation TEXT NOT NULL);
CREATE TABLE registrar(person_id INTEGER PRIMARY KEY REFERENCES employee(person_id), clearance_level TEXT NOT NULL);
CREATE TABLE collection_unit(unit_id INTEGER PRIMARY KEY, unit_name TEXT UNIQUE NOT NULL);
CREATE TABLE collection_type(collection_type_id INTEGER PRIMARY KEY, type_name TEXT UNIQUE NOT NULL);
CREATE TABLE artifact(artifact_id INTEGER PRIMARY KEY, accession_no TEXT NOT NULL UNIQUE, unit_id INTEGER NOT NULL REFERENCES collection_unit(unit_id), collection_type_id INTEGER NOT NULL REFERENCES collection_type(collection_type_id), owner_party_id INTEGER NOT NULL REFERENCES party(party_id), title TEXT NOT NULL, estimated_value REAL, ownership_known_from TEXT);
CREATE TABLE loan(loan_id INTEGER PRIMARY KEY, loan_no TEXT UNIQUE NOT NULL, lender_party_id INTEGER NOT NULL REFERENCES lender(party_id), responsible_curator_id INTEGER NOT NULL REFERENCES curator(person_id), processing_registrar_id INTEGER NOT NULL REFERENCES registrar(person_id), loan_date TEXT NOT NULL, expected_return_date TEXT NOT NULL, actual_return_date TEXT, loan_status TEXT NOT NULL CHECK(loan_status IN ('DRAFT','APPROVED','ACTIVE','CLOSED','CANCELLED')), purpose TEXT NOT NULL, CHECK(expected_return_date>=loan_date), CHECK(actual_return_date IS NULL OR actual_return_date>=loan_date));
CREATE TABLE loan_object(loan_id INTEGER NOT NULL REFERENCES loan(loan_id), artifact_id INTEGER NOT NULL REFERENCES artifact(artifact_id), custody_start TEXT NOT NULL, custody_end TEXT, loan_line_description TEXT NOT NULL, loan_line_value REAL NOT NULL CHECK(loan_line_value>=0), PRIMARY KEY(loan_id,artifact_id), CHECK(custody_end IS NULL OR custody_end>=custody_start));
CREATE INDEX ix_loan_object_artifact_dates ON loan_object(artifact_id,custody_start,custody_end);
CREATE TABLE exhibition(exhibition_id INTEGER PRIMARY KEY, exhibition_code TEXT UNIQUE NOT NULL, exhibition_name TEXT NOT NULL, opens_on TEXT NOT NULL, closes_on TEXT NOT NULL, CHECK(closes_on>=opens_on));
CREATE TABLE display_slot(exhibition_id INTEGER NOT NULL REFERENCES exhibition(exhibition_id), slot_no INTEGER NOT NULL CHECK(slot_no>0), gallery_name TEXT NOT NULL, position_description TEXT NOT NULL, PRIMARY KEY(exhibition_id,slot_no));
CREATE TABLE placement(placement_id INTEGER PRIMARY KEY, loan_id INTEGER NOT NULL, artifact_id INTEGER NOT NULL, exhibition_id INTEGER NOT NULL, slot_no INTEGER NOT NULL, placement_start TEXT NOT NULL, placement_end TEXT, display_caption TEXT, FOREIGN KEY(loan_id,artifact_id) REFERENCES loan_object(loan_id,artifact_id), FOREIGN KEY(exhibition_id,slot_no) REFERENCES display_slot(exhibition_id,slot_no), CHECK(placement_end IS NULL OR placement_end>=placement_start));
CREATE INDEX ix_placement_slot_dates ON placement(exhibition_id,slot_no,placement_start,placement_end);
CREATE TABLE notification_contact(contact_id INTEGER PRIMARY KEY, person_id INTEGER REFERENCES person(party_id), organization_id INTEGER REFERENCES organization(party_id), contact_label TEXT NOT NULL, email TEXT, phone TEXT, CHECK((person_id IS NOT NULL AND organization_id IS NULL) OR (person_id IS NULL AND organization_id IS NOT NULL)));
CREATE TABLE loan_notification_contact(loan_id INTEGER NOT NULL REFERENCES loan(loan_id), contact_id INTEGER NOT NULL REFERENCES notification_contact(contact_id), notification_purpose TEXT NOT NULL, PRIMARY KEY(loan_id,contact_id,notification_purpose));
CREATE TABLE condition_report(report_id INTEGER PRIMARY KEY, loan_id INTEGER NOT NULL, artifact_id INTEGER NOT NULL, inspector_person_id INTEGER NOT NULL REFERENCES employee(person_id), report_date TEXT NOT NULL, report_stage TEXT NOT NULL CHECK(report_stage IN ('RECEIPT','DURING_CUSTODY','RETURN')), condition_code TEXT NOT NULL CHECK(condition_code IN ('EXCELLENT','GOOD','FAIR','POOR','DAMAGED')), notes TEXT NOT NULL, FOREIGN KEY(loan_id,artifact_id) REFERENCES loan_object(loan_id,artifact_id));
CREATE INDEX ix_condition_artifact_date ON condition_report(artifact_id,report_date);
CREATE TRIGGER person_party_kind BEFORE INSERT ON person
WHEN (SELECT party_kind FROM party WHERE party_id=NEW.party_id) <> 'PERSON'
BEGIN SELECT RAISE(ABORT,'Person subtype does not match PARTY.PartyKind'); END;
CREATE TRIGGER organization_party_kind BEFORE INSERT ON organization
WHEN (SELECT party_kind FROM party WHERE party_id=NEW.party_id) <> 'ORGANIZATION'
BEGIN SELECT RAISE(ABORT,'Organization subtype does not match PARTY.PartyKind'); END;
CREATE TRIGGER curator_role_check BEFORE INSERT ON curator
WHEN (SELECT role FROM employee WHERE person_id=NEW.person_id) <> 'CURATOR'
BEGIN SELECT RAISE(ABORT,'CURATOR subtype requires employee role CURATOR'); END;
CREATE TRIGGER registrar_role_check BEFORE INSERT ON registrar
WHEN (SELECT role FROM employee WHERE person_id=NEW.person_id) <> 'REGISTRAR'
BEGIN SELECT RAISE(ABORT,'REGISTRAR subtype requires employee role REGISTRAR'); END;
CREATE TRIGGER placement_no_overlap BEFORE INSERT ON placement
WHEN EXISTS (SELECT 1 FROM placement p WHERE p.exhibition_id=NEW.exhibition_id
 AND p.slot_no=NEW.slot_no AND NEW.placement_start<=COALESCE(p.placement_end,'9999-12-31')
 AND COALESCE(NEW.placement_end,'9999-12-31')>=p.placement_start)
BEGIN SELECT RAISE(ABORT,'Overlapping placement in display slot'); END;
CREATE TRIGGER custody_no_overlap BEFORE INSERT ON loan_object
WHEN EXISTS (SELECT 1 FROM loan_object x WHERE x.artifact_id=NEW.artifact_id
 AND NEW.custody_start<=COALESCE(x.custody_end,'9999-12-31')
 AND COALESCE(NEW.custody_end,'9999-12-31')>=x.custody_start)
BEGIN SELECT RAISE(ABORT,'Overlapping custody period for artifact'); END;
"""

QUERIES = {
    "Q1_overdue_open": """SELECT loan_id, loan_no, lender_party_id, expected_return_date FROM loan WHERE actual_return_date IS NULL AND loan_status='ACTIVE' AND expected_return_date < '2026-11-13' ORDER BY expected_return_date LIMIT 5""",
    "Q2_no_condition_evidence": """SELECT a.artifact_id, a.accession_no, a.title FROM artifact a LEFT JOIN loan_object lo ON lo.artifact_id=a.artifact_id LEFT JOIN condition_report cr ON cr.loan_id=lo.loan_id AND cr.artifact_id=lo.artifact_id WHERE cr.report_id IS NULL ORDER BY a.artifact_id LIMIT 5""",
    "Q3_custody_history": """SELECT a.accession_no, l.loan_no, l.loan_status, lo.custody_start, lo.custody_end FROM artifact a JOIN loan_object lo ON lo.artifact_id=a.artifact_id JOIN loan l ON l.loan_id=lo.loan_id WHERE a.artifact_id=? ORDER BY lo.custody_start""",
    "Q4_condition_attention": """SELECT cr.report_id, a.accession_no, cr.report_date, cr.condition_code FROM condition_report cr JOIN artifact a ON a.artifact_id=cr.artifact_id WHERE cr.condition_code IN ('POOR','DAMAGED') ORDER BY cr.report_date DESC LIMIT 5""",
    "Q5_unit_loan_counts": """SELECT cu.unit_name, COUNT(DISTINCT lo.loan_id), COUNT(DISTINCT lo.artifact_id) FROM collection_unit cu JOIN artifact a ON a.unit_id=cu.unit_id JOIN loan_object lo ON lo.artifact_id=a.artifact_id GROUP BY cu.unit_id,cu.unit_name ORDER BY cu.unit_id""",
    "Q6_slot_occupancy": """SELECT e.exhibition_code, ds.slot_no, p.artifact_id, p.placement_start, p.placement_end FROM exhibition e JOIN display_slot ds ON ds.exhibition_id=e.exhibition_id LEFT JOIN placement p ON p.exhibition_id=ds.exhibition_id AND p.slot_no=ds.slot_no ORDER BY e.exhibition_id,ds.slot_no LIMIT 8""",
    "Q7_open_loan_contacts": """SELECT l.loan_no, nc.contact_label, nc.email, l.expected_return_date FROM loan l JOIN loan_notification_contact lnc ON lnc.loan_id=l.loan_id JOIN notification_contact nc ON nc.contact_id=lnc.contact_id WHERE l.actual_return_date IS NULL ORDER BY l.loan_id LIMIT 5""",
    "Q8_latest_condition": """SELECT a.accession_no, cr.report_date, cr.report_stage, cr.condition_code FROM artifact a JOIN condition_report cr ON cr.artifact_id=a.artifact_id WHERE cr.report_date=(SELECT MAX(cr2.report_date) FROM condition_report cr2 WHERE cr2.artifact_id=a.artifact_id) ORDER BY a.artifact_id LIMIT 5""",
}
PARAMS = {"Q3_custody_history": (3,)}


def build_db(n: int, db_path: Path) -> dict:
    if db_path.exists(): db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    rng = random.Random(4211)
    # Fixed operational backbone: 8 collection units, 6 types, 35 curators, 5 registrars.
    con.executemany("INSERT INTO collection_unit VALUES (?,?)", [(i, f"Unit {i:02d}") for i in range(1,9)])
    con.executemany("INSERT INTO collection_type VALUES (?,?)", [(i, x) for i,x in enumerate(["Painting","Sculpture","Textile","Ceramic","Manuscript","Photograph"],1)])
    parties=[]; persons=[]; lenders=[]; employees=[]; curators=[]; registrars=[]
    # First 35 + 5 are museum staff. Remaining persons are lenders.
    staff_total=40
    for pid in range(1, staff_total+n+1):
        parties.append((pid,"PERSON"))
        persons.append((pid, f"Person{pid:06d}", f"Surname{pid%997:03d}", f"p{pid}@example.test"))
    for i in range(1,n+1):
        pid=staff_total+i
        lenders.append((pid,f"LEN-{i:06d}","2024-01-01"))
    for i in range(1,staff_total+1):
        employees.append((i,f"EMP-{i:04d}","CURATOR" if i<=35 else "REGISTRAR"))
        if i<=35: curators.append((i,f"Specialisation {((i-1)%7)+1}"))
        else: registrars.append((i,"STANDARD"))
    con.executemany("INSERT INTO party VALUES (?,?)", parties)
    con.executemany("INSERT INTO person VALUES (?,?,?,?)", persons)
    con.executemany("INSERT INTO lender VALUES (?,?,?)", lenders)
    con.executemany("INSERT INTO employee VALUES (?,?,?)", employees)
    con.executemany("INSERT INTO curator VALUES (?,?)", curators)
    con.executemany("INSERT INTO registrar VALUES (?,?)", registrars)
    con.executemany("INSERT INTO person_phone VALUES (?,?,?)", [(i,"MOBILE",f"+91-90000{i:05d}") for i in range(1, staff_total+n+1)])
    con.executemany("INSERT INTO organization VALUES (?,?)", [])
    # Create a small organization pool and contacts to exercise union category.
    org_ids=[]
    for j in range(1, min(11, max(3, n//10+1))):
        oid=staff_total+n+j
        con.execute("INSERT INTO party VALUES (?, 'ORGANIZATION')", (oid,))
        con.execute("INSERT INTO organization VALUES (?,?)", (oid,f"Museum Partner {j:02d}"))
        org_ids.append(oid)
    artifacts=[]; loans=[]; loan_objects=[]; reports=[]; placements=[]; contacts=[]; loan_contacts=[]
    today=date(2026,11,13)
    for i in range(1, 2*n+1):
        lender_pid=staff_total+((i-1)//2)+1
        owner_pid = lender_pid if i%5 else rng.randint(staff_total+1, staff_total+n)
        unit=((i-1)%8)+1; ctype=((i-1)%6)+1
        artifacts.append((i,f"MM-{i:06d}",unit,ctype,owner_pid,f"Museum artifact {i:06d}",float(1000+(i%10000)*12.5),None if i%11==0 else "2020-01-01"))
    for i in range(1,n+1):
        lender_pid=staff_total+i
        start=date(2026,1,1)+timedelta(days=(i*7)%300)
        # repeatable mix: 25% overdue active, 25% active not due, 50% closed
        if i%4==0:
            status="ACTIVE"; actual=None; due=today-timedelta(days=1+(i%20))
        elif i%4==1:
            status="ACTIVE"; actual=None; due=today+timedelta(days=5+(i%30))
        else:
            status="CLOSED"; due=start+timedelta(days=45); actual=due+timedelta(days=i%3)
        loans.append((i,f"LN-{i:06d}",lender_pid,((i-1)%35)+1,36+((i-1)%5),start.isoformat(),due.isoformat(),actual.isoformat() if actual else None,status,"Temporary exhibition loan"))
        for k in range(2):
            art_id=2*(i-1)+k+1
            custody_end=actual.isoformat() if actual else None
            loan_objects.append((i,art_id,start.isoformat(),custody_end,f"Loan register description for artifact {art_id}",float(5000+art_id*3)))
            # Every 4th artifact has no report, making the missing-evidence query meaningful.
            if art_id%4 != 0:
                ccode = "DAMAGED" if art_id%17==0 else "POOR" if art_id%13==0 else "GOOD" if art_id%3 else "FAIR"
                rdate=(start+timedelta(days=1)).isoformat()
                reports.append((len(reports)+1,i,art_id,((i-1)%35)+1,rdate,"RECEIPT",ccode,"Synthetic validation note"))
            if art_id%2==0:
                exhibition_id=((i-1)%12)+1
                slot_no=((i-1)//12)%10+1
                place_start=date(2026,1,1)+timedelta(days=((i-1)//120)*7)
                placements.append((len(placements)+1,i,art_id,exhibition_id,slot_no,place_start.isoformat(),(place_start+timedelta(days=6)).isoformat(),f"Gallery caption for artifact {art_id}"))
    # Re-loan artifact 3 after its earlier closed custody interval to demonstrate
    # successive loans for one physical object without overlapping custody.
    reloan_id=n+1
    loans.append((reloan_id,"LN-RET-000001",staff_total+1,1,36,"2026-06-01","2026-07-01",None,"ACTIVE","Successive loan after prior return"))
    loan_objects.append((reloan_id,3,"2026-06-01",None,"Re-loan register description for artifact 3",5010.0))
    reports.append((len(reports)+1,reloan_id,3,1,"2026-06-01","RECEIPT","GOOD","Synthetic re-loan receipt evidence"))
    con.executemany("INSERT INTO artifact VALUES (?,?,?,?,?,?,?,?)", artifacts)
    con.executemany("INSERT INTO loan VALUES (?,?,?,?,?,?,?,?,?,?)", loans)
    con.executemany("INSERT INTO loan_object VALUES (?,?,?,?,?,?)", loan_objects)
    con.executemany("INSERT INTO condition_report VALUES (?,?,?,?,?,?,?,?)", reports)
    con.executemany("INSERT INTO exhibition VALUES (?,?,?,?,?)", [(i,f"EX-{i:03d}",f"Temporary Exhibition {i:02d}","2026-01-01","2027-12-31") for i in range(1,13)])
    con.executemany("INSERT INTO display_slot VALUES (?,?,?,?)", [(e,s,f"Gallery {(s-1)%3+1}",f"Position {s}") for e in range(1,13) for s in range(1,11)])
    # Placement table depends on exhibition and slots; created after those.
    con.executemany("INSERT INTO placement VALUES (?,?,?,?,?,?,?,?)", placements)
    # Notification contacts: one person contact per every 10th loan; organization contact sample.
    for i in range(1,n+1):
        if i%10==0:
            c_id=i
            p_id=staff_total+i
            contacts.append((c_id,p_id,None,f"Lender contact {i}",f"p{p_id}@example.test",f"+91-90000{i:05d}"))
            loan_contacts.append((i,c_id,"RETURN_NOTICE"))
    if org_ids and n>=1:
        cid=n+1; contacts.append((cid,None,org_ids[0],"Organization notification desk","loans@partner.example.test","+91-8000000000"))
        loan_contacts.append((1,cid,"COPY_NOTICE"))
    con.executemany("INSERT INTO notification_contact VALUES (?,?,?,?,?,?)", contacts)
    con.executemany("INSERT INTO loan_notification_contact VALUES (?,?,?)", loan_contacts)
    con.execute("CREATE INDEX ix_loan_due ON loan(loan_status,actual_return_date,expected_return_date)")
    con.execute("CREATE INDEX ix_artifact_unit ON artifact(unit_id)")
    con.execute("CREATE INDEX ix_loan_lender ON loan(lender_party_id)")
    con.commit()
    counts={t:con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ["party","person","lender","employee","curator","registrar","artifact","loan","loan_object","condition_report","placement"]}
    return con, counts


def run_one_size(n: int, keep_db: bool = False) -> dict:
    db_path=OUT/f"museum_{n}.sqlite"
    con, counts=build_db(n,db_path)
    results={}; timing={}; join_counts={}
    for name,sql in QUERIES.items():
        params=PARAMS.get(name,())
        sample_rows=con.execute(sql,params).fetchall()
        full_sql=sql.replace(" LIMIT 5", "").replace(" LIMIT 8", "")
        count_sql=f"SELECT COUNT(*) FROM ({full_sql}) AS counted_rows"
        full_count=con.execute(count_sql,params).fetchone()[0]
        results[name]={"row_count":full_count,"sample_rows":[list(r) for r in sample_rows[:5]]}
        samples=[]
        for _ in range(7):
            t0=time.perf_counter(); con.execute(count_sql,params).fetchone(); samples.append(time.perf_counter()-t0)
        timing[name+"_median_ms"]=round(statistics.median(samples)*1000,4)
        join_counts[name]=sql.upper().count(" JOIN ")
    # constraint failure evidence: invalid role, loan dates, contact category, FK slot.
    failures=[]
    tests=[
      ("duplicate accession identity", "INSERT INTO artifact VALUES (999999,'MM-000001',1,1,?, 'Duplicate accession',10.0,'2020-01-01')", (staff_total_placeholder(n),)),
      ("invalid loan date workflow", "INSERT INTO loan VALUES (999999,'BAD-DATE',?,1,36,'2026-11-14','2026-11-01',NULL,'ACTIVE','bad')", (staff_total_placeholder(n),)),
      ("invalid notification union category", "INSERT INTO notification_contact VALUES (999999,NULL,NULL,'no party',NULL,NULL)", ()),
      ("invalid employee role discriminator", "UPDATE employee SET role='APPRAISER' WHERE person_id=1", ()),
      ("subtype role mismatch", "INSERT INTO curator VALUES (36,'wrong subtype')", ()),
      ("invalid display slot parent", "INSERT INTO placement VALUES (999999,1,1,999,999,'2026-01-01',NULL,'bad caption')", ()),
    ]
    for label,sql,params in tests:
        try:
            con.execute(sql,params); con.commit()
            failures.append({"test":label,"result":"UNEXPECTED SUCCESS"})
        except sqlite3.IntegrityError as e:
            failures.append({"test":label,"result":"REJECTED","message":str(e)})
            con.rollback()
    # Cross-row temporal rule: attempt to occupy the exact same slot/time twice.
    first=con.execute("SELECT loan_id,artifact_id,exhibition_id,slot_no,placement_start,placement_end,display_caption FROM placement ORDER BY placement_id LIMIT 1").fetchone()
    try:
        con.execute("INSERT INTO placement VALUES (999998,?,?,?,?,?,?,?)", first)
        con.commit()
        failures.append({"test":"overlapping display-slot period","result":"UNEXPECTED SUCCESS"})
    except sqlite3.IntegrityError as e:
        failures.append({"test":"overlapping display-slot period","result":"REJECTED","message":str(e)})
        con.rollback()
    plan=con.execute("EXPLAIN QUERY PLAN "+QUERIES["Q1_overdue_open"]).fetchall()
    # Flat-file anomaly mini-demonstration.
    anomaly={
      "insertion_anomaly":"A lender with no loan has no row in a flat loan file, so the lender cannot be recorded independently.",
      "update_anomaly":"The lender name and artifact description are repeated on every line; changing one copy leaves inconsistent values.",
      "deletion_anomaly":"Deleting the only loan line for a lender also removes the only copy of that lender's details."
    }
    con.close()
    if not keep_db:
        try: db_path.unlink()
        except OSError: pass
    return {"population_lenders":n,"counts":counts,"query_results":results,"median_query_ms":timing,"explicit_join_counts":join_counts,"constraint_tests":failures,"q1_query_plan":[list(x) for x in plan],"flat_file_anomalies":anomaly}


def staff_total_placeholder(n:int)->int:
    return 41 # one valid lender party in each validation dataset


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--sizes',default='100,1000,10000,100000')
    ap.add_argument('--keep-db',action='store_true')
    args=ap.parse_args()
    sizes=[int(x.strip()) for x in args.sizes.split(',')]
    summary=[]
    for n in sizes:
        print(f"Validating workload with {n:,} lenders ...",flush=True)
        result=run_one_size(n,args.keep_db)
        summary.append(result)
    out=OUT/'validation_results.json'
    out.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    # Compact CSV timing summary.
    import csv
    with (OUT/'timing_summary.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['lenders','artifacts','loans','loan_objects','Q1_ms','Q2_ms','Q3_ms','Q4_ms','Q5_ms','Q6_ms','Q7_ms','Q8_ms'])
        for r in summary:
            t=r['median_query_ms']; c=r['counts']
            w.writerow([r['population_lenders'],c['artifact'],c['loan'],c['loan_object']]+[t[k+'_median_ms'] for k in ["Q1_overdue_open","Q2_no_condition_evidence","Q3_custody_history","Q4_condition_attention","Q5_unit_loan_counts","Q6_slot_occupancy","Q7_open_loan_contacts","Q8_latest_condition"]])
    print(f"Wrote {out}")
    for r in summary:
        print(f"{r['population_lenders']:>7,} lenders | {r['counts']['artifact']:>7,} artifacts | {r['counts']['loan']:>7,} loans | Q1 {r['median_query_ms']['Q1_overdue_open_median_ms']:.4f} ms | Q2 {r['median_query_ms']['Q2_no_condition_evidence_median_ms']:.4f} ms")

if __name__=='__main__':
    main()
