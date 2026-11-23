#!/usr/bin/env python3
from pathlib import Path
import json, csv, math
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Assignment'; OUT.mkdir(exist_ok=True)
D=ROOT/'Diagrams'; O=ROOT/'outputs'
RESULT=json.load(open(O/'simulation_results.json'))
CSV=list(csv.DictReader(open(O/'performance_results.csv',newline='')))

NAVY='17365D'; BLUE='1F4E79'; LIGHT='D9EAF7'; PALE='EEF4FA'; GREY='666666'; MID='A6A6A6'; WHITE='FFFFFF'; GREEN='E2F0D9'; RED='FCE4D6'; GOLD='FFF2CC'

def set_cell_shading(cell, fill):
    tcPr=cell._tc.get_or_add_tcPr(); shd=tcPr.find(qn('w:shd'))
    if shd is None: shd=OxmlElement('w:shd'); tcPr.append(shd)
    shd.set(qn('w:fill'),fill)

def set_cell_margins(cell, top=75, start=90, bottom=75, end=90):
    tc=cell._tc; tcPr=tc.get_or_add_tcPr(); tcMar=tcPr.first_child_found_in('w:tcMar')
    if tcMar is None: tcMar=OxmlElement('w:tcMar'); tcPr.append(tcMar)
    for m,v in [('top',top),('start',start),('bottom',bottom),('end',end)]:
        node=tcMar.find(qn('w:'+m))
        if node is None: node=OxmlElement('w:'+m); tcMar.append(node)
        node.set(qn('w:w'),str(v)); node.set(qn('w:type'),'dxa')

def set_table_borders(table, color='B4C7E7', sz='5'):
    tblPr=table._tbl.tblPr; borders=tblPr.first_child_found_in('w:tblBorders')
    if borders is None: borders=OxmlElement('w:tblBorders'); tblPr.append(borders)
    for edge in ('top','left','bottom','right','insideH','insideV'):
        tag='w:'+edge; el=borders.find(qn(tag))
        if el is None: el=OxmlElement(tag); borders.append(el)
        el.set(qn('w:val'),'single'); el.set(qn('w:sz'),sz); el.set(qn('w:space'),'0'); el.set(qn('w:color'),color)

def mark_repeat_table_header(row):
    trPr=row._tr.get_or_add_trPr(); tblHeader=OxmlElement('w:tblHeader'); tblHeader.set(qn('w:val'),'true'); trPr.append(tblHeader)

def prevent_row_split(row):
    trPr=row._tr.get_or_add_trPr(); cant=OxmlElement('w:cantSplit'); trPr.append(cant)

def set_keep(paragraph, keep=True):
    paragraph.paragraph_format.keep_with_next=keep

def add_field(run, field):
    fldChar1=OxmlElement('w:fldChar'); fldChar1.set(qn('w:fldCharType'),'begin')
    instrText=OxmlElement('w:instrText'); instrText.set(qn('xml:space'),'preserve'); instrText.text=field
    fldChar2=OxmlElement('w:fldChar'); fldChar2.set(qn('w:fldCharType'),'end')
    run._r.append(fldChar1); run._r.append(instrText); run._r.append(fldChar2)

def add_text(doc, text='', bold_start=None, italic=False, align=None, style=None, after=5, before=0):
    p=doc.add_paragraph(style=style)
    if align is not None: p.alignment=align
    p.paragraph_format.space_after=Pt(after); p.paragraph_format.space_before=Pt(before)
    p.paragraph_format.line_spacing=1.08
    if bold_start and text.startswith(bold_start):
        r=p.add_run(bold_start); r.bold=True
        p.add_run(text[len(bold_start):])
    else:
        r=p.add_run(text); r.italic=italic
    return p

def h1(doc, text):
    p=doc.add_paragraph(style='Heading 1'); p.add_run(text); set_keep(p); return p

def h2(doc, text):
    p=doc.add_paragraph(style='Heading 2'); p.add_run(text); set_keep(p); return p

def h3(doc, text):
    p=doc.add_paragraph(style='Heading 3'); p.add_run(text); set_keep(p); return p

def bullet(doc, text, level=0):
    p=doc.add_paragraph(style='List Bullet' if level==0 else 'List Bullet 2')
    p.paragraph_format.space_after=Pt(2); p.paragraph_format.line_spacing=1.03
    p.add_run(text); return p

def numbered(doc, text):
    p=doc.add_paragraph(style='List Number'); p.paragraph_format.space_after=Pt(2); p.add_run(text); return p

def code(doc, text, fontsize=8.1):
    p=doc.add_paragraph()
    p.paragraph_format.left_indent=Inches(.18); p.paragraph_format.right_indent=Inches(.12)
    p.paragraph_format.space_before=Pt(3); p.paragraph_format.space_after=Pt(7)
    p.paragraph_format.line_spacing=1.0; p.paragraph_format.keep_together=True
    pPr=p._p.get_or_add_pPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),'F2F5F8'); pPr.append(shd)
    border=OxmlElement('w:pBdr'); left=OxmlElement('w:left'); left.set(qn('w:val'),'single'); left.set(qn('w:sz'),'16'); left.set(qn('w:color'),BLUE); border.append(left); pPr.append(border)
    r=p.add_run(text); r.font.name='Consolas'; r._element.rPr.rFonts.set(qn('w:eastAsia'),'Consolas'); r.font.size=Pt(fontsize); r.font.color.rgb=RGBColor.from_string('243746')
    return p

def table(doc, headers, rows, widths=None, fontsize=8.5, header_fill=BLUE, align_center_cols=None):
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=False
    if widths:
        for i,w in enumerate(widths):
            for c in t.columns[i].cells: c.width=Inches(w)
    hdr=t.rows[0]; mark_repeat_table_header(hdr); prevent_row_split(hdr)
    for i,txt in enumerate(headers):
        c=hdr.cells[i]; set_cell_shading(c,header_fill); set_cell_margins(c)
        c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p=c.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(0)
        r=p.add_run(str(txt)); r.bold=True; r.font.size=Pt(fontsize); r.font.color.rgb=RGBColor(255,255,255)
    for ri,row in enumerate(rows):
        new_row=t.add_row(); prevent_row_split(new_row); cells=new_row.cells
        for i,val in enumerate(row):
            c=cells[i]; set_cell_margins(c); c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if widths: c.width=Inches(widths[i])
            if ri%2==1: set_cell_shading(c,'F4F7FA')
            p=c.paragraphs[0]; p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1.0
            if align_center_cols and i in align_center_cols: p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            r=p.add_run(str(val)); r.font.size=Pt(fontsize)
    set_table_borders(t)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return t

def figure(doc, path, caption, width=6.1):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(1)
    p.add_run().add_picture(str(path),width=Inches(width))
    c=doc.add_paragraph(); c.alignment=WD_ALIGN_PARAGRAPH.CENTER; c.paragraph_format.space_after=Pt(7)
    r=c.add_run(caption); r.italic=True; r.font.size=Pt(8.5); r.font.color.rgb=RGBColor.from_string(GREY)

def task_title(doc, n, title, marks):
    h1(doc,f'TASK {n} - {title.upper()} ({marks} MARKS)')

def fmt(x, digits=2):
    return f'{float(x):,.{digits}f}'

# Document and styles
doc=Document()
sec=doc.sections[0]
sec.page_width=Inches(8.27); sec.page_height=Inches(11.69)
sec.top_margin=Inches(.72); sec.bottom_margin=Inches(.68); sec.left_margin=Inches(.72); sec.right_margin=Inches(.72)
styles=doc.styles
normal=styles['Normal']; normal.font.name='Calibri'; normal.font.size=Pt(10.5); normal.font.color.rgb=RGBColor.from_string('222222')
normal.paragraph_format.space_after=Pt(5); normal.paragraph_format.line_spacing=1.08
for name,size in [('Title',26),('Heading 1',17),('Heading 2',13.5),('Heading 3',11.5)]:
    st=styles[name]; st.font.name='Calibri'; st.font.size=Pt(size); st.font.bold=True; st.font.color.rgb=RGBColor.from_string(NAVY if name!='Title' else '1F2937')
    st.paragraph_format.space_before=Pt(12 if name=='Heading 1' else 9); st.paragraph_format.space_after=Pt(5)
    st.paragraph_format.keep_with_next=True
for name in ['List Bullet','List Bullet 2','List Number']:
    styles[name].font.name='Calibri'; styles[name].font.size=Pt(10.3)

