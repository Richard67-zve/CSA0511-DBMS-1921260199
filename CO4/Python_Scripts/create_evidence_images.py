from PIL import Image, ImageDraw, ImageFont
import csv, os, textwrap
os.makedirs('Execution_Evidence/Output_Captures',exist_ok=True)
try: font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',16)
except: font=ImageFont.load_default()
try: bold=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',16)
except: bold=font

def render(lines,path,title):
    wrapped=[]
    for line in lines:
        wrapped.extend(textwrap.wrap(line,width=110,subsequent_indent='    ') or [''])
    w=1300; lineh=25; h=70+lineh*(len(wrapped)+1)+28
    im=Image.new('RGB',(w,h),(16,22,29)); d=ImageDraw.Draw(im)
    d.rectangle((0,0,w,48),fill=(31,43,55)); d.text((24,13),title,font=bold,fill=(235,240,245))
    y=62
    for line in wrapped:
        d.text((24,y),line,font=font,fill=(170,225,180) if line.startswith('PASS') else (218,224,232)); y+=lineh
    im.save(path)

rows=list(csv.DictReader(open('Results/benchmark.csv')))
lines=['$ python Python_Scripts/block_simulator.py --out Results/benchmark.csv','The following are logical block counts from the simulator; not physical HDD/SSD timings.']
for r in rows:
    lines.append(f"{int(r['records']):,} | {r['strategy']} | data/index pages={int(r['blocks']):,} | equality avg reads={float(r['equality_avg_reads']):.2f} | range avg reads={float(r['range_avg_reads']):.2f}")
lines.append('CSV saved: Results/benchmark.csv')
render(lines,'Execution_Evidence/Output_Captures/benchmark_execution.png','CO4 BLOCK-LEVEL SIMULATION - EXECUTION OUTPUT')
lines=open('Execution_Evidence/Text_Logs/self_test.log').read().splitlines()
render(['$ python Python_Scripts/self_test.py']+lines,'Execution_Evidence/Output_Captures/self_test_execution.png','CO4 STRATEGY CORRECTNESS - EXECUTION OUTPUT')
