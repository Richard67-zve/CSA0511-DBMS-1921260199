"""Run every CO4 simulation, trace and evidence-generation step in order."""
import subprocess, sys, os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
steps=[
    [sys.executable,'Python_Scripts/block_simulator.py','--out','Results/benchmark.csv'],
    [sys.executable,'Python_Scripts/self_test.py'],
    [sys.executable,'Python_Scripts/tree_hash_traces.py'],
    [sys.executable,'Python_Scripts/hash_traces.py'],
    [sys.executable,'Python_Scripts/generate_transactions.py','--size','100','--out','Data/transactions_preview.csv'],
    [sys.executable,'Python_Scripts/make_charts.py'],
    [sys.executable,'Python_Scripts/create_evidence_images.py'],
]
for i,cmd in enumerate(steps,1):
    print(f'[{i}/{len(steps)}] $ '+' '.join(cmd),flush=True)
    subprocess.run(cmd,cwd=ROOT,check=True)
print('CO4 simulation and evidence generation completed successfully.')
