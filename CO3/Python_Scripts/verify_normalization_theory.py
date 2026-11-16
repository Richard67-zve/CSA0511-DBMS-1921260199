"""Executable checks for CO3 tuple swapping, 5NF JD, closure and key claims."""
from itertools import product
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'; OUT.mkdir(exist_ok=True)
# Independent MVD facts: 2 tags x 4 colours (eight tuples, as required by the brief).
tags={'eco','fragile'}; colours={'black','blue','red','white'}
combined={(1,t,c) for t in tags for c in colours}
pt={(p,t) for p,t,c in combined}; pc={(p,c) for p,t,c in combined}
reconstructed={(p,t,c) for p,t in pt for pp,c in pc if p==pp}
# 5NF case instance: S (0..2), C (0..2), W (0..2)
R={(1,1,1),(1,3,3),(2,1,2),(2,2,3),(3,1,1),(3,3,3)}
SC={(s,c) for s,c,w in R}; CW={(c,w) for s,c,w in R}; SW={(s,w) for s,c,w in R}
R3={(s,c,w) for s,c in SC for cc,w in CW if c==cc and (s,w) in SW}
SC_SW={(s,c,w) for s,c in SC for ss,w in SW if s==ss}
SC_CW={(s,c,w) for s,c in SC for cc,w in CW if c==cc}
SW_CW={(s,c,w) for s,w in SW for c,ww in CW if w==ww}
# FD closure engine
fds=[({'OrderID'},{'OrderDate'}),({'OrderID'},{'CustomerID'}),({'OrderID'},{'ShipStreet'}),({'OrderID'},{'ShipPIN'}),
     ({'CustomerID'},{'CustomerName'}),({'CustomerID'},{'CustomerEmail'}),({'ShipPIN'},{'ShipCity'}),({'ShipPIN'},{'ShipState'}),
     ({'ShipStreet','ShipCity'},{'ShipPIN'}),({'ProductID'},{'ProductName'}),({'ProductID'},{'UnitPrice'}),({'ProductID'},{'TagList'}),({'ProductID'},{'ColourList'}),({'ProductID'},{'CategoryID'}),
     ({'ProductID'},{'SupplierID'}),({'CategoryID'},{'CategoryName'}),({'SupplierID'},{'SupplierName'}),({'SupplierID'},{'SupplierPhone'}),
     ({'WarehouseID'},{'WarehouseCity'}),({'OrderID','ProductID'},{'Quantity'}),({'OrderID','ProductID'},{'WarehouseID'})]
def closure(attrs):
    c=set(attrs); changed=True; steps=[]
    while changed:
        changed=False
        for x,y in fds:
            if x<=c and not y<=c:
                old=set(c); c |= y; changed=True; steps.append((sorted(old),sorted(x),sorted(y),sorted(c)))
    return c,steps
allattrs={'OrderID','OrderDate','CustomerID','CustomerName','CustomerEmail','ShipStreet','ShipCity','ShipPIN','ShipState','ProductID','ProductName','UnitPrice','TagList','ColourList','CategoryID','CategoryName','SupplierID','SupplierName','SupplierPhone','Quantity','WarehouseID','WarehouseCity'}
key_cl, key_steps=closure({'OrderID','ProductID'})
assert key_cl==allattrs
assert closure({'OrderID'})[0] != allattrs and closure({'ProductID'})[0] != allattrs
assert R3==R
summary={
 'mvd':{'tags':sorted(tags),'colours':sorted(colours),'combined_cartesian_rows':len(combined),'product_tag_rows':len(pt),'product_colour_rows':len(pc),'reconstructed_rows':len(reconstructed),'reconstruction_exact':reconstructed==combined},
 '5nf':{'input_triples':len(R),'supplier_category_pairs':len(SC),'category_warehouse_pairs':len(CW),'supplier_warehouse_pairs':len(SW),'three_projection_join_rows':len(R3),'three_projection_join_exact':R3==R,'two_projection_join_counts':{'SC_join_SW':len(SC_SW),'SC_join_CW':len(SC_CW),'SW_join_CW':len(SW_CW)},'all_two_way_decompositions_lossy':all(len(x)>len(R) for x in (SC_SW,SC_CW,SW_CW))},
 'closures':{'OrderID_ProductID_closure_sorted':sorted(key_cl),'OrderID_closure_sorted':sorted(closure({'OrderID'})[0]),'ProductID_closure_sorted':sorted(closure({'ProductID'})[0]),'ShipPIN_closure_sorted':sorted(closure({'ShipPIN'})[0]),'CustomerID_closure_sorted':sorted(closure({'CustomerID'})[0]),'SupplierID_closure_sorted':sorted(closure({'SupplierID'})[0]),'key_steps':key_steps}
}
(OUT/'theory_verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
log=[]
log.append('SHOPNEST CO3 THEORY CHECKS')
log.append(f"MVD combined product-tag-colour rows: {len(combined)}; separate ProductTag rows: {len(pt)}; ProductColour rows: {len(pc)}; reconstructed exactly: {reconstructed==combined}")
log.append(f"5NF triple relation rows: {len(R)}; projections SC={len(SC)}, CW={len(CW)}, SW={len(SW)}; all-three join rows={len(R3)}; exact={R3==R}")
log.append(f"Pairwise joins rows: SC⋈SW={len(SC_SW)}, SC⋈CW={len(SC_CW)}, SW⋈CW={len(SW_CW)}; each creates spurious triples={all(len(x)>len(R) for x in (SC_SW,SC_CW,SW_CW))}")
log.append('Candidate key closure (OrderID, ProductID) reaches all attributes: '+str(key_cl==allattrs))
log.append('Proper-subset test: OrderID alone and ProductID alone are not superkeys.')
(OUT/'theory_verification.txt').write_text('\n'.join(log)+'\n',encoding='utf-8')
print('\n'.join(log))