# Header / footer
header=sec.header.paragraphs[0]; header.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=header.add_run('CSA05  |  DATABASE MANAGEMENT SYSTEMS  |  ASSIGNMENT 5 - CO5'); r.font.name='Calibri'; r.font.size=Pt(8); r.font.color.rgb=RGBColor.from_string(GREY)
# thin bottom border
pPr=header._p.get_or_add_pPr(); pbdr=OxmlElement('w:pBdr'); bottom=OxmlElement('w:bottom'); bottom.set(qn('w:val'),'single'); bottom.set(qn('w:sz'),'4'); bottom.set(qn('w:space'),'4'); bottom.set(qn('w:color'),'D9E2F3'); pbdr.append(bottom); pPr.append(pbdr)
footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
rr=footer.add_run('Page '); rr.font.size=Pt(8); rr.font.color.rgb=RGBColor.from_string(GREY)
rr=footer.add_run(); rr.font.size=Pt(8); rr.font.color.rgb=RGBColor.from_string(GREY); add_field(rr,'PAGE')

# COVER
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after=Pt(20)
p.add_run().add_picture(str(D/'engineering_logo_crop.png'),width=Inches(1.65))
p.add_run('      ')
p.add_run().add_picture(str(D/'simats_crest_crop.png'),width=Inches(1.42))
for txt,size,color,bold,under in [
    ('DATABASE MANAGEMENT SYSTEMS',20,'111111',True,False),
    ('ASSIGNMENT 5 - CO5',22,NAVY,True,True),
]:
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(12); p.paragraph_format.space_after=Pt(6)
    r=p.add_run(txt); r.bold=bold; r.font.size=Pt(size); r.font.color.rgb=RGBColor.from_string(color)
    if under: r.underline=True
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(18); p.paragraph_format.space_after=Pt(22)
r=p.add_run('CONCURRENCY AND RECOVERY FOR\nIRRIGATION WATER QUOTA ALLOCATION'); r.bold=True; r.underline=True; r.font.size=Pt(20); r.font.color.rgb=RGBColor.from_string(NAVY)
cover_rows=[
    ('Name','M. Richard'),('Register Number','1921260199'),('Department','B.Tech IT'),('Course Code','CSA05'),
    ('Course','Database Management Systems'),('Code Repository Package','CO5_GitHub_Upload.zip (ready-to-upload package)'),('Submission Date','____________________________')]
table(doc,['DETAIL','INFORMATION'],cover_rows,[2.35,4.1],fontsize=10,header_fill=NAVY)
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(14)
r=p.add_run('TOTAL MARKS: 50  |  TASKS: 1-12  |  DURATION: ONE WEEK'); r.bold=True; r.font.color.rgb=RGBColor.from_string(BLUE); r.font.size=Pt(11)

# CONTENTS
doc.add_page_break()
h1(doc,'REPORT CONTENTS')
contents=[
('1','Introduction, case interpretation and experiment scope'),
('2','Task 1 - Design alternative concurrency-control strategies'),
('3','Task 2 - Transaction operations and ACID requirements'),
('4','Task 3 - Schedule construction and serializability'),
('5','Task 4 - Recoverability, ACA and strictness'),
('6','Task 5 - Locking, 2PL variants and deadlock handling'),
('7','Task 6 - Timestamp ordering and Thomas’ rule'),
('8','Task 7 - Write-ahead logging and restart recovery'),
('9','Task 8 - Python implementation and reproducible tests'),
('10','Task 9 - Measured simulation performance'),
('11','Task 10 - Theory versus experimental behaviour'),
('12','Task 11 - Baseline strategy recommendation'),
('13','Task 12 - Adaptation for drought concentration and farm ceilings'),
('14','Conclusion and references'),
('A','Appendix A - Reproducibility and evidence map')]
table(doc,['SECTION','CONTENTS'],contents,[.85,5.6],fontsize=9.5)

# 1 INTRODUCTION
h1(doc,'1. INTRODUCTION AND CASE INTERPRETATION')
add_text(doc,'This report addresses the RiverGate Cooperative irrigation-water quota allocation scenario. Each approved delivery moves a conserved quantity of entitlement tokens from a source canal holding pool to a destination farm holding pool. The source allowance check and the debit must occur in the same transaction as the destination credit. If two allocation-office operators approve requests against the same remaining balance without concurrency control, they can both spend the same tokens. A regional report can also combine balances read at incompatible moments and display a total that never existed as a committed state.')
add_text(doc,'The assignment gives a planning workload of 67 requests per second. It explicitly says that the controlled tests use bursts and must not be represented as observed production traffic. The changed requirement concentrates 81% of allocations on one canal, adds a daily ceiling for each farm and requires restart to complete within 35 seconds. The recommended design must therefore address consistency first, then contention, retry behaviour and recoverability.')
h2(doc,'1.1 Transaction and conservation model')
add_text(doc,'A successful delivery has a stable DeliveryID, a source pool, a destination pool, an amount and a business date. For a transfer of q tokens from pool A to pool B: A is reduced by q and B is increased by q. The total across all affected pools must remain unchanged. The DeliveryID is unique so replaying the same gateway or office request returns its stored outcome instead of moving the tokens twice.')
code(doc,'BEGIN\n  claim DeliveryID (unique idempotency key)\n  read source and destination balances\n  validate q > 0 and source_balance >= q\n  debit source by q\n  credit destination by q\n  write allocation audit record\nCOMMIT\n\nOn any validation, write or system failure: ROLLBACK; do not expose a partial debit/credit.')
h2(doc,'1.2 Experiment assumptions and reproducibility')
assumptions=[
('Scenario planning rate','67 requests/second (given by the assignment; not measured production traffic)'),
('Generated bursts','10, 50, 200 and 1,000 transactions'),
('Distributions','Uniform across 32 pools; integer-rounded 81% hot-source target to P00 for skew81 (exact at 200 and 1,000; nearest whole count at 10 and 50)'),
('Arrival spacing','1/67 second = 14.925 ms between generated requests'),
('Service assumption','20 ms per transaction attempt; an explicit modelling assumption, not a measured DBMS latency'),
('Initial pool state','100,000 tokens in each of 32 pools; 3,200,000 total tokens'),
('Admission control','Conservative strict 2PL model uses 16 admission slots in the main experiment'),
('Timestamp variation','Deterministic 0-34 ms pre-commit timing jitter; 0-8 ms retry jitter'),
('Random seed','5505; the same generated source/destination/amount/arrival records are passed to each candidate')]
table(doc,['PARAMETER','VALUE / INTERPRETATION'],assumptions,[1.75,4.7],fontsize=8.8)
add_text(doc,'The simulator is a transaction-level discrete-event model, not MySQL, Oracle or a physical storage benchmark. In strict 2PL, the 20 ms interval is treated as time during which the transaction owns its exclusive locks. In timestamp ordering, the 20 ms interval represents work before an atomic validation/commit event; this allows optimistic overlap but can cause retries. The distinction is stated so that timing differences are not mistaken for a general performance guarantee.')
h2(doc,'1.3 Scope boundary for the farm ceiling')
add_text(doc,'The first simulation phase enforces token conservation and replay safety, but does not silently assume that the daily farm ceiling exists in the baseline schema. Task 12 adds a separate guard test and proposes a FARM_DAILY_USAGE row keyed by (FarmID, AllocationDate). The guard is read, checked and updated inside the same atomic delivery transaction. A row-level CHECK cannot safely enforce a sum across multiple allocations or deliveries by itself.')
figure(doc,D/'concurrency_strategies.png','Figure 1. Three concurrency-control alternatives and the negative no-control reference.',6.0)

