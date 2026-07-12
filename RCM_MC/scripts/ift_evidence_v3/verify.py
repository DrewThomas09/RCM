import zipfile, re, json
import xml.etree.ElementTree as ET
from collections import Counter
Z=zipfile.ZipFile('IFT_Sourced_Evidence_Master_v3_5.xlsx')
names=set(Z.namelist())
C='{http://schemas.openxmlformats.org/drawingml/2006/chart}'
MAIN='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
ODOC='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
RNS='{http://schemas.openxmlformats.org/package/2006/relationships}'
wb=ET.fromstring(Z.read('xl/workbook.xml'))
sheet_rid={s.get('name'):s.get('{%s}id'%ODOC) for s in wb.iter(MAIN+'sheet')}
wbrels=ET.fromstring(Z.read('xl/_rels/workbook.xml.rels'))
rid_target={r.get('Id'):r.get('Target') for r in wbrels.iter(RNS+'Relationship')}
name_to_file={nm:rid_target[rid].lstrip('/') for nm,rid in sheet_rid.items()}
existing=set(name_to_file)

# self-test empty detector: build nonempty for SP_NE then test empty far cell
col_re=re.compile(r'([A-Z]+)(\d+)')
def col2num(c):
    n=0
    for ch in c: n=n*26+(ord(ch)-64)
    return n
def nonempty(nm):
    f=name_to_file[nm]; s=set()
    root=ET.fromstring(Z.read(f))
    for c in root.iter(MAIN+'c'):
        r=c.get('r')
        v=c.find(MAIN+'v'); ie=c.find(MAIN+'is'); fe=c.find(MAIN+'f')
        has=(v is not None and v.text and v.text.strip()) or (ie is not None and ''.join(ie.itertext()).strip()) or (fe is not None)
        if has and r: s.add(r)
    return s
ne=nonempty('SP_NE')
print('SELF-TEST empty detector:')
print('  SP_NE!B38 in set (formula cell, should be True):', 'B38' in ne)
print('  SP_NE!ZZ9999 in set (should be False):', 'ZZ9999' in ne)
print('  SP_NE nonempty cell count:', len(ne))

num=lambda s:int(re.search(r'\d+',s.split('/')[-1]).group())
allcharts=sorted([n for n in names if re.match(r'xl/charts/chart\d+\.xml$',n)], key=num)

# Rule2 tabulation
r2=Counter(); r3=Counter(); bar_bardir=Counter()
line_smooth_missing=0; line_ser_total=0
for c in allcharts:
    root=ET.fromstring(Z.read(c))
    pa=root.find(C+'chart/'+C+'plotArea')
    bar=pa.find(C+'barChart'); line=pa.find(C+'lineChart')
    catax=pa.find(C+'catAx')
    axpos=catax.find(C+'axPos').get('val') if catax is not None and catax.find(C+'axPos') is not None else None
    de=catax.find(C+'delete') if catax is not None else None
    dev=de.get('val') if de is not None else 'MISSING'
    if bar is not None:
        bd=bar.find(C+'barDir'); bdv=bd.get('val') if bd is not None else '?'
        bar_bardir[bdv]+=1
        r2[('bar',bdv,axpos,dev)]+=1
    if line is not None:
        r2[('line','-',axpos,dev)]+=1
        for ser in line.findall(C+'ser'):
            line_ser_total+=1
            sm=ser.find(C+'smooth')
            smv=sm.get('val') if sm is not None else 'MISSING'
            r3[smv]+=1
            if sm is None: line_smooth_missing+=1
print()
print('Rule2 (plot, barDir, catAx axPos, catAx delete) combos:')
for k,v in sorted(r2.items()): print('  ',k,'->',v)
print('barDir distribution:', dict(bar_bardir))
print()
print('Rule3 line-series smooth val distribution:', dict(r3), ' total line ser:', line_ser_total)
