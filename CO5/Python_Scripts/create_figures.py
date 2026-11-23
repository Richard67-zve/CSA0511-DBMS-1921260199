import json, csv, subprocess
from pathlib import Path
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'Diagrams'; O=ROOT/'outputs'
D.mkdir(exist_ok=True)
data=json.load(open(O/'simulation_results.json'))
rows=[]
with open(O/'performance_results.csv',newline='') as f: rows=list(csv.DictReader(f))

# Throughput trend
fig,ax=plt.subplots(figsize=(9,5.2))
for dist,ls in [('uniform','-'),('skew81','--')]:
 for strategy in ['Global serial execution','Conservative strict 2PL (cap 16)','Strict timestamp ordering (commit-atomic validation)']:
  rr=sorted([r for r in rows if r['distribution']==dist and r['strategy']==strategy],key=lambda x:int(x['transactions']))
  ax.plot([int(r['transactions']) for r in rr],[float(r['throughput_per_second']) for r in rr],marker='o',linestyle=ls,label=f"{strategy} | {dist}")
ax.set_title('Completed-delivery throughput across burst sizes')
ax.set_xlabel('Generated deliveries'); ax.set_ylabel('Deliveries per second')
ax.grid(True,alpha=.25); ax.legend(fontsize=7,loc='best'); fig.tight_layout()
fig.savefig(D/'throughput_by_burst.png',dpi=180); plt.close(fig)

# p95 latency
fig,ax=plt.subplots(figsize=(9,5.2))
for dist,ls in [('uniform','-'),('skew81','--')]:
 for strategy in ['Global serial execution','Conservative strict 2PL (cap 16)','Strict timestamp ordering (commit-atomic validation)']:
  rr=sorted([r for r in rows if r['distribution']==dist and r['strategy']==strategy],key=lambda x:int(x['transactions']))
  ax.plot([int(r['transactions']) for r in rr],[float(r['p95_response_ms']) for r in rr],marker='o',linestyle=ls,label=f"{strategy} | {dist}")
ax.set_title('Nearest-rank p95 response time (arrival to completion)')
ax.set_xlabel('Generated deliveries'); ax.set_ylabel('p95 response time (ms)')
ax.grid(True,alpha=.25); ax.legend(fontsize=7,loc='best'); fig.tight_layout()
fig.savefig(D/'p95_latency_by_burst.png',dpi=180); plt.close(fig)

# Admission cap trade-off (Task 12)
ac=data['extras']['admission_comparison_skewed_1000']
caps=[4,8,16,32]
fig,ax=plt.subplots(figsize=(8.5,5))
ax.plot(caps,[ac[str(c)]['mean_admission_wait_ms'] for c in caps],marker='o',label='Admission queue mean')
ax.plot(caps,[ac[str(c)]['mean_lock_wait_ms'] for c in caps],marker='s',label='Lock wait mean')
ax.plot(caps,[ac[str(c)]['mean_response_ms'] for c in caps],marker='^',label='End-to-end mean response')
ax.set_title('Bounded admission shifts queueing under 81% hot-canal demand')
ax.set_xlabel('Maximum admitted transactions'); ax.set_ylabel('Milliseconds')
ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout()
fig.savefig(D/'admission_queue_tradeoff.png',dpi=180); plt.close(fig)

# Strategy architecture diagram
dot='''digraph Strategies {
 graph [rankdir=LR, bgcolor="white", pad="0.25", nodesep="0.45", ranksep="0.65", fontname="Arial", label="RiverGate concurrency alternatives", labelloc=t, fontsize=18];
 node [shape=box, style="rounded,filled", fillcolor="#eef4fb", color="#52749b", fontname="Arial", fontsize=10, margin="0.15,0.10"];
 edge [fontname="Arial", fontsize=9, color="#52606d"];
 A [label="A. Global serial queue\\nOne transaction at a time\\nSimple correctness baseline"];
 B [label="B. Conservative strict 2PL\\nAcquire all known X locks\\nHold through COMMIT"];
 C [label="C. Timestamp ordering\\nR-TS / W-TS checks\\nReject stale operation; retry"];
 N [label="No control\\nConcurrent read/write\\nLost update / mixed report", fillcolor="#fff1ed", color="#c85a45"];
 A -> V [label="global exclusion"];
 B -> V [label="resource exclusion"];
 C -> V [label="timestamp validation"];
 N -> F [label="not reliable"];
 V [label="Atomic movement\\nDebit source + credit destination\\nCOMMIT as one unit", shape=box, fillcolor="#edf7ef", color="#4b8b60"];
 F [label="Invariant failure\\nToken conservation can break", shape=box, fillcolor="#fff1ed", color="#c85a45"];
}'''
(D/'concurrency_strategies.dot').write_text(dot)
subprocess.run(['dot','-Tpng',str(D/'concurrency_strategies.dot'),'-o',str(D/'concurrency_strategies.png')],check=True)

