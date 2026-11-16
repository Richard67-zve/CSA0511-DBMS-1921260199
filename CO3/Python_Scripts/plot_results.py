from pathlib import Path
import csv, json
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
ROOT=Path(__file__).resolve().parents[1]; D=ROOT/'Diagrams'; O=ROOT/'outputs'; E=ROOT/'Execution_Evidence'/'Output_Captures'
D.mkdir(exist_ok=True); O.mkdir(exist_ok=True); E.mkdir(exist_ok=True)
rows=list(csv.DictReader((O/'benchmark_results.csv').open()))
for r in rows:
    for k in ['rows','database_mib','load_seconds','supplier_update_rows_touched','supplier_update_seconds_median','history_query_seconds_median']:
        r[k]=float(r[k])
# Charts
for key,title,ylabel,filename in [
    ('database_mib','Database storage by population size','Allocated database size (MiB)','storage_by_design.png'),
    ('load_seconds','Dataset load time by population size','Load time (seconds)','load_time_by_design.png'),
    ('history_query_seconds_median','Order-history query time by population size','Median query time (seconds)','history_query_time.png')]:
    fig,ax=plt.subplots(figsize=(8.8,4.8))
    for design,label in [('unf','Unnormalised'),('3nf','3NF'),('4nf5nf','4NF/5NF')]:
        rr=[x for x in rows if x['design']==design]
        ax.plot([x['rows'] for x in rr],[x[key] for x in rr],marker='o',label=label)
    ax.set_xscale('log'); ax.set_xticks([1000,10000,100000,1000000],['1,000','10,000','100,000','1,000,000'])
    ax.set_xlabel('Order-line rows'); ax.set_ylabel(ylabel); ax.set_title(title); ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(O/filename,dpi=180); plt.close(fig)
# update affected lines
fig,ax=plt.subplots(figsize=(8.8,4.8))
for design,label in [('unf','Unnormalised'),('3nf','3NF'),('4nf5nf','4NF/5NF')]:
    rr=[x for x in rows if x['design']==design]
    ax.plot([x['rows'] for x in rr],[x['supplier_update_rows_touched'] for x in rr],marker='o',label=label)
ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xticks([1000,10000,100000,1000000],['1,000','10,000','100,000','1,000,000'])
ax.set_xlabel('Order-line rows'); ax.set_ylabel('Rows modified by supplier-phone update'); ax.set_title('Update amplification by design'); ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(O/'supplier_update_amplification.png',dpi=180); plt.close(fig)
# Dependency map using boxes and arrows
fig,ax=plt.subplots(figsize=(12,7)); ax.set_xlim(0,12); ax.set_ylim(0,8); ax.axis('off')
def box(x,y,w,h,text,fc='#eaf1f8',ec='#28527a',fs=9):
    p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.12',fc=fc,ec=ec,lw=1.2); ax.add_patch(p); ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=fs,wrap=True)
def arrow(x1,y1,x2,y2,label=''):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='->',mutation_scale=12,lw=1.1,color='#52616b'))
    if label: ax.text((x1+x2)/2,(y1+y2)/2+.12,label,ha='center',fontsize=8)
box(.4,6.4,2.1,.75,'OrderID\n(OrderDate, CustomerID, ShipStreet, ShipPIN)')
box(3.25,6.4,2.0,.75,'CustomerID\n(CustomerName, Email)')
box(6.15,6.4,2.0,.75,'ShipPIN\n(ShipCity, ShipState)')
box(.4,4.6,2.1,.75,'ProductID\n(ProductName, UnitPrice, CategoryID, SupplierID)')
box(3.25,4.6,2.0,.75,'CategoryID\n(CategoryName)')
box(6.15,4.6,2.0,.75,'SupplierID\n(SupplierName, Phone)')
box(9.0,4.6,2.2,.75,'WarehouseID\n(WarehouseCity)')
box(4.2,2.4,3.0,.8,'(OrderID, ProductID)\n(Quantity, WarehouseID)\nCANDIDATE KEY')
box(.6,.65,3.0,.85,'ProductID ↠ Tag\n(independent multivalued fact)',fc='#f4f0e8',ec='#9a6b28')
box(8.2,.65,3.0,.85,'ProductID ↠ Colour\n(independent multivalued fact)',fc='#f4f0e8',ec='#9a6b28')
arrow(2.5,6.78,3.25,6.78,'partial'); arrow(5.25,6.78,6.15,6.78,'transitive');
arrow(2.5,4.98,3.25,4.98,'transitive'); arrow(5.25,4.98,6.15,4.98,'transitive');
arrow(2.5,4.8,4.6,3.2,'partial'); arrow(5.7,4.6,6.0,3.2,'full'); arrow(10.1,4.6,6.9,3.2,'warehouse city')
arrow(1.5,4.6,1.9,1.5,'MVD'); arrow(2.0,4.6,9.5,1.5,'MVD')
ax.text(6,7.65,'ORDER_LINE functional-dependency map (simplified)',ha='center',fontsize=14,weight='bold')
fig.tight_layout(); fig.savefig(D/'dependency_diagram.png',dpi=200,bbox_inches='tight'); plt.close(fig)
# Normalization road map
fig,ax=plt.subplots(figsize=(11,4.5)); ax.axis('off'); ax.set_xlim(0,11); ax.set_ylim(0,4.5)
steps=[('UNF','Repeating lists\nTagList / ColourList'),('1NF','Atomic values\nseparate tag/colour rows'),('2NF','Remove partial\nkey dependencies'),('3NF','Remove transitive\ndependencies'),('BCNF','Every FD determinant\nis a superkey'),('4NF','Separate independent\nMVDs'),('5NF','Decompose non-trivial\njoin dependency')]
xs=[.25,1.85,3.45,5.05,6.65,8.25,9.85]
for i,(t,d) in enumerate(steps):
    boxp=FancyBboxPatch((xs[i],1.6),1.25,1.3,boxstyle='round,pad=.08',fc='#eaf1f8',ec='#28527a'); ax.add_patch(boxp)
    ax.text(xs[i]+.625,2.55,t,ha='center',weight='bold',fontsize=10); ax.text(xs[i]+.625,2.05,d,ha='center',va='center',fontsize=7.2)
    if i<6: ax.add_patch(FancyArrowPatch((xs[i]+1.28,2.25),(xs[i+1]-.05,2.25),arrowstyle='->',mutation_scale=10,color='#52616b'))