# TASK 1
task_title(doc,1,'Design Alternative Concurrency-Control Strategies',5)
h2(doc,'2.1 Strategy A - Whole-system serialization')
add_text(doc,'A single global transaction gate admits one quota movement at a time. An allocation obtains the gate, reads the source and destination, validates the source allowance, applies the debit and credit, writes the delivery outcome and commits before the next allocation starts. A regional report either runs between movements or uses a defined snapshot. This is the correctness baseline: it is simple to explain and excludes concurrent lost updates, but unrelated canals cannot progress at the same time.')
code(doc,'SERIAL-ALLOCATE(request):\n  wait until global_gate is free\n  acquire global_gate\n  BEGIN\n    if DeliveryID already committed: return saved outcome\n    read source_balance, destination_balance\n    if source_balance < amount: ROLLBACK; reject\n    write source_balance - amount\n    write destination_balance + amount\n    insert committed DeliveryID\n  COMMIT\n  release global_gate')
add_text(doc,'Failure excluded: two allocation clerks cannot both read the same 100-token source allowance and each spend 70. The second clerk sees the first committed balance. Cost: every write, including movements on independent canals, waits behind the same gate.')
h2(doc,'2.2 Strategy B - Conservative strict two-phase locking')
add_text(doc,'The application knows the source and destination pool IDs before it changes either row. The transaction requests all required exclusive (X) locks as a set. It does not hold one partial lock while waiting for the other. Once all locks are granted, the transaction performs the debit and credit, records the idempotency outcome and retains its X locks until COMMIT or ROLLBACK. This is conservative 2PL (all locks requested before execution) combined with strict 2PL (exclusive locks retained through commit).')
code(doc,'STRICT-2PL-ALLOCATE(request):\n  if DeliveryID has committed: return saved outcome\n  lock_set = {X(source_pool), X(destination_pool), X(delivery_id)}\n  request the complete lock_set atomically\n  if lock_set unavailable: queue before execution; hold no partial set\n  BEGIN\n    read the two pool rows\n    validate source_balance >= amount\n    stage source debit and destination credit\n    insert the unique DeliveryID outcome\n  COMMIT\n  release all locks\n  on error: ROLLBACK; release all locks')
add_text(doc,'Failure excluded: conflicting movements cannot read and overwrite the same pool state at the same time. The schedule is conflict-serializable and strict. Because the lock set is acquired atomically, the generated simulator does not form partial-lock wait-for cycles. A dynamic strict-2PL example is still analysed in Task 5 to show why ordinary lock acquisition order may deadlock.')
h2(doc,'2.3 Strategy C - Timestamp ordering')
add_text(doc,'Each transaction receives a unique timestamp TS(T) when it begins. Every pool item X stores read-timestamp R-TS(X) and write-timestamp W-TS(X). A read is accepted only when TS(T) is not older than W-TS(X). A write is accepted only when TS(T) is not older than either R-TS(X) or W-TS(X). A rejected transaction discards its staged work and restarts with a new timestamp. The RiverGate movement updates both pool rows as one validated commit unit.')
code(doc,'TO-ALLOCATE(request, TS):\n  read source and destination from the transaction snapshot\n  if TS < W-TS(source) or TS < W-TS(destination): ABORT and retry\n  if TS < R-TS(source) or TS < R-TS(destination): ABORT and retry\n  validate source allowance and the farm/day predicate\n  atomically publish both debit and credit at commit\n  set R-TS and W-TS for every accessed item to max(old, TS)\n  COMMIT')
add_text(doc,'Failure excluded: a late older operation cannot overwrite a value already written by a newer timestamp. Timestamp ordering does not create a lock wait-for cycle because a stale operation is rejected rather than waiting for a younger transaction. The cost is restart work under high conflict. Basic TO alone is not automatically strict; the candidate used here publishes only the atomic validated result and does not expose uncommitted values.')
h2(doc,'2.4 No control - negative reference')
add_text(doc,'Without a scheduler, two allocation clerks can read the same source balance and write competing debits. A report can read a canal pool before a movement and a farm pool after it. This version is included only as a negative reference: token conservation and consistent reporting are not guaranteed.')
h2(doc,'2.5 Comparative decision')
table(doc,['ALTERNATIVE','IDENTITY / CONTROL PRINCIPLE','STRENGTH','LIMITATION'],[
('A. Global serial','One global queue; total order','Simple correctness baseline','Unrelated requests block one another'),
('B. Conservative strict 2PL','Known resource set; X locks to commit','Strict and conflict-serializable; no partial-lock deadlock','Hot pool creates a long lock queue'),
('C. Strict timestamp order','R-TS/W-TS validation; restart stale work','No lock deadlocks; high overlap on independent work','Retry rate rises with conflicting timestamps'),
('No control','No serialization mechanism','Fast only in an unsafe sense','Lost update, dirty data and mixed summary possible')],[1.05,1.55,2.0,1.85],fontsize=8.0)
add_text(doc,'The baseline recommendation is conservative strict 2PL because the transaction knows its complete resource set, the source check and debit are protected, and the commit outcome is easy to audit. Task 12 revisits that choice when the new concentration changes the measured contention pattern.')

# TASK 2
task_title(doc,2,'Identify Transaction Operations and ACID Requirements',2)
h2(doc,'3.1 Transaction programs')
add_text(doc,'A movement transaction is an update program: it validates a unique delivery request, reads the two balances, checks the source allowance, stages both writes and commits. The report is a read-only program and should use one consistent snapshot or serializable read so that every row belongs to one logical point in time. A repeated delivery is not a second allocation; the unique DeliveryID identifies the original decision and returns its saved result.')
code(doc,"""MOVE-TOKENS(DeliveryID, SourceID, FarmID, Amount, BusinessDate):
  BEGIN
    INSERT Delivery(DeliveryID, Status='PENDING')  -- unique key
    if duplicate key: return existing committed result
    read SourcePool.Remaining, FarmPool.Balance
    read FarmDailyUsage.Used for (FarmID, BusinessDate)
    VALIDATE Amount > 0
    VALIDATE SourcePool.Remaining >= Amount
    VALIDATE Used + Amount <= DailyCeiling
    UPDATE SourcePool SET Remaining = Remaining - Amount
    UPDATE FarmPool SET Balance = Balance + Amount
    UPDATE FarmDailyUsage SET Used = Used + Amount
    UPDATE Delivery SET Status='COMMITTED'
  COMMIT
  on any failure: ROLLBACK""")
code(doc,'REGIONAL-REPORT():\n  BEGIN READ ONLY WITH CONSISTENT SNAPSHOT\n    read all pool balances from one committed snapshot\n    calculate total tokens and per-canal subtotals\n  COMMIT')
h2(doc,'3.2 ACID responsibility allocation')
table(doc,['PROPERTY','RIVERGATE REQUIREMENT','PRIMARY DBMS / APPLICATION RESPONSIBILITY'],[
('Atomicity','The source debit, destination credit, daily-usage increment and delivery outcome all succeed or all roll back.','Transaction manager plus undo/redo recovery; application defines the complete unit.'),
('Consistency','Token total is conserved; balances are non-negative; daily farm ceiling is not exceeded; DeliveryID is unique.','Application validation, keys/constraints, stored procedure or guarded update; DBMS enforces declared constraints.'),
('Isolation','Concurrent movements behave as an allowed serial order; reports do not combine incompatible committed states.','Scheduler, lock manager or timestamp validator; consistent-snapshot / serializable report policy.'),
('Durability','A successful COMMIT survives a process or machine restart.','WAL log manager forces the commit record before acknowledgment; recovery redoes committed work.')],[.8,2.75,2.9],fontsize=8.2)
h2(doc,'3.3 Concrete anomalies')
table(doc,['ANOMALY','INTERLEAVING / EXAMPLE','EFFECT'],[
('Lost update','Source=100. T1 reads 100 and plans a debit of 70; T2 reads 100 and plans a debit of 60. T1 writes 30; T2 overwrites it with 40.','Both requests appear accepted although they total 130. Final source is 40, so one debit is lost; a correct serial execution must reject the second request.'),
('Dirty read','T1 debits Canal-A from 100 to 90 but has not credited Farm-1. T2 report reads 90. T1 then aborts.','The report used an uncommitted debit that never became a valid movement.'),
('Repeated / non-repeatable read','T1 reads Canal-A=100. T2 commits a debit of 10. T1 reads Canal-A again and sees 90.','One transaction observes two committed versions of the same item.'),
('Mixed summary','Report reads Canal-A=100 before a 10-token move, then reads Farm-1=50 after its credit.','The report total includes the old source and new destination versions; it may overstate the committed total by 10.'),
('Phantom','A report selects allocations where FarmDailyUsage is at or above a threshold. Another transaction inserts a new qualifying allocation before the report repeats the predicate.','The second predicate read returns an extra row; range protection or a consistent snapshot is needed.')],[1.0,3.0,2.45],fontsize=7.8)
add_text(doc,'The lost-update example is a concurrency illustration, not a suggestion that negative quotas should be accepted. With source validation and a serial schedule, the second transaction must either see the updated remaining quantity and be rejected or spend only what remains. The invariant is checked on the full transaction, not on independent writes.')

