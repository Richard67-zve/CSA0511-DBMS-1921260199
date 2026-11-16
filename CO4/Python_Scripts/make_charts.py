import csv, os
import matplotlib.pyplot as plt
from collections import defaultdict
os.makedirs('Diagrams',exist_ok=True)
with open('Results/benchmark.csv',newline='') as f: rows=list(csv.DictReader(f))
strategies=[]
for r in rows:
    if r['strategy'] not in strategies: strategies.append(r['strategy'])
sizes=sorted({int(r['records']) for r in rows})
for metric,title,ylabel,out in [
    ('equality_avg_reads','Equality search: average logical block reads','Block reads per equality lookup','Diagrams/equality_reads.png'),
    ('range_avg_reads','Range search: average logical block reads','Block reads per range lookup','Diagrams/range_reads.png')]:
    plt.figure(figsize=(8,4.6))
    for s in strategies:
        rr=[r for r in rows if r['strategy']==s]
        plt.plot([int(r['records']) for r in rr],[float(r[metric]) for r in rr],marker='o',label=s)
    plt.xscale('log'); plt.yscale('log'); plt.xticks(sizes,[f'{x:,}' for x in sizes]); plt.xlabel('Number of transaction records (log scale)'); plt.ylabel(ylabel); plt.title(title); plt.grid(True,which='both',alpha=.25); plt.legend(fontsize=7); plt.tight_layout(); plt.savefig(out,dpi=180); plt.close()
# Layout diagram
plt.figure(figsize=(11,5)); ax=plt.gca(); ax.axis('off')
boxes=[(0.05,0.58,0.25,0.25,'TXN logical record\n200 bytes fixed length'),(0.38,0.58,0.25,0.25,'4,096-byte disk block\n20 records + 96 unused bytes'),(0.71,0.58,0.24,0.25,'Access structures\nHeap / Sorted / Hash / B+ tree'),(0.38,0.10,0.25,0.23,'Query patterns\nTxnID / AccountNo / Branch / range')]
for x,y,w,h,t in boxes:
    ax.add_patch(plt.Rectangle((x,y),w,h,fill=False,linewidth=1.7)); ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=10)
for a,b in [((.30,.705),(.38,.705)),((.63,.705),(.71,.705)),((.83,.58),(.63,.33)),((.505,.58),(.505,.33))]:
    ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',lw=1.5))
plt.title('Bank transaction storage and access model',fontsize=14); plt.tight_layout(); plt.savefig('Diagrams/storage_architecture.png',dpi=180); plt.close()
