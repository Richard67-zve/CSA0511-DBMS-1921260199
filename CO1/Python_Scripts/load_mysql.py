#!/usr/bin/env python3
"""Populate the MySQL 8.0 Meridian Museum schema with a deterministic workload.

Run 01_schema_mysql.sql first. Install mysql-connector-python and provide
MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD and MYSQL_DATABASE env vars.
Seed is fixed at 4211. Records are inserted in dependency order and committed
in one transaction per table batch.
"""
from __future__ import annotations
import argparse, os, random
from datetime import date, timedelta
import mysql.connector

SEED = 4211

def chunks(rows, size=5000):
    for i in range(0, len(rows), size):
        yield rows[i:i+size]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--size',type=int,default=100,help='number of LENDER rows: 100, 1000, 10000 or 100000')
    args=ap.parse_args()
    n=args.size
    if n not in {100,1000,10000,100000}:
        raise SystemExit('Choose --size 100, 1000, 10000 or 100000')
    cfg={
      'host':os.getenv('MYSQL_HOST','127.0.0.1'),
      'port':int(os.getenv('MYSQL_PORT','3306')),
      'user':os.getenv('MYSQL_USER','root'),
      'password':os.getenv('MYSQL_PASSWORD',''),
      'database':os.getenv('MYSQL_DATABASE','meridian_museum'),
      'autocommit':False,
    }
    cnx=mysql.connector.connect(**cfg)
    cur=cnx.cursor()
    rng=random.Random(SEED)
    staff=40
    people_count=staff+n
    org_count=10
    try:
        cur.execute('SET FOREIGN_KEY_CHECKS=1')
        cur.executemany('INSERT INTO party(party_id,party_kind) VALUES (%s,%s)',
                        [(i,'PERSON') for i in range(1,people_count+1)] +
                        [(people_count+j,'ORGANIZATION') for j in range(1,org_count+1)])
        cnx.commit()
        for batch in chunks([(i,f'Person{i:06d}',f'Surname{i%997:03d}',f'p{i}@example.test') for i in range(1,people_count+1)]):
            cur.executemany('INSERT INTO person(party_id,first_name,last_name,email) VALUES (%s,%s,%s,%s)',batch)
            cnx.commit()
        cur.executemany('INSERT INTO organization(party_id,legal_name,registration_no) VALUES (%s,%s,%s)',
                        [(people_count+j,f'Museum Partner {j:02d}',f'ORG-{j:04d}') for j in range(1,org_count+1)])
        cnx.commit()
        cur.executemany('INSERT INTO person_phone(party_id,phone_type,phone_number) VALUES (%s,%s,%s)',
                        [(i,'MOBILE',f'+91-90000{i:05d}') for i in range(1,people_count+1)])
        cur.executemany('INSERT INTO lender(party_id,lender_code,joined_on) VALUES (%s,%s,%s)',
                        [(staff+i,f'LEN-{i:06d}','2024-01-01') for i in range(1,n+1)])
        cnx.commit()
        cur.executemany('INSERT INTO employee(person_id,employee_no,role,hired_on) VALUES (%s,%s,%s,%s)',
                        [(i,f'EMP-{i:04d}','CURATOR' if i<=35 else 'REGISTRAR','2020-01-01') for i in range(1,staff+1)])
        cur.executemany('INSERT INTO curator(person_id,specialisation) VALUES (%s,%s)',[(i,f'Specialisation {(i-1)%7+1}') for i in range(1,36)])
        cur.executemany('INSERT INTO registrar(person_id,clearance_level) VALUES (%s,%s)',[(i,'STANDARD') for i in range(36,41)])
        cnx.commit()
        cur.executemany('INSERT INTO collection_unit(unit_id,unit_name) VALUES (%s,%s)',[(i,f'Unit {i:02d}') for i in range(1,9)])
        cur.executemany('INSERT INTO collection_type(collection_type_id,type_name) VALUES (%s,%s)',[(i,x) for i,x in enumerate(['Painting','Sculpture','Textile','Ceramic','Manuscript','Photograph'],1)])
        cur.executemany('INSERT INTO exhibition(exhibition_id,exhibition_code,exhibition_name,opens_on,closes_on) VALUES (%s,%s,%s,%s,%s)',[(i,f'EX-{i:03d}',f'Temporary Exhibition {i:02d}','2026-01-01','2050-12-31') for i in range(1,13)])
        cur.executemany('INSERT INTO display_slot(exhibition_id,slot_no,gallery_name,position_description) VALUES (%s,%s,%s,%s)',[(e,s,f'Gallery {(s-1)%3+1}',f'Position {s}') for e in range(1,13) for s in range(1,11)])
        cnx.commit()
        artifact_rows=[]; loan_rows=[]; loan_object_rows=[]; report_rows=[]; placement_rows=[]
        today=date(2026,11,13)
        report_id=1; placement_id=1
        for i in range(1,n+1):
            lender_pid=staff+i
            start=date(2026,1,1)+timedelta(days=(i*7)%300)
            if i%4==0:
                status='ACTIVE'; actual=None; due=today-timedelta(days=1+(i%20))
            elif i%4==1:
                status='ACTIVE'; actual=None; due=today+timedelta(days=5+(i%30))
            else:
                status='CLOSED'; due=start+timedelta(days=45); actual=due+timedelta(days=i%3)
            loan_id=i
            loan_rows.append((loan_id,f'LN-{i:06d}',lender_pid,((i-1)%35)+1,36+((i-1)%5),start,due,actual,status,'Temporary exhibition loan'))
            for k in range(2):
                art_id=2*(i-1)+k+1
                owner_pid=lender_pid if art_id%5 else rng.randint(staff+1,staff+n)
                artifact_rows.append((art_id,f'MM-{art_id:06d}',((art_id-1)%8)+1,((art_id-1)%6)+1,owner_pid,f'Museum artifact {art_id:06d}',1000+(art_id%10000)*12.5,'INR',None if art_id%11==0 else date(2020,1,1),date(2018,1,1)))
                end=actual
                loan_object_rows.append((loan_id,art_id,start,end,f'Loan register description for artifact {art_id}',5000+art_id*3,'INR'))
                if art_id%4 != 0:
                    code='DAMAGED' if art_id%17==0 else 'POOR' if art_id%13==0 else 'GOOD' if art_id%3 else 'FAIR'
                    report_rows.append((report_id,loan_id,art_id,((i-1)%35)+1,start+timedelta(days=1),'RECEIPT',code,'Synthetic validation note'))
                    report_id+=1
                if art_id%2==0:
                    ex=((i-1)%12)+1; slot=((i-1)//12)%10+1
                    place_start=date(2026,1,1)+timedelta(days=((i-1)//120)*7)
                    placement_rows.append((placement_id,loan_id,art_id,ex,slot,place_start,place_start+timedelta(days=6),f'Gallery caption for artifact {art_id}'))
                    placement_id+=1
        # Re-loan artifact 3 after its earlier closed custody interval. This proves
        # an artifact can have successive LOAN_OBJECT occurrences without overlap.
        reloan_id=n+1
        loan_rows.append((reloan_id,'LN-RET-000001',staff+1,1,36,date(2026,6,1),date(2026,7,1),None,'ACTIVE','Successive loan after prior return'))
        loan_object_rows.append((reloan_id,3,date(2026,6,1),None,'Re-loan register description for artifact 3',5010.0,'INR'))
        report_rows.append((report_id,reloan_id,3,1,date(2026,6,1),'RECEIPT','GOOD','Synthetic re-loan receipt evidence'))
        # Explicit primary keys make seeded results exactly reproducible.
        for batch in chunks(artifact_rows):
            cur.executemany('INSERT INTO artifact(artifact_id,accession_no,unit_id,collection_type_id,owner_party_id,title,estimated_value,currency_code,ownership_known_from,acquired_on) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',batch); cnx.commit()
        for batch in chunks(loan_rows):
            cur.executemany('INSERT INTO loan(loan_id,loan_no,lender_party_id,responsible_curator_id,processing_registrar_id,loan_date,expected_return_date,actual_return_date,loan_status,purpose) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',batch); cnx.commit()
        for batch in chunks(loan_object_rows):
            cur.executemany('INSERT INTO loan_object(loan_id,artifact_id,custody_start,custody_end,loan_line_description,loan_line_value,currency_code) VALUES (%s,%s,%s,%s,%s,%s,%s)',batch); cnx.commit()
        for batch in chunks(report_rows):
            cur.executemany('INSERT INTO condition_report(report_id,loan_id,artifact_id,inspector_person_id,report_date,report_stage,condition_code,notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',batch); cnx.commit()
        for batch in chunks(placement_rows):
            cur.executemany('INSERT INTO placement(placement_id,loan_id,artifact_id,exhibition_id,slot_no,placement_start,placement_end,display_caption) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',batch); cnx.commit()
        # Contacts use the union-category table: each row identifies exactly one person OR organization.
        contacts=[]; mappings=[]
        for i in range(10,n+1,10):
            pid=staff+i; cid=len(contacts)+1
            contacts.append((cid,pid,None,f'Lender contact {i}',f'p{pid}@example.test',f'+91-90000{i:05d}'))
            mappings.append((i,cid,'RETURN_NOTICE'))
        if org_count:
            cid=len(contacts)+1; contacts.append((cid,None,people_count+1,'Organization notification desk','loans@partner.example.test','+91-8000000000'))
            mappings.append((1,cid,'COPY_NOTICE'))
        for batch in chunks(contacts):
            cur.executemany('INSERT INTO notification_contact(contact_id,person_id,organization_id,contact_label,email,phone) VALUES (%s,%s,%s,%s,%s,%s)',batch); cnx.commit()
        for batch in chunks(mappings):
            cur.executemany('INSERT INTO loan_notification_contact(loan_id,contact_id,notification_purpose) VALUES (%s,%s,%s)',batch); cnx.commit()
        print(f'Loaded seed={SEED}, lenders={n:,}, artifacts={2*n:,}, loans={n:,}, loan_objects={2*n:,}, condition_reports={len(report_rows):,}, placements={len(placement_rows):,}')
    except Exception:
        cnx.rollback()
        raise
    finally:
        cur.close(); cnx.close()

if __name__=='__main__': main()