# TASK 3
task_title(doc,3,'Analyse Schedules for Serializability',6)
h2(doc,'4.1 Notation and precedence-graph rule')
add_text(doc,'R1(A) means transaction T1 reads item A; W1(A) means T1 writes A; C1 and A1 mean commit and abort. Two operations conflict when they belong to different transactions, access the same item and at least one is a write. If a conflicting operation of Ti precedes one of Tj, draw edge Ti -> Tj. A schedule is conflict-serializable exactly when its precedence graph is acyclic.')
h2(doc,'4.2 Destination overwrite - cycle and lost credit')
add_text(doc,'Initial balances are A=100, C=100 and B=20. T1 moves 10 from A to B; T2 moves 5 from C to B. Both destination reads happen before either write, so both compute a replacement value from B=20.')
code(doc,'S1: R1(A=100); R1(B=20); R2(C=100); R2(B=20);\n    W1(A=90); W1(B=30); W2(C=95); W2(B=25); C1; C2')
table(doc,['CONFLICTING PAIR','EDGE','REASON'],[
('R1(B) before W2(B)','T1 -> T2','T1 reads B before T2 overwrites B'),
('R2(B) before W1(B)','T2 -> T1','T2 reads B before T1 overwrites B'),
('W1(B) before W2(B)','T1 -> T2','Both write the same destination')],[2.35,1.1,3.0],fontsize=8.3)
figure(doc,D/'destination_overwrite_cycle.png','Figure 2. Destination overwrite precedence graph: T1 and T2 form a cycle.',4.4)
add_text(doc,'The destination schedule contains both T1 -> T2 and T2 -> T1, so it is not conflict-serializable. Final B=25, but two successful credits should have produced B=35. A, C and B together lose 10 tokens. A strict transaction scheduler prevents both transactions from using the same stale destination value.')
h2(doc,'4.3 Inconsistent inventory scan')
code(doc,'Initial: Canal-A=100, Farm-B=40, total=140\nRReport(A)=100\nW1(A=90)\nW1(B=50)\nRReport(B)=50\nReport displays 100+50=150\nC1')
add_text(doc,'The report reads A before T1 and B after T1. The conflicts give Report -> T1 from RReport(A) before W1(A), and T1 -> Report from W1(B) before RReport(B). The cycle proves that this interleaving is not conflict-serializable. A consistent snapshot would return either (100,40) or (90,50), both totalling 140.')
figure(doc,D/'inconsistent_scan_cycle.png','Figure 3. Precedence graph for the mixed-time regional report.',4.8)
h2(doc,'4.4 Independent canal-pool operations')
code(doc,'T1: R(A), W(A), R(B), W(B), C1\nT2: R(C), W(C), R(D), W(D), C2\nResource sets are disjoint: {A,B} intersect {C,D} = empty.')
add_text(doc,'No pair of operations conflicts because the transactions access disjoint pools. The precedence graph has no edges; either serial order is equivalent. This is the concurrency that a global lock unnecessarily suppresses and a resource-based scheduler can preserve.')
h2(doc,'4.5 Blind dispatch-status writes: conflict versus view serializability')
code(doc,"""S2: W1(DispatchStatus='READY');
    W2(DispatchStatus='DISPATCHED');
    W1(DispatchStatus='RELEASED')""")
add_text(doc,'The first W1 before W2 gives T1 -> T2. W2 before the final W1 gives T2 -> T1. The graph is cyclic, so the schedule is not conflict-serializable. There are no reads and the final writer is T1. The serial order T2 then T1 has the same final writer and is view-equivalent; therefore this blind-write schedule is view-serializable even though it is not conflict-serializable.')
figure(doc,D/'blind_write_cycle.png','Figure 4. Precedence graph for the blind-write schedule: T1 <-> T2.',4.4)
h2(doc,'4.6 Order-preserving interleaving counts')
add_text(doc,'For two transactions whose internal operation orders must be preserved, if T1 has m operations and T2 has n operations, the number of possible interleavings is C(m+n,m). For the chosen movement trace, T1 has five operations (read source, read destination, write source, write destination, commit) and T2 has four operations. Therefore C(9,5)=9!/(5!4!)=126 order-preserving interleavings. This counts candidate interleavings, not the number that are correct or serializable.')

# TASK 4
task_title(doc,4,'Analyse Recoverability',4)
h2(doc,'5.1 Definitions')
add_text(doc,'Recoverability, cascadelessness and strictness are separate from conflict serializability. A schedule can be serializable yet permit a dirty read, and a schedule can be recoverable without being cascadeless.')
table(doc,['PROPERTY','RULE','RIVERGATE MEANING'],[
('Recoverable','If Tj reads a value written by Ti, Tj cannot commit before Ti commits.','A dependent allocation decision must not be durable before the movement it used.'),
('ACA / Cascadeless','A transaction reads only values written by committed transactions.','A report or movement never reads a canal balance from an uncommitted update.'),
('Strict','No transaction may read or overwrite an item written by an uncommitted transaction.','Both dirty reads and dirty writes are prevented; recovery is simpler.')],[1.1,2.75,2.6],fontsize=8.1)
h2(doc,'5.2 Schedule classification')
table(doc,['CLASS','SCHEDULE','WHY'],[
('Recoverable, not ACA','W1(A); R2(A); C1; C2','T2 reads T1’s uncommitted value, but T2 commits after T1.'),
('ACA, not strict','W1(A); W2(A); C1; C2','No transaction reads dirty data, but T2 overwrites A before T1 commits; strictness is violated.'),
('Strict','W1(A); C1; R2(A); W2(A); C2','T2 reads and writes only after T1 commits.'),
('Not recoverable','W1(A); R2(A); C2; A1','T2 commits using T1’s dirty value before T1 aborts.')],[1.2,2.65,2.6],fontsize=8.1)
h2(doc,'5.3 Cascading abort example')
code(doc,'T1: W(Canal-A=90)\nT2: R(Canal-A=90), W(Farm-B=10)\nT3: R(Farm-B=10), W(ReportCache=...)\nT1 aborts\n=> T2 must abort; T3 must also abort because it used T2\'s result.')
add_text(doc,'One aborted canal movement can invalidate a dependent allocation and a later report cache. Under strict scheduling, the dependent transactions cannot consume the uncommitted result, so this chain is avoided.')
h2(doc,'5.4 Why basic timestamp ordering is not automatically strict')
add_text(doc,'Basic timestamp ordering may allow an operation to pass its R-TS/W-TS test even when the transaction whose value it reads has not committed. If that writer later aborts, the reader may need a cascading abort. To make the timestamp candidate strict, reads and writes of an item changed by an uncommitted transaction must be delayed until that writer commits, or writes must be buffered and published only at an atomic commit point. The simulation uses the latter: the two pool changes are validated and published as one commit event; an aborted attempt publishes neither side.')

# TASK 5
task_title(doc,5,'Analyse Locking and Deadlock Handling',3)
h2(doc,'6.1 Shared / exclusive lock compatibility')
table(doc,['REQUEST / HELD','S (SHARED)','X (EXCLUSIVE)'],[
('S (shared)','Compatible','Not compatible'),('X (exclusive)','Not compatible','Not compatible')],[2.0,2.2,2.2],fontsize=9,align_center_cols={1,2})
add_text(doc,'A report may hold S(A) with another report. An allocation movement requires X locks because it changes a balance. An S-to-X upgrade is allowed only when no other transaction holds a conflicting S or X lock.')
h2(doc,'6.2 Read-to-write upgrade trace')
code(doc,'1. T1 obtains S(Canal-A) and reads 100.\n2. T2 obtains S(Canal-A) and reads 100.\n3. T1 requests upgrade S->X; it waits because T2 still holds S.\n4. T2 requests upgrade S->X; it waits because T1 still holds S.\n5. Wait-for graph: T1 -> T2 and T2 -> T1. A cycle exists.')
add_text(doc,'The same pattern occurs when two allocation clerks first inspect a shared quota row and then both try to debit it. A transaction may avoid this upgrade deadlock by acquiring the required X lock before reading for update, or by using a single guarded update.')
h2(doc,'6.3 Two-phase locking variants')
table(doc,['VARIANT','LOCKING RULE','RIVERGATE CONSEQUENCE'],[
('Basic 2PL','Growing phase acquires; shrinking phase releases; no new lock after first release.','Serializability, but locks can be released before commit and dirty reads/writes may remain possible.'),
('Conservative 2PL','Acquire the complete required lock set before execution.','Avoids deadlock when the set is known; a blocked transaction holds no partial lock.'),
('Strict 2PL','Retain all X locks until commit/abort.','Prevents dirty reads/writes on updated pool rows and simplifies recovery.'),
('Rigorous 2PL','Retain both S and X locks until commit/abort.','Strongest hold policy; reports can hold shared locks longer and increase blocking.')],[1.05,2.65,2.75],fontsize=8.0)
h2(doc,'6.4 Wait-for cycle and victim choice')
figure(doc,D/'wait_for_deadlock.png','Figure 4. T1 waits for B held by T2, while T2 waits for A held by T1.',4.5)
add_text(doc,'T1 holds X(A) and requests X(B); T2 holds X(B) and requests X(A). The wait-for edges form T1 -> T2 -> T1. The detector chooses the younger T2 as victim, rolls it back, releases B and allows T1 to proceed. T2 later restarts from its original DeliveryID; idempotency prevents it from applying the movement twice if a prior outcome had in fact committed.')
h2(doc,'6.5 Wait-die and wound-wait on the same resources')
table(doc,['POLICY','OLDER T1 REQUESTS B HELD BY YOUNGER T2','YOUNGER T2 REQUESTS A HELD BY OLDER T1'],[
('Wait-die','Older requester may wait.','Younger requester dies (aborts) instead of waiting.'),
('Wound-wait','Older requester wounds/aborts younger holder T2.','Younger requester waits for older T1.')],[1.05,2.65,2.75],fontsize=8.0)
add_text(doc,'Both timestamp-based deadlock-prevention rules avoid a cycle by restricting which age may wait. They do not guarantee that a particular young transaction never starves. A retry can repeatedly lose under a hot canal. A FIFO queue per item, bounded retry backoff and retry-count aging can reduce unfairness, but must not be described as a proof of starvation freedom. Any priority aging rule must preserve the transaction timestamp used for correctness or explicitly restart with a new timestamp.')