# Deadlock wait-for graph
dot='''digraph Deadlock {
 graph [rankdir=LR, bgcolor="white", pad="0.25", fontname="Arial", label="Dynamic 2PL wait-for cycle", labelloc=t, fontsize=18];
 node [shape=box, style="rounded,filled", fillcolor="#eef4fb", color="#52749b", fontname="Arial", fontsize=12, width=1.4, height=.65];
 edge [fontname="Arial", fontsize=10, color="#b23a2b", penwidth=2];
 T1 [label="T1 (older)\\nholds X(A)\\nwaits for X(B)"];
 T2 [label="T2 (younger)\\nholds X(B)\\nwaits for X(A)"];
 T1 -> T2 [label="waits for B"];
 T2 -> T1 [label="waits for A"];
}'''
(D/'wait_for_deadlock.dot').write_text(dot)
subprocess.run(['dot','-Tpng',str(D/'wait_for_deadlock.dot'),'-o',str(D/'wait_for_deadlock.png')],check=True)

# Precedence graph blind write
# manually use graphviz with cycle
dot='''digraph BlindWrite {
 graph [rankdir=LR, bgcolor="white", pad="0.25", fontname="Arial", label="Blind writes: cycle in precedence graph", labelloc=t, fontsize=18];
 node [shape=circle, style="filled", fillcolor="#eef4fb", color="#52749b", fontname="Arial", fontsize=13, width=.75, height=.75];
 edge [fontname="Arial", fontsize=10, color="#2f6f9f", penwidth=2];
 T1 -> T2 [label="w1(M) before w2(M)"];
 T2 -> T1 [label="w2(M) before final w1(M)"];
}'''
(D/'blind_write_cycle.dot').write_text(dot)
subprocess.run(['dot','-Tpng',str(D/'blind_write_cycle.dot'),'-o',str(D/'blind_write_cycle.png')],check=True)

# Recovery timeline
# Clean checkpoint, winners, losers, crash

dot='''digraph Recovery {
 graph [rankdir=LR, bgcolor="white", pad="0.25", nodesep="0.35", ranksep="0.45", fontname="Arial", label="WAL crash trace around the clean checkpoint", labelloc=t, fontsize=18];
 node [shape=box, style="rounded,filled", fillcolor="#eef4fb", color="#52749b", fontname="Arial", fontsize=10, margin="0.13,0.09"];
 edge [fontname="Arial", fontsize=9, color="#52606d"];
 CP [label="Clean checkpoint\\nall earlier work durable", fillcolor="#edf7ef", color="#4b8b60"];
 T1 [label="T1 BEGIN / UPDATE\\nCOMMIT at LSN 16", fillcolor="#edf7ef", color="#4b8b60"];
 T2 [label="T2 BEGIN / UPDATE\\nCOMMIT at LSN 20", fillcolor="#edf7ef", color="#4b8b60"];
 T3 [label="T3 BEGIN / UPDATE\\nNo COMMIT", fillcolor="#fff7e7", color="#b08a3c"];
 T4 [label="T4 BEGIN / UPDATE\\nNo COMMIT", fillcolor="#fff7e7", color="#b08a3c"];
 CR [label="CRASH\\nLSN 23", fillcolor="#fff1ed", color="#c85a45"];
 CP -> T1 -> T3 -> T2 -> T4 -> CR;
}'''
(D/'crash_recovery_timeline.dot').write_text(dot)
subprocess.run(['dot','-Tpng',str(D/'crash_recovery_timeline.dot'),'-o',str(D/'crash_recovery_timeline.png')],check=True)

# Render stdout snippets for visual evidence (not a terminal screenshot)
try:
 from PIL import Image, ImageDraw, ImageFont
 log=(ROOT/'Execution_Evidence'/'Text_Logs'/'01_simulation_run.txt').read_text().splitlines()
 # choose header + all rows + recovery summary
 chosen=log[:6]+log[6:18]+log[-15:]
 font_path='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
 font=ImageFont.truetype(font_path,13)
 line_h=19; w=1900; h=55+len(chosen)*line_h
 im=Image.new('RGB',(w,h),'white'); dr=ImageDraw.Draw(im)
 dr.text((20,12),'PYTHON SIMULATION OUTPUT CAPTURE - GENERATED FROM STDOUT LOG',fill='#224466',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16))
 y=44
 for line in chosen:
  dr.text((20,y),line[:210],fill='#17212b',font=font); y+=line_h
 im.save(ROOT/'Execution_Evidence'/'Output_Captures'/'01_simulation_output.png')
except Exception as e:
 print('capture skip',e)
print('Figures created in',D)
