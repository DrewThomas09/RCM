"""Re-parse v2.7 chart XML with full fidelity -> v27_charts2.json.

The first parse dropped every category reference and several series names;
this one keeps cat/name refs, axis titles, number formats, smooth flags and
grouping so the rebuild can be faithful.
"""
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET

SCRATCH = os.path.dirname(os.path.abspath(__file__))
V27 = '/root/.claude/uploads/3de345a1-c58f-5ce6-b747-7cbb0636d5d9/bec059da-IFT_Sourced_Evidence_Master_v2_7.xlsx'
if not os.path.exists(V27):
    V27 = '/home/user/RCM/RCM_MC/rcm_mc/market_reports/reference/IFT_Sourced_Evidence_Master_v2_7.xlsx'

C = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
XDR = 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'
X = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


def q(ns, tag):
    return f'{{{ns}}}{tag}'


def text_of(el):
    if el is None:
        return None
    return ''.join(t.text or '' for t in el.iter(q(A, 't'))) or None


def ref_of(parent, *path):
    node = parent
    for p in path:
        if node is None:
            return None
        node = node.find(q(C, p))
    if node is None:
        return None
    f = node.find(f'.//{q(C, "f")}')
    return f.text if f is not None else None


def parse_axis(ax):
    return {
        'axId': ax.find(q(C, 'axId')).get('val'),
        'title': text_of(ax.find(q(C, 'title'))),
        'numFmt': (ax.find(q(C, 'numFmt')).get('formatCode')
                   if ax.find(q(C, 'numFmt')) is not None else None),
        'pos': (ax.find(q(C, 'axPos')).get('val')
                if ax.find(q(C, 'axPos')) is not None else None),
    }


def _resolve(base_dir, target):
    if target.startswith('/'):
        return target.lstrip('/')
    return os.path.normpath(os.path.join(base_dir, target)).replace('\\', '/')


def main():
    z = zipfile.ZipFile(V27)
    # sheet name <- drawing <- chart mapping
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rid2t = {r.get('Id'): r.get('Target') for r in rels}
    chart2sheet = {}
    chart2anchor = {}
    for sh in wb.find(q(X, 'sheets')):
        t = rid2t[sh.get(q(R, 'id'))]
        spath = t.lstrip('/') if t.startswith('/') else 'xl/' + t
        relp = os.path.dirname(spath) + '/_rels/' + os.path.basename(spath) + '.rels'
        if relp not in z.namelist():
            continue
        dpath = None
        for r in ET.fromstring(z.read(relp)):
            if r.get('Type').endswith('/drawing'):
                dpath = _resolve(os.path.dirname(spath), r.get('Target'))
        if not dpath or dpath not in z.namelist():
            continue
        drelp = os.path.dirname(dpath) + '/_rels/' + os.path.basename(dpath) + '.rels'
        rid2chart = {}
        if drelp in z.namelist():
            for r in ET.fromstring(z.read(drelp)):
                if r.get('Type').endswith('/chart'):
                    rid2chart[r.get('Id')] = _resolve(os.path.dirname(dpath), r.get('Target'))
        for anch in ET.fromstring(z.read(dpath)):
            gf = anch.find(f'.//{q(XDR, "graphicFrame")}')
            if gf is None:
                continue
            cref = gf.find(f'.//{q(C, "chart")}')
            if cref is None:
                continue
            cpath = rid2chart.get(cref.get(q(R, 'id')))
            if not cpath:
                continue
            chart2sheet[cpath] = sh.get('name')
            frm = anch.find(q(XDR, 'from'))
            to = anch.find(q(XDR, 'to'))
            def cr(el):
                return (int(el.find(q(XDR, 'col')).text), int(el.find(q(XDR, 'row')).text))
            if frm is not None and to is not None:
                chart2anchor[cpath] = {'from': cr(frm), 'to': cr(to)}
            elif frm is not None:
                ext = anch.find(q(XDR, 'ext'))
                cx = int(ext.get('cx')) if ext is not None else 5486400
                cy = int(ext.get('cy')) if ext is not None else 3200400
                fc, fr = cr(frm)
                chart2anchor[cpath] = {'from': (fc, fr),
                                       'to': (fc + round(cx / 585216), fr + round(cy / 190500))}

    specs = []
    for cpath in sorted(chart2sheet, key=lambda p: int(re.search(r'(\d+)', p).group())):
        root = ET.fromstring(z.read(cpath))
        plot = root.find(f'.//{q(C, "plotArea")}')
        spec = {
            'file': cpath.replace('xl/charts/', 'xl/charts/'),
            'sheet': chart2sheet[cpath],
            'anchor': chart2anchor.get(cpath),
            'title': text_of(root.find(f'.//{q(C, "title")}')),
            'plots': [],
            'axes': [],
        }
        for tag in ('catAx', 'valAx', 'dateAx'):
            for ax in plot.findall(q(C, tag)):
                d = parse_axis(ax)
                d['kind'] = tag
                spec['axes'].append(d)
        for tag in ('lineChart', 'barChart', 'areaChart', 'scatterChart', 'pieChart'):
            for p in plot.findall(q(C, tag)):
                pd = {
                    'type': tag,
                    'grouping': (p.find(q(C, 'grouping')).get('val')
                                 if p.find(q(C, 'grouping')) is not None else None),
                    'barDir': (p.find(q(C, 'barDir')).get('val')
                               if p.find(q(C, 'barDir')) is not None else None),
                    'axIds': [a.get('val') for a in p.findall(q(C, 'axId'))],
                    'series': [],
                }
                for ser in p.findall(q(C, 'ser')):
                    tx = ser.find(q(C, 'tx'))
                    name_ref = ref_of(ser, 'tx', 'strRef') if tx is not None else None
                    name_ref = name_ref or (ref_of(ser, 'tx') if tx is not None else None)
                    name_lit = None
                    if tx is not None and name_ref is None:
                        v = tx.find(f'.//{q(C, "v")}')
                        name_lit = v.text if v is not None else None
                    sm = ser.find(q(C, 'smooth'))
                    pd['series'].append({
                        'name_ref': name_ref,
                        'name': name_lit,
                        'cat': ref_of(ser, 'cat', 'numRef') or ref_of(ser, 'cat', 'strRef'),
                        'val': ref_of(ser, 'val', 'numRef'),
                        'x': ref_of(ser, 'xVal', 'numRef'),
                        'y': ref_of(ser, 'yVal', 'numRef'),
                        'smooth': sm.get('val') if sm is not None else None,
                    })
                spec['plots'].append(pd)
        specs.append(spec)

    out = os.path.join(SCRATCH, 'v27_charts2.json')
    json.dump(specs, open(out, 'w'), indent=1)
    n_ser = sum(len(p['series']) for s in specs for p in s['plots'])
    n_cat = sum(1 for s in specs for p in s['plots'] for x in p['series'] if x['cat'])
    n_named = sum(1 for s in specs for p in s['plots'] for x in p['series']
                  if x['name_ref'] or x['name'])
    n_combo = sum(1 for s in specs if len(s['plots']) > 1)
    print(f'{len(specs)} charts, {n_ser} series, cat={n_cat}, named={n_named}, '
          f'combos={n_combo} -> {out}')


if __name__ == '__main__':
    main()