# TASK 6
task_title(doc,6,'Analyse Timestamp-Based Concurrency Control',3)
h2(doc,'7.1 Timestamp tests')
table(doc,['OPERATION','ACCEPTANCE TEST FOR ITEM X','UPDATE'],[
('Read X by T','Accept if TS(T) >= W-TS(X); otherwise abort/restart.','R-TS(X) = max(R-TS(X), TS(T)).'),
('Write X by T','Accept if TS(T) >= R-TS(X) and TS(T) >= W-TS(X); otherwise abort/restart.','W-TS(X) = TS(T) after the write is accepted.')],[1.0,3.1,2.35],fontsize=8.1)
h2(doc,'7.2 Late older transaction - read is rejected')
code(doc,'TS(T1)=10 (older); TS(T2)=20 (younger).\nT2 writes Canal-A and commits: W-TS(A)=20.\nT1 later requests R(A).\nTest: 10 < W-TS(A)=20 => reject T1 and restart it.\nRetry receives TS=21 and reads the committed new value.')
h2(doc,'7.3 Late older transaction - write is rejected after a read')
code(doc,'TS(T1)=10: R(A), so R-TS(A)=10; T1 computes a debit.\nTS(T2)=20: W(A), commit; W-TS(A)=20.\nT1 then attempts W(A).\nTest: 10 < W-TS(A)=20 => reject T1; discard its staged debit.\nRestart with a fresh TS; reread and revalidate the balance.')
h2(doc,'7.4 Thomas’ write rule and conditional quota update')
add_text(doc,'Thomas’ write rule may ignore an obsolete blind write when TS(T) < W-TS(X): a newer write already makes the older assignment irrelevant. If TS(T) < R-TS(X), the transaction is still rejected because a newer transaction has read the item and the old write would violate timestamp order. This optimisation is suitable only when the older write is a blind assignment that has been superseded and has no required side effects.')
add_text(doc,'A quota movement is not an obsolete blind assignment. Its debit is conditional on the source balance and must be paired with a credit to another pool. Ignoring an older debit would silently discard a real request and could violate token conservation or the farm ceiling. The safe action is to abort, reread the current source and destination, recheck the predicate and retry the complete movement.')
h2(doc,'7.5 Deadlock freedom and repeated aborts')
add_text(doc,'Timestamp ordering does not wait for resource locks, so it cannot form a lock wait-for cycle. This does not mean every transaction completes immediately: an older transaction that is delayed behind a newer committed write can be repeatedly rejected. The 81% hot-canal workload therefore creates validation/retry work even though it creates no timestamp wait-for deadlock. A retry limit should return a controlled temporary-failure response, not bypass the consistency test.')

# TASK 7
task_title(doc,7,'Design the Recovery Strategy',4)
h2(doc,'8.1 Write-ahead log structure and force rules')
add_text(doc,'Each update record contains at least (LSN, TxnID, ItemID, before-image, after-image). The log also contains BEGIN, COMMIT, ABORT and checkpoint records. A record is appended before the corresponding data page can be written. The log record must be durable before the page containing its after-image is flushed (write-ahead rule). Before the application receives COMMIT success, the commit record and all preceding log records for that transaction are forced to stable storage (commit-force rule).')
code(doc,'BEGIN(T1)\nUPDATE(T1, Canal-A, before=100, after=80)\nUPDATE(T1, Farm-1,  before=20,  after=40)\nCOMMIT(T1)   -- force log through this LSN before ACK')
h2(doc,'8.2 Clean checkpoint definition')
add_text(doc,'A clean checkpoint in this report is defined as a quiescent checkpoint: temporarily stop admitting new movements, wait for active transactions to commit or abort, flush all dirty data pages and the log through the checkpoint LSN, write CHECKPOINT_END and then resume admissions. Because no transaction remains active at the checkpoint boundary, restart can begin from that checkpoint and process only the later log tail. This is a deliberately clear model; a fuzzy checkpoint would require an active-transaction table and dirty-page table.')
h2(doc,'8.3 Immediate versus deferred update')
table(doc,['METHOD','WHEN DATA PAGES MAY CHANGE','RECOVERY WORK'],[
('Immediate update','A page may be written before COMMIT, but WAL ensures its update log is durable first.','Redo committed winners as needed; undo uncommitted losers using before-images.'),
('Deferred update','Uncommitted after-images are kept in log/buffers and are not written to database pages.','Redo committed winners if pages were not flushed; no loser undo is needed for uncommitted page updates.')],[1.1,2.75,2.6],fontsize=8.0)
h2(doc,'8.4 Worked crash trace')
add_text(doc,'The checkpoint state is Canal-A=100, Farm-1=20, Canal-B=60, Farm-2=30 and Farm-3=10. The assignment brief refers to a crash trace but does not include fixed LSN-level rows. This report therefore states a controlled, reproducible RiverGate trace that crashes at LSN 23. T1 and T2 have commit records; T3 and T4 do not.')
log=RESULT['extras']['crash_recovery']['log']
log_rows=[]
for rec in log:
    if rec['type']=='UPDATE': detail=f"{rec['item']}: {rec['before']} -> {rec['after']}"
    else: detail=rec['type']
    log_rows.append((rec['lsn'],rec['txn'],rec['type'],detail))
table(doc,['LSN','TXN','TYPE','DETAIL'],log_rows,[.6,.75,1.0,4.1],fontsize=7.9)
figure(doc,D/'crash_recovery_timeline.png','Figure 5. Committed winners and uncommitted losers around the crash.',6.0)
table(doc,['CLASS','TRANSACTION','REASON'],[
('Winner','T1','COMMIT at LSN 16.'),('Winner','T2','COMMIT at LSN 20.'),('Loser','T3','BEGIN and updates exist; no COMMIT before crash.'),('Loser','T4','BEGIN and update exist; no COMMIT before crash.')],[1.0,1.1,4.3],fontsize=8.2)
h2(doc,'8.5 Redo, undo and recovered balances')
table(doc,['RECOVERY STEP','ACTION','RESULT'],[
('Redo winners','Redo T1 Canal-A=80; Farm-1=40; T2 Canal-B=50; Farm-2=40.','All committed movements are preserved.'),
('Undo losers in reverse LSN order','Undo T4 Canal-B 47->50; T3 Farm-3 15->10; T3 Canal-A 75->80.','All uncommitted effects are removed.'),
('Final state','Canal-A=80; Farm-1=40; Canal-B=50; Farm-2=40; Farm-3=10.','Final token total = 220, same as checkpoint total.')],[1.1,3.45,1.8],fontsize=7.9)
add_text(doc,'Under immediate update, the pre-recovery pages may contain all five after-images, so four committed updates are redone and three loser updates are undone. Under deferred update, no T3/T4 update page is written; T1/T2 still require four redo operations if the committed pages were not flushed, and no loser undo is needed. The recovery script verifies the same final balances and total.')
h2(doc,'8.6 Shadow paging')
add_text(doc,'Shadow paging keeps an old page table and writes changed pages elsewhere, then atomically switches the root pointer at commit. It avoids log-based UNDO/REDO for the changed page set, but repeated small changes to the same canal row create page copying and fragmentation. Copying or maintaining the page table also increases write amplification. For RiverGate’s frequent small quota movements, WAL with checkpoints is the preferred model because it records compact updates and supports efficient sequential recovery.')
h2(doc,'8.7 Restart-time model and 35-second limit')
add_text(doc,'The restart model uses the full offered 67 requests/second as a conservative log-generation rate. Each transaction emits 176 bytes (BEGIN, two update records and COMMIT combined) and two update records. Assume sequential log scan bandwidth 1 MiB/s, redo throughput 1,600 update records/second, undo throughput 1,500 update records/second, fixed restart cost 2 seconds and up to 200 loser update records at crash. These are declared model assumptions, not measured device speeds.')
code(doc,'T_restart(I) = 2 + (176 * 67 * I / 1,048,576)\n                  + (2 * 67 * I / 1,600) + (200 / 1,500)\n\nI = 285 seconds: T_restart = 29.21 seconds\nI = 240 seconds: T_restart = 24.93 seconds')
table(doc,['CHECKPOINT INTERVAL','LOG BYTES SINCE CHECKPOINT','REDO UPDATE RECORDS','MODELED RESTART','35s DEADLINE'],[
('285 s (original)',f"{67*285*176:,.0f}",f"{67*285*2:,.0f}",'29.21 s','Pass, 5.79 s margin'),
('240 s (proposed)',f"{67*240*176:,.0f}",f"{67*240*2:,.0f}",'24.93 s','Pass, 10.07 s margin')],[1.35,1.5,1.25,1.2,1.15],fontsize=7.8)
add_text(doc,'The original 285-second interval meets the modelled 35-second limit, but leaves only about 5.8 seconds of headroom. A 240-second interval is proposed as a margin improvement. This conclusion is conditional on the stated scan and replay rates; it must be remeasured on the actual recovery platform before production use.')