ax.text(5.5,3.8,'ShopNest normalisation progression',ha='center',fontsize=14,weight='bold')
ax.text(5.5,.65,'Logical design changes; implementation may use controlled indexes and read projections.',ha='center',fontsize=9)
fig.tight_layout(); fig.savefig(D/'normalization_roadmap.png',dpi=200,bbox_inches='tight'); plt.close(fig)
# MVD diagram
fig,ax=plt.subplots(figsize=(9,4.5)); ax.axis('off'); ax.set_xlim(0,9); ax.set_ylim(0,4.5)
box(.5,1.8,2.0,1.0,'PRODUCT\n(ProductID, ProductName)',fc='#eaf1f8',ec='#28527a')
box(3.6,2.8,2.0,.85,'PRODUCT_TAG\n(ProductID, Tag)',fc='#f4f0e8',ec='#9a6b28')
box(6.5,1.0,2.0,.85,'PRODUCT_COLOUR\n(ProductID, Colour)',fc='#f4f0e8',ec='#9a6b28')
arrow2=lambda a,b: ax.add_patch(FancyArrowPatch(a,b,arrowstyle='->',mutation_scale=13,lw=1.4,color='#52616b'))
arrow2((2.5,2.45),(3.6,3.1)); arrow2((2.5,2.1),(6.5,1.45))
ax.text(4.5,4.1,'Independent multi-valued facts (4NF)',ha='center',fontsize=13,weight='bold')
ax.text(4.5,.35,'For t tags and c colours: combined table has t × c rows; split tables have t + c rows.',ha='center',fontsize=9)
fig.tight_layout(); fig.savefig(D/'mvd_4nf.png',dpi=200,bbox_inches='tight'); plt.close(fig)
# 5NF JD diagram
fig,ax=plt.subplots(figsize=(10,5)); ax.axis('off'); ax.set_xlim(0,10); ax.set_ylim(0,5)
box(3.5,3.65,3,0.85,'SUPPLY(Supplier, Category, Warehouse)',fc='#eaf1f8',ec='#28527a',fs=10)
box(.3,1.6,2.5,0.85,'SUPPLIER_CATEGORY\n(Supplier, Category)',fc='#f4f0e8',ec='#9a6b28')
box(3.75,1.6,2.5,0.85,'CATEGORY_WAREHOUSE\n(Category, Warehouse)',fc='#f4f0e8',ec='#9a6b28')
box(7.2,1.6,2.5,0.85,'SUPPLIER_WAREHOUSE\n(Supplier, Warehouse)',fc='#f4f0e8',ec='#9a6b28')
for a,b in [((4.3,3.65),(1.55,2.45)),((5,3.65),(5,2.45)),((5.7,3.65),(8.45,2.45))]: ax.add_patch(FancyArrowPatch(a,b,arrowstyle='->',mutation_scale=12,color='#52616b'))
ax.text(5,4.75,'Three-way join dependency / 5NF decomposition',ha='center',fontsize=13,weight='bold')
ax.text(5,.65,'The three pairwise projections reconstruct six legal triples; any selected two-projection join adds spurious triples.',ha='center',fontsize=9)
fig.tight_layout(); fig.savefig(D/'join_dependency_5nf.png',dpi=200,bbox_inches='tight'); plt.close(fig)
# Copy output charts to captures
for p in O.glob('*.png'):
    (E/p.name).write_bytes(p.read_bytes())
print('Generated diagrams and charts:', len(list(D.glob('*.png'))), len(list(O.glob('*.png'))))
