#!/usr/bin/env python3
"""Small executable demonstrations for Task 6 4NF, 5NF and spurious join."""
import sqlite3,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'
con=sqlite3.connect(':memory:')
con.executescript('''
CREATE TABLE service_mode(ServiceID INTEGER, TransportMode TEXT, PRIMARY KEY(ServiceID,TransportMode));
CREATE TABLE service_document(ServiceID INTEGER, DocumentType TEXT, PRIMARY KEY(ServiceID,DocumentType));
CREATE TABLE authorization_triple(OperatorID TEXT, ItemID TEXT, ChannelID TEXT, PRIMARY KEY(OperatorID,ItemID,ChannelID));
CREATE TABLE operator_item_approval(OperatorID TEXT,ItemID TEXT,PRIMARY KEY(OperatorID,ItemID));
CREATE TABLE operator_channel_approval(OperatorID TEXT,ChannelID TEXT,PRIMARY KEY(OperatorID,ChannelID));
CREATE TABLE item_channel_approval(ItemID TEXT,ChannelID TEXT,PRIMARY KEY(ItemID,ChannelID));
CREATE TABLE wrong_obs(SenderID TEXT,ServiceID INTEGER,DispatchWave INTEGER,CoordinatorID INTEGER);
CREATE TABLE wrong_service_coord(ServiceID INTEGER,CoordinatorID INTEGER,CoordinatorName TEXT);
''')
# 4NF: independent sets; their combined relation has 3x3 Cartesian combinations.
con.executemany('INSERT INTO service_mode VALUES(1,?)', [('Van',),('Bike',),('Locker',)])
con.executemany('INSERT INTO service_document VALUES(1,?)', [('IDProof',),('Invoice',),('Signature',)])
combos=con.execute('SELECT m.ServiceID,m.TransportMode,d.DocumentType FROM service_mode m JOIN service_document d USING(ServiceID)').fetchall()
# 5NF: pairwise approvals are defined as the complete rule; their join yields exactly these 2 triples.
triples=[('OP-A','ITEM-1','WEB'),('OP-B','ITEM-2','DESK')]
con.executemany('INSERT INTO authorization_triple VALUES(?,?,?)',triples)
con.executemany('INSERT INTO operator_item_approval VALUES(?,?)',[(a,b) for a,b,c in triples])
con.executemany('INSERT INTO operator_channel_approval VALUES(?,?)',[(a,c) for a,b,c in triples])
con.executemany('INSERT INTO item_channel_approval VALUES(?,?)',[(b,c) for a,b,c in triples])
joined=con.execute('''SELECT oi.OperatorID,oi.ItemID,oc.ChannelID FROM operator_item_approval oi
JOIN operator_channel_approval oc USING(OperatorID)
JOIN item_channel_approval ic ON ic.ItemID=oi.ItemID AND ic.ChannelID=oc.ChannelID ORDER BY 1,2,3''').fetchall()
# Deliberately wrong split only by ServiceID: Coordinator is scoped by SenderID + ServiceID.
con.executemany('INSERT INTO wrong_obs VALUES(?,?,?,?)',[('S1',1,1,7),('S2',1,1,9)])
con.executemany('INSERT INTO wrong_service_coord VALUES(?,?,?)',[(1,7,'Coord 7'),(1,9,'Coord 9')])
spurious=con.execute('''SELECT o.SenderID,o.ServiceID,o.DispatchWave,c.CoordinatorID,c.CoordinatorName
FROM wrong_obs o JOIN wrong_service_coord c USING(ServiceID) ORDER BY o.SenderID,c.CoordinatorID''').fetchall()
actual=[('S1',1,1,7,'Coord 7'),('S2',1,1,9,'Coord 9')]
result={
 'four_nf':{'mode_count':3,'document_count':3,'combined_cross_product_rows':len(combos),'decomposed_rows':6,'mvd_statement':'ServiceID ->> TransportMode and ServiceID ->> DocumentType'},
 'five_nf':{'original_triples':triples,'pairwise_join_result':joined,'lossless_join':set(triples)==set(joined)},
 'wrong_common_serviceid_split':{'correct_rows':actual,'join_rows':spurious,'spurious_rows':len(spurious)-len(actual)}
}
(OUT/'higher_normal_forms_demo.json').write_text(json.dumps(result,indent=2))
print('4NF independent resource sets: 3 modes + 3 document types -> 9 combined combinations; 6 decomposed rows.')
print('5NF pairwise join equals original triples:', result['five_nf']['lossless_join'], joined)
print('Wrong common-ServiceID split join rows:', spurious, '| spurious rows:', result['wrong_common_serviceid_split']['spurious_rows'])
con.close()