# TASK 8
task_title(doc,8,'Implement and Test the Strategies',4)
h2(doc,'9.1 Implementation structure')
add_text(doc,'The Python 3 implementation is in Python_Scripts/run_simulation.py. It generates a deterministic request list once for each size and distribution and passes that same list to all three candidates. The transaction contains DeliveryID, arrival time, source pool, destination pool and amount. Each successful delivery debits one pool and credits another by one token.')
table(doc,['CANDIDATE','IMPLEMENTED BEHAVIOUR','MEASURED COUNTERS'],[
('Global serial','One global server; start is max(arrival, previous finish).','Completed transactions; queue delay; throughput; mean/p95.'),
('Conservative strict 2PL','Acquire the full source/destination X-lock set atomically; retain until commit; 16 admission slots.','Admission wait, lock wait, throughput, mean/p95, aborts and cycles.'),
('Strict timestamp ordering','Commit-atomic R-TS/W-TS validation; late/stale attempt aborts and retries with a fresh timestamp.','Total attempts, abort/retries, throughput, mean/p95; no wait-for lock cycles.')],[1.2,3.0,2.0],fontsize=7.8)
h2(doc,'9.2 Workloads and correctness checks')
add_text(doc,'The same seed 5505 supplies all candidates. Sizes are 10, 50, 200 and 1,000 deliveries. The uniform case selects two different pools from all 32. The skew81 case uses an integer-rounded 81% target from dominant pool P00 (80% for the 10- and 50-row batches because whole requests are indivisible; exactly 81% for 200 and 1,000); the remainder is dispersed across the other 31 pools. The main tests use 67 requests/second arrival spacing and 20 ms transaction service assumption.')
bullet(doc,'All 24 candidate/distribution/size combinations complete every generated request.')
bullet(doc,'For every combination, the final token total is 3,200,000 and no pool balance becomes negative.')
bullet(doc,'The same generated request list is reused for each policy, avoiding different source/destination mixes between candidates.')
bullet(doc,'The timestamp run counts each stale attempt as an abort/retry; the strict 2PL experiment uses all-lock acquisition and has no deadlock cycle in these generated runs.')
bullet(doc,'The separate wait-for fixture creates a real dynamic-2PL cycle; the crash fixture checks winners, losers, redo, undo and recovered token total.')
h2(doc,'9.3 Boundary and domain-rule tests')
bound=RESULT['extras']['boundary_tests']
table(doc,['TEST','OBSERVED RESULT','PASS CONDITION'],[
('Empty file / empty ledger',str(bound['empty_file_ok']),'No rows and no exception.'),
('First delivery',bound['first_delivery'],'One transfer commits.'),
('Duplicate replay',bound['duplicate_replay'],'Same DeliveryID is ignored; no second transfer.'),
('Balance after replay',f"A={bound['balance_after_one_delivery_and_replay']['A']}, B={bound['balance_after_one_delivery_and_replay']['B']}",'Exactly one 10-token movement.'),
('Delete last key',str(bound['delete_last_key_ok']),'Deleting the only idempotency key leaves an empty ledger.')],[1.5,2.4,2.3],fontsize=8.0)
ceiling=RESULT['extras']['farm_ceiling_extension']
table(doc,['SEPARATE TASK 12 GUARD FIXTURE','RESULT'],[
('Requests evaluated','1,000'),('Test-only daily ceiling','25 tokens per farm per day'),('Accepted within ceiling',str(ceiling['accepted_under_fixture_guard'])),('Rejected by ceiling',str(ceiling['rejected_by_farm_ceiling'])),('Maximum accepted farm usage',str(ceiling['maximum_recorded_farm_usage']))],[3.2,3.0],fontsize=8.2)
add_text(doc,'The value 25 is a test fixture chosen to demonstrate the guard; it is not a quota supplied by the assignment. The 773 accepted and 227 rejected rows are the actual deterministic output of this separate predicate test. This extension is not included in the base scheduler timing series.')

# TASK 9
task_title(doc,9,'Record Experimental Performance',3)
h2(doc,'10.1 Metric definitions')
add_text(doc,'Throughput is completed deliveries divided by elapsed time from the first generated arrival to the final completion. Response time is completion time minus arrival time and therefore includes all waiting and retries. Mean is the arithmetic mean; p95 uses the nearest-rank method (sorted position ceil(0.95*n)). For strict 2PL, admission queueing is measured before a transaction enters the lock scheduler and lock waiting is measured after admission until both requested pool locks can be granted. The timestamp model has no lock wait queue; its extra work is counted as abort/retry attempts.')
h2(doc,'10.2 Performance results - uniform request distribution')
for dist,title in [('uniform','Uniform access'),('skew81','81% hot-canal access')]:
    h2(doc,f'10.2.{1 if dist=="uniform" else 2} {title}')
    rr=[r for r in CSV if r['distribution']==dist]
    rows=[]
    for r in sorted(rr,key=lambda x:(int(x['transactions']), ['Global serial execution','Conservative strict 2PL (cap 16)','Strict timestamp ordering (commit-atomic validation)'].index(x['strategy']))):
        st={'Global serial execution':'Global serial','Conservative strict 2PL (cap 16)':'Strict 2PL','Strict timestamp ordering (commit-atomic validation)':'Strict TO'}[r['strategy']]
        rows.append((r['transactions'],st,fmt(r['throughput_per_second']),fmt(r['mean_response_ms']),fmt(r['p95_response_ms']),r['abort_attempts']))
    table(doc,['N','STRATEGY','THROUGHPUT/s','MEAN ms','p95 ms','RETRIES'],rows,[.45,1.25,1.05,1.0,.9,.75],fontsize=7.6)
    if dist=='uniform':
        add_text(doc,'Under uniform requests, 2PL maintains low response times because most transactions use independent pools. Strict TO has more aborts as the burst grows because timestamped attempts can arrive at validation in an order that differs from their start order. Global serial execution is limited by the single 20 ms server.')
    else:
        add_text(doc,'Under skew81, the dominant source row becomes the bottleneck for strict 2PL. The mean and p95 response times rise sharply as transactions wait for that pool. Strict TO avoids lock waiting in this model but pays for stale attempts with retries. The TO throughput is not a production guarantee because its atomic commit application is modelled as zero-duration.')
figure(doc,D/'throughput_by_burst.png','Figure 6. Throughput by burst size and access distribution.',6.1)
figure(doc,D/'p95_latency_by_burst.png','Figure 7. Nearest-rank p95 response time by burst size and access distribution.',6.1)
h2(doc,'10.3 Detailed 1,000-request measurements')
rows=[]
for dist in ('uniform','skew81'):
  for r in RESULT['experiments'][f'1000_{dist}']['summary']:
    rows.append((dist,r['strategy'].replace(' (commit-atomic validation)','').replace(' (cap 16)',''),fmt(r['throughput_per_second']),fmt(r['mean_response_ms']),fmt(r['p95_response_ms']),r['abort_attempts'],r['wait_for_cycles']))
