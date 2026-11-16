#!/usr/bin/env python3
"""Execute the five CO2 operational questions against the largest local BCNF fixture."""
import sqlite3, csv, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'outputs'/'databases'/'bcnf_600000.sqlite'
OUT=ROOT/'outputs'
con=sqlite3.connect(DB)
queries={
'Q1_actor1_wave4': '''SELECT s.SenderID,s.SenderName,sv.ServiceID,sv.ServiceCode,sv.ServiceName,o.DispatchWave,o.Completion,
 cp.ServiceBand,bp.RouteFactor,ROUND(o.Completion*sv.VolumeWeight*bp.RouteFactor,4) AS AdjustedIndex
 FROM observation o JOIN sender s USING(SenderID) JOIN service sv USING(ServiceID)
 JOIN completion_policy cp USING(Completion) JOIN service_band_policy bp USING(ServiceBand)
 WHERE o.SenderID=1 AND o.DispatchWave=4 ORDER BY sv.ServiceID''',
'Q2_all_required_services_all_waves_at_least_39': '''SELECT s.SenderID,s.SenderName,s.RouteGroup FROM sender s
 WHERE NOT EXISTS (SELECT 1 FROM group_required_service g CROSS JOIN (SELECT 1 AS wave UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4) w
 WHERE g.RouteGroup=s.RouteGroup AND NOT EXISTS (SELECT 1 FROM observation o WHERE o.SenderID=s.SenderID
 AND o.ServiceID=g.ServiceID AND o.DispatchWave=w.wave AND o.Completion>=39)) ORDER BY s.SenderID LIMIT 20''',
'Q3_observed_wave4_services_no_value_below_39': '''SELECT sv.ServiceID,sv.ServiceCode,sv.ServiceName FROM service sv
 WHERE EXISTS (SELECT 1 FROM observation o WHERE o.ServiceID=sv.ServiceID AND o.DispatchWave=4)
 AND NOT EXISTS (SELECT 1 FROM observation o WHERE o.ServiceID=sv.ServiceID AND o.DispatchWave=4 AND o.Completion<39)
 ORDER BY sv.ServiceID''',
'Q4_coordinator_mean_below_observation_weighted_hub_mean': '''WITH coordinator_means AS (
 SELECT c.CoordinatorID,c.CoordinatorName,c.Hub,AVG(o.Completion) AS CoordMean,COUNT(*) AS N
 FROM observation o JOIN assignment a USING(SenderID,ServiceID) JOIN coordinator c USING(CoordinatorID)
 GROUP BY c.CoordinatorID,c.CoordinatorName,c.Hub),
 hub_means AS (
 SELECT c.Hub,AVG(o.Completion) AS HubMean FROM observation o
 JOIN assignment a USING(SenderID,ServiceID) JOIN coordinator c USING(CoordinatorID) GROUP BY c.Hub)
 SELECT cm.CoordinatorID,cm.CoordinatorName,cm.Hub,ROUND(cm.CoordMean,3),ROUND(hm.HubMean,3),cm.N
 FROM coordinator_means cm JOIN hub_means hm USING(Hub) WHERE cm.CoordMean<hm.HubMean
 ORDER BY cm.Hub,cm.CoordMean LIMIT 20''',
'Q5_senders_with_low_observations_in_at_least_3_waves': '''SELECT s.SenderID,s.SenderName,COUNT(DISTINCT o.DispatchWave) AS LowWaves
 FROM sender s JOIN observation o USING(SenderID) WHERE o.Completion<39
 GROUP BY s.SenderID,s.SenderName HAVING COUNT(DISTINCT o.DispatchWave)>=3
 ORDER BY s.SenderID LIMIT 20'''
}
results={}
for name,sql in queries.items():
    cur=con.execute(sql)
    rows=cur.fetchall()
    headers=[d[0] for d in cur.description]
    results[name]={'columns':headers,'row_count_returned':len(rows),'sample_rows':rows[:20]}
    outpath=OUT/f'{name}.csv'
    with open(outpath,'w',newline='') as f:
        w=csv.writer(f); w.writerow(headers);w.writerows(rows)
    print(f'\n{name} | rows returned/displayed: {len(rows)}')
    print(' | '.join(headers))
    for r in rows[:8]: print(' | '.join(str(x) for x in r))
with open(OUT/'case_query_results.json','w') as f: json.dump(results,f,indent=2)
con.close()
print('\nQuery CSV files and case_query_results.json written to outputs/.')