table(doc,['ACCESS','STRATEGY','TP/s','MEAN ms','p95 ms','ABORTS','CYCLES'],rows,[.7,1.7,.65,.75,.75,.65,.6],fontsize=7.4)
add_text(doc,'The generated strict 2PL cases have zero wait-for cycles because the model acquires the full lock set before execution. The explicit dynamic-2PL deadlock fixture in Task 5 detects one cycle and resolves it by aborting the younger transaction. The timestamp strategy has no lock wait-for cycles, but it can restart stale transactions.')
h2(doc,'10.4 Admission queue versus lock blocking')
ac=RESULT['extras']['admission_comparison_skewed_1000']
ac_rows=[]
for cap in (4,8,16,32):
    r=ac[str(cap)]
    ac_rows.append((cap,fmt(r['throughput_per_second']),fmt(r['mean_admission_wait_ms']),fmt(r['mean_lock_wait_ms']),fmt(r['mean_response_ms']),fmt(r['p95_response_ms'])))
table(doc,['ADMISSION CAP','TP/s','MEAN ADMISSION ms','MEAN LOCK ms','MEAN RESPONSE ms','p95 ms'],ac_rows,[1.0,.7,1.15,1.0,1.1,.8],fontsize=7.4)
figure(doc,D/'admission_queue_tradeoff.png','Figure 8. A smaller admission cap shifts time from lock waiting into admission waiting; throughput changes only slightly in this fixture.',6.0)
add_text(doc,'For the 1,000-request skewed strict-2PL run, reducing the admission cap from 32 to 4 changes mean admission wait from 1,742.8 ms to 2,232.5 ms, while mean lock wait falls from 491.3 ms to 49.2 ms. Throughput changes only slightly, from 57.54/s at cap 4 to 58.96/s at caps 16 and 32. Bounded admission therefore shapes and limits the number of in-flight waiters; it does not increase the service capacity of the dominant canal pool.')
h2(doc,'10.5 Replay, undo and restart work')
add_text(doc,'The crash fixture generated four winner update redo actions and three loser update undo actions for immediate update. With deferred update, it generated four winner redo actions and zero loser page undo actions. The restart figures 29.21 seconds at 285 seconds and 24.93 seconds at 240 seconds are analytical estimates from the declared rates in Task 7, not timed process restarts.')

# TASK 10
task_title(doc,10,'Compare Theory with Experimental Behaviour',4)
h2(doc,'11.1 Predicted and observed growth')
table(doc,['STRATEGY','THEORETICAL EXPECTATION','OBSERVED MODEL PATTERN'],[
('Global serial','At most one transaction uses the server; queue grows when offered arrival rate exceeds service rate.','50 deliveries/s under a 20 ms server; mean and p95 increase with burst size.'),
('Conservative strict 2PL','Disjoint transactions may overlap; same-row X-lock conflicts wait; a hot row serializes its writers.','Uniform workload stays near 67/s; skew81 reduces throughput and creates a large lock queue.'),
('Strict timestamp order','No lock wait-for cycle; conflicting stale operations abort and retry; independent work can overlap.','No lock cycles; retries rise under large bursts and skew; model p95 remains lower because validation is atomic and short.')],[1.25,2.75,2.65],fontsize=7.8)
h2(doc,'11.2 Why the hot canal changes the answer')
add_text(doc,'The design challenge directs 81% of requests to one canal. At the 67/s planning arrival rate, this is 0.81 x 67 = 54.27 requests per second for the dominant pool. Under the modelled 20 ms exclusive-lock interval, one pool can complete at most about 1/0.020 = 50 such movements per second. The offered hot-pool rate is therefore about 4.27/s above that modelled service capacity. The queue grows until arrivals stop or the design changes the work per hot row.')
h2(doc,'11.3 Differences from a real DBMS')
bullet(doc,'The Python model has no buffer pool, disk flush latency, network latency, replication, CPU contention, log device queue or commercial lock-manager implementation.')
bullet(doc,'A real timestamp-ordering commit includes validation and durable log work. The simulator’s commit event is atomic and zero-duration; the TO throughput must not be projected directly into production.')
bullet(doc,'Node and page occupancy are not relevant to this transaction-level simulation; log scan and redo rates are stated assumptions in the separate recovery model.')
bullet(doc,'The exact number of retries depends on timestamp assignment, execution jitter and the chosen retry policy. The seed and jitter range make this experiment reproducible rather than universal.')
add_text(doc,'The experiment supports the qualitative claims: global serialization makes unrelated work wait; strict 2PL creates waiting on the hot canal row; timestamp validation trades lock waiting for restart work. It does not prove that a timestamp-ordered commercial DBMS will be faster than a lock-based one.')

# TASK 11
task_title(doc,11,'Recommend and Defend the Final Strategy',4)
h2(doc,'12.1 Baseline recommendation before the changed requirement')
add_text(doc,'For the original RiverGate workload, recommend conservative strict 2PL for token movements. The application knows the complete source/destination lock set before execution; acquiring all X locks before reading avoids partial-lock deadlocks; retaining X locks to commit gives strictness; and one transaction contains the source debit, destination credit and unique request outcome. Reports use a consistent snapshot. Compared with global serialization, the design preserves concurrency for disjoint pools. Compared with timestamp ordering, it avoids repeated restart work in the uniform test.')
h2(doc,'12.2 Correctness evidence')
bullet(doc,'The token movement is one atomic transaction, so a failed debit cannot leave a destination credit or source-only debit committed.')
bullet(doc,'Conservative lock acquisition obtains both source/destination X locks before reads; strict retention prevents dirty reads and dirty writes on those rows.')
bullet(doc,'The serial schedule is the correctness reference. The precedence-graph examples show how lost credit and mixed report totals create cycles when no control is used.')
bullet(doc,'The simulator verifies 24/24 candidate/workload combinations for all generated transactions completed, token total conserved and non-negative pool balances.')
bullet(doc,'Idempotency is enforced by a unique DeliveryID; a repeated request returns REPLAY_IGNORED in the boundary test and does not move tokens again.')
h2(doc,'12.3 Performance evidence and limitations')
add_text(doc,'At 1,000 uniform requests, the simulator reports 66.98 deliveries/s, mean response 20.66 ms and p95 25.07 ms for conservative strict 2PL, with zero abort attempts and zero generated wait-for cycles. The global serial baseline is 50.00/s with p95 4,835.82 ms. Under skew81, however, strict 2PL falls to 58.96/s with p95 3,917.31 ms. This limitation is the reason Task 12 reopens the design.')
h2(doc,'12.4 Recovery policy')
add_text(doc,'Use WAL with commit-force, strict X-lock retention and a quiescent clean checkpoint. The original 285-second checkpoint interval estimates to 29.21 seconds, below the 35-second target but with limited margin. A 240-second interval estimates to 24.93 seconds under the declared log and replay assumptions. The 240-second interval is selected for the revised plan, subject to measurement on the target platform.')

# TASK 12
task_title(doc,12,'Re-evaluate and Adapt the Design',8)
h2(doc,'13.1 A. Impact analysis (2 marks)')
add_text(doc,'The changed case introduces three linked changes: 81% of allocation requests target one canal; each farm has a daily ceiling; and restart has a 35-second maximum. The earlier uniform-access assumption no longer describes contention. The dominant source pool is now a hot item. The earlier token-only transaction is also incomplete because an allocation that is within the canal’s remaining balance may still exceed the particular farm’s daily allowance.')
add_text(doc,'At 67 requests/s, the dominant canal receives about 54.27 requests/s. With a 20 ms full-lock transaction interval, the modelled per-row lock capacity is 50/s. The skewed 1,000-request simulation shows a strict-2PL p95 of 3,917.31 ms. This is not a production throughput prediction, but it demonstrates the structural bottleneck: every transaction touching the dominant canal must serialize at that row.')
add_text(doc,'The restart deadline is independent of the in-memory queue: it depends on log tail size, scan throughput, redo and undo work. With the stated assumptions, the original 285-second checkpoint interval estimates to 29.21 seconds, so it passes but leaves only 5.79 seconds of margin. A shorter checkpoint interval reduces the recovery tail.')
h2(doc,'13.2 B. Evaluate the original design (2 marks)')
add_text(doc,'The original conservative strict-2PL candidate remains correct but is no longer satisfactory as the only throughput plan under the 81% concentration. It completes all requests and preserves all tokens in the model, but its lock queue is severe. Bounded admission does not remove the hot-row service limit; it moves some waiting from the lock queue to the admission queue.')
add_text(doc,'The admission comparison for 1,000 skewed requests shows throughput changes only slightly, from 57.54/s at cap 4 to 58.96/s at caps 16 and 32. A cap of 4 lowers mean lock wait to 49.2 ms but raises admission wait to 2,232.5 ms. A cap of 32 has mean lock wait 491.3 ms and admission wait 1,742.8 ms. This is a queue-location trade-off, not a capacity improvement. The daily farm ceiling cannot be guaranteed by canal locking alone; the farm/day predicate must be checked and updated in the same transaction.')
h2(doc,'13.3 C. Adaptation or redesign (2 marks)')
add_text(doc,'Modify the original plan to use strict commit-atomic timestamp ordering for the quota movement write set under the concentrated workload, with a bounded admission front end, a per-farm/day guard record, idempotent DeliveryIDs and the shorter 240-second clean-checkpoint interval. The token movement remains one atomic unit. The timestamp validator checks every item in the read/write set before publishing both pool changes and the farm usage increment. Any stale attempt rolls back its staged work and retries with a new timestamp. No update becomes visible before commit.')
code(doc,'REVISED MOVE-AND-CHECK(DeliveryID, CanalID, FarmID, Date, q):\n  bounded admission queue (cap chosen by operations; initial test candidate = 8)\n  assign TS; stage read set {CanalPool, FarmPool, FarmDailyUsage}\n  validate TS >= W-TS for each read item\n  validate TS >= R-TS and W-TS for each write item\n  validate q > 0 and CanalPool.remaining >= q\n  validate FarmDailyUsage.used + q <= FarmDailyUsage.ceiling\n  if any test fails: discard all staged writes; assign new TS; retry / return controlled busy\n  atomically commit: canal -= q; farm += q; farm/day used += q; record DeliveryID\n  force COMMIT record before acknowledging success')
add_text(doc,'The base timestamp scheduler and retry counts are measured. The per-farm/day guard is a separate tested predicate fixture (773 accepted, 227 rejected for the test-only ceiling of 25); the combined farm-guard plus timestamp design is a proposed integration and has not been benchmarked as a production system. The cap-8 option is a bounded-admission proposal informed by the measured cap sweep, not a claim that cap 8 increases throughput.')
h2(doc,'13.4 D. Evidence-based defence (2 marks)')
table(doc,['EVIDENCE','BASE strict 2PL UNDER SKEW81','STRICT TO UNDER SKEW81','INTERPRETATION'],[
('Throughput at 1,000','58.96/s','66.80/s','TO model meets the 67/s offered rate more closely.'),
('Mean response','2,255.66 ms','63.02 ms','TO trades retries for less lock waiting in this simulation.'),
('p95 response','3,917.31 ms','80.52 ms','The modelled tail is much smaller for TO.'),
('Abort / retry attempts','0','1,015','TO has substantial restart work; idempotency and retry control are essential.'),
('Wait-for cycles','0','0','Conservative all-lock acquisition avoids partial-lock cycles; TO has no lock wait graph.'),
('Checkpoint restart estimate','29.21 s at 285 s','24.93 s at 240 s','Both are modelled; 240 s provides more margin.')],[1.35,1.45,1.35,2.15],fontsize=7.4)
add_text(doc,'The final decision is a modification, not a claim that timestamp ordering is universally superior. It follows from the test conditions: exact 81% hot-canal demand, the assignment’s 67/s planning rate, the 20 ms modelled service interval and a measured high 2PL tail. The strict TO model improves throughput and response by allowing overlap before commit, but it causes about one restart per request in the 1,000 skewed run. An operational rollout must load-test durable commit cost, retry storms and the farm/day guard together before replacing the baseline scheduler.')
add_text(doc,'For the recovery target, the retained log volume under the model at 285 seconds is 67 x 285 x 176 = 3,360,720 bytes, with 38,190 update records to redo. At 240 seconds it is 2,830,080 bytes and 32,160 update records. The formula gives 29.21 seconds and 24.93 seconds respectively. The added farm guard costs an extra read/validation/write of one FARM_DAILY_USAGE row and increases the transaction write set; it also serializes requests for the same farm/day row. That cost is required to enforce the newly stated rule. The daily ceiling test demonstrates why the original two-pool token model alone is insufficient.')

# conclusion and references
h1(doc,'14. CONCLUSION')
add_text(doc,'RiverGate’s core correctness requirement is that a water-token movement must debit the source, credit the destination and record the delivery as one atomic and durable event. Global serial execution is the simple reference. Conservative strict 2PL is the baseline recommendation when access is dispersed and the complete lock set is known. The changed 81% hot-canal workload creates a bottleneck for a long-held exclusive lock, and the experiment shows a substantial lock-wait tail. The revised proposal uses strict commit-atomic timestamp validation with retries, an explicit farm/day ceiling guard, bounded admission and a 240-second checkpoint interval. The measured results are controlled Python simulations and analytical restart estimates, not production measurements; the final implementation must be benchmarked on the target DBMS and hardware.')
h1(doc,'REFERENCES')
for ref in [
'Silberschatz, A., Korth, H. F., and Sudarshan, S. Database System Concepts. McGraw-Hill. Topics: transaction management, serializability, locking, timestamp ordering and recovery.',
'Elmasri, R. and Navathe, S. B. Fundamentals of Database Systems. Pearson. Topics: transaction processing, schedules, concurrency control and database recovery.',
'Ramakrishnan, R. and Gehrke, J. Database Management Systems. McGraw-Hill. Topics: concurrency control, logging, checkpoints and recovery.'
]: bullet(doc,ref)

# Appendix A - reproducibility and evidence map
doc.add_page_break()
h1(doc,'APPENDIX A - REPRODUCIBILITY AND EVIDENCE MAP')
add_text(doc,'This appendix maps the report’s claims to the files supplied in the CO5 repository package. The original assignment brief is included so that the work can be checked against the exact RiverGate requirements.')
table(doc,['ARTIFACT','REPOSITORY LOCATION','PURPOSE / EVIDENCE'],[
('Original assignment','Source/CSA05_Assignment_CO5.docx','The seven-page CO5 brief used as the task and scenario source.'),
('Concurrency and recovery simulator','Python_Scripts/run_simulation.py','Seeded workload generator, serial / conservative strict-2PL / strict-TO simulations, schedule fixtures, crash trace, boundary tests and separate farm/day predicate test.'),
('Diagram and chart generator','Python_Scripts/create_figures.py','Produces concurrency, precedence-graph and recovery figures, plus throughput, p95 and admission-wait charts.'),
('Report generator','Python_Scripts/build_report.py','Rebuilds the editable report from the stored simulation outputs and figures.'),
('Structured measurements','outputs/simulation_results.json; outputs/performance_results.csv','Raw deterministic experiment summaries for all burst sizes and access distributions.'),
('Execution logs','Execution_Evidence/Text_Logs/','Console output, schedule/deadlock fixtures, immediate/deferred recovery trace and boundary/domain tests.'),
('Output capture','Execution_Evidence/Output_Captures/01_simulation_output.png','Rendered image of the saved stdout log; it is not represented as a screenshot of a live desktop terminal.')],[1.3,2.15,3.15],fontsize=7.6)
h2(doc,'A.1 Reproduction commands')
code(doc, 'cd CO5\npython Python_Scripts/run_simulation.py --sizes 10,50,200,1000\npython Python_Scripts/create_figures.py\npython Python_Scripts/build_report.py')
add_text(doc,'The simulation uses seed 5505 and evaluates three controlled candidates at four burst sizes under two access distributions: 4 x 2 x 3 = 24 experiment combinations. All 24 combinations passed the recorded checks for full completion, conserved token total, matching report total and non-negative pool balances. Boundary tests also verify an empty ledger, one committed movement, duplicate replay suppression and deletion of the final idempotency key.')
h2(doc,'A.2 Evidence boundaries')
bullet(doc,'The test-only farm/day ceiling is 25 tokens per farm per day; it is a fixture value, not a quota specified by the assignment. That independent test accepts 773 and rejects 227 of 1,000 generated requests. The integrated farm guard plus timestamp scheduler is proposed, not jointly benchmarked.')
bullet(doc,'The model assumes a 20 ms transaction attempt, deterministic seed and bounded jitter. It does not include disk flush, network, replication, buffer-pool, CPU or commercial DBMS overhead.')
bullet(doc,'Restart values are calculated from declared log scan, redo, undo and fixed-time assumptions. They are modelled estimates, not timed crash/restart measurements.')
bullet(doc,'No MySQL, Oracle or production database execution is claimed. The actual data supplied are Python simulation output, deterministic fixtures and mathematical estimates.')

# Core properties
for p in doc.paragraphs:
    if p.style.name.startswith('Heading'):
        p.paragraph_format.keep_with_next=True
# Set document properties
props=doc.core_properties; props.title='DBMS Assignment 5 - CO5: Concurrency and Recovery for Irrigation Water Quota Allocation'
props.subject='RiverGate Cooperative concurrency control, serializability and restart recovery'
props.author='M. Richard'; props.keywords='CSA05, DBMS, CO5, concurrency control, recovery'

out=OUT/'M_Richard_DBMS_Assignment5_CO5_FINAL.docx'
doc.save(out)
print(out)
