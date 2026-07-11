"""Audit every chart in the v3.2 deliverable straight from the OOXML parts.

For each chart: which sheet/anchor it sits on, plot types, series counts,
axis wiring (axId/crossAx/crosses/delete), titles, number formats, size.
Flags likely rendering defects.
"""
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

XLSX = sys.argv[1] if len(sys.argv) > 1 else \
    '/home/user/RCM/RCM_MC/deliverables/IFT_Sourced_Evidence_Master_v3_2.xlsx'

NS = {
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'xdr': 'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
}

PLOTS = ['lineChart', 'barChart', 'pieChart', 'scatterChart', 'areaChart',
         'doughnutChart', 'radarChart', 'bubbleChart']


def sheet_map(z):
    """sheet name -> (sheetN.xml path, drawing path or None)."""
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rid2t = {r.get('Id'): r.get('Target') for r in rels}
    out = {}
    for sh in wb.find('x:sheets', NS):
        rid = sh.get('{%s}id' % NS['r'])
        t = rid2t[rid]
        path = t.lstrip('/') if t.startswith('/') else 'xl/' + t
        out[sh.get('name')] = path
    return out


def _resolve(base_dir, target):
    if target.startswith('/'):
        return target.lstrip('/')
    return os.path.normpath(os.path.join(base_dir, target)).replace('\\', '/')


def drawing_for(z, sheet_path):
    relp = os.path.dirname(sheet_path) + '/_rels/' + os.path.basename(sheet_path) + '.rels'
    if relp not in z.namelist():
        return None
    rels = ET.fromstring(z.read(relp))
    for r in rels:
        if r.get('Type').endswith('/drawing'):
            return _resolve(os.path.dirname(sheet_path), r.get('Target'))
    return None


def charts_in_drawing(z, dpath):
    """yield (anchor_cell, ext_cx_emu, ext_cy_emu, chart_xml_path)."""
    if dpath is None or dpath not in z.namelist():
        return
    relp = os.path.dirname(dpath) + '/_rels/' + os.path.basename(dpath) + '.rels'
    rid2chart = {}
    if relp in z.namelist():
        for r in ET.fromstring(z.read(relp)):
            if r.get('Type').endswith('/chart'):
                rid2chart[r.get('Id')] = _resolve(os.path.dirname(dpath), r.get('Target'))
    root = ET.fromstring(z.read(dpath))
    for anch in root:
        gf = anch.find('.//xdr:graphicFrame', NS)
        if gf is None:
            continue
        cref = gf.find('.//c:chart', NS)
        if cref is None:
            continue
        rid = cref.get('{%s}id' % NS['r'])
        frm = anch.find('xdr:from', NS)
        col = int(frm.find('xdr:col', NS).text) if frm is not None else -1
        row = int(frm.find('xdr:row', NS).text) if frm is not None else -1
        ext = anch.find('xdr:ext', NS)
        cx = int(ext.get('cx')) if ext is not None else 0
        cy = int(ext.get('cy')) if ext is not None else 0
        # oneCellAnchor uses xdr:ext; twoCellAnchor has to/from
        yield (col, row, cx, cy, rid2chart.get(rid))


def audit_chart(z, cpath):
    x = z.read(cpath)
    root = ET.fromstring(x)
    plot = root.find('.//c:plotArea', NS)
    info = {'path': cpath, 'plots': [], 'axes': [], 'title': None}
    t = root.find('.//c:title//a:t', NS)
    info['title'] = t.text if t is not None else None
    ax_by_id = {}
    for ax_tag in ('valAx', 'catAx', 'dateAx'):
        for ax in plot.findall(f'c:{ax_tag}', NS):
            d = {
                'kind': ax_tag,
                'axId': ax.find('c:axId', NS).get('val'),
                'delete': (ax.find('c:delete', NS).get('val')
                           if ax.find('c:delete', NS) is not None else None),
                'crossAx': (ax.find('c:crossAx', NS).get('val')
                            if ax.find('c:crossAx', NS) is not None else None),
                'crosses': (ax.find('c:crosses', NS).get('val')
                            if ax.find('c:crosses', NS) is not None else None),
                'pos': (ax.find('c:axPos', NS).get('val')
                        if ax.find('c:axPos', NS) is not None else None),
                'numFmt': (ax.find('c:numFmt', NS).get('formatCode')
                           if ax.find('c:numFmt', NS) is not None else None),
                'majorGridlines': ax.find('c:majorGridlines', NS) is not None,
                'title': None,
            }
            att = ax.find('.//c:title//a:t', NS)
            d['title'] = att.text if att is not None else None
            info['axes'].append(d)
            ax_by_id[d['axId']] = d
    for ptag in PLOTS:
        for p in plot.findall(f'c:{ptag}', NS):
            sers = p.findall('c:ser', NS)
            axids = [a.get('val') for a in p.findall('c:axId', NS)]
            cats = p.find('.//c:cat', NS)
            pd = {
                'type': ptag,
                'n_series': len(sers),
                'axIds': axids,
                'barDir': (p.find('c:barDir', NS).get('val')
                           if p.find('c:barDir', NS) is not None else None),
                'grouping': (p.find('c:grouping', NS).get('val')
                             if p.find('c:grouping', NS) is not None else None),
                'has_cat': cats is not None,
                'ser_names': [],
                'ser_smooth': [],
                'ser_has_spPr': [],
            }
            for s in sers[:30]:
                tx = s.find('c:tx', NS)
                if tx is not None:
                    v = tx.find('.//c:v', NS)
                    f = tx.find('.//c:f', NS)
                    pd['ser_names'].append(v.text if v is not None
                                           else (f.text if f is not None else None))
                else:
                    pd['ser_names'].append(None)
                sm = s.find('c:smooth', NS)
                pd['ser_smooth'].append(sm.get('val') if sm is not None else 'absent')
                pd['ser_has_spPr'].append(s.find('c:spPr', NS) is not None)
            info['plots'].append(pd)
    legend = root.find('.//c:legend', NS)
    info['legend_pos'] = (legend.find('c:legendPos', NS).get('val')
                          if legend is not None and legend.find('c:legendPos', NS) is not None
                          else ('present-nopos' if legend is not None else None))
    return info, ax_by_id


def main():
    z = zipfile.ZipFile(XLSX)
    smap = sheet_map(z)
    report = []
    flags = {}

    def flag(k, item):
        flags.setdefault(k, []).append(item)

    for sheet, spath in smap.items():
        dpath = drawing_for(z, spath)
        if not dpath:
            continue
        for col, row, cx, cy, cpath in charts_in_drawing(z, dpath):
            if not cpath:
                continue
            info, ax_by_id = audit_chart(z, cpath)
            info['sheet'] = sheet
            info['anchor'] = f'r{row + 1}c{col + 1}'
            info['size_cm'] = (round(cx / 360000, 1), round(cy / 360000, 1))
            report.append(info)
            key = f"{sheet}!{info['anchor']}"

            n_plots = len(info['plots'])
            n_val_ax = sum(1 for a in info['axes'] if a['kind'] == 'valAx')
            if n_plots > 1 or n_val_ax > 1:
                flag('combo_or_secondary', key)
            # axis wiring checks
            ids = {a['axId'] for a in info['axes']}
            for a in info['axes']:
                if a['crossAx'] not in ids:
                    flag('crossAx_dangling', f"{key} ax {a['axId']} -> {a['crossAx']}")
                if a['delete'] in ('1', 'true'):
                    flag('axis_deleted', f"{key} {a['kind']}")
                if a['delete'] is None:
                    flag('axis_delete_absent', f"{key} {a['kind']}")
            for p in info['plots']:
                for axid in p['axIds']:
                    if axid not in ids:
                        flag('plot_axid_dangling', f"{key} {p['type']} -> {axid}")
                if p['n_series'] == 0:
                    flag('zero_series', key)
                if p['n_series'] > 8:
                    flag('too_many_series', f"{key} {p['type']} n={p['n_series']}")
                if None in p['ser_names']:
                    flag('unnamed_series', key)
                if p['type'] == 'lineChart' and 'absent' in p['ser_smooth']:
                    flag('smooth_absent', key)
                if not any(p['ser_has_spPr']):
                    flag('no_series_style', key)
                if not p['has_cat']:
                    flag('no_categories', key)
            if not info['title']:
                flag('no_title', key)
            if info['legend_pos'] is None:
                flag('no_legend', key)
            w, h = info['size_cm']
            if w < 10 or h < 6:
                flag('small', f'{key} {w}x{h}cm')

    print(f'charts: {len(report)}')
    for k in sorted(flags):
        v = flags[k]
        print(f'\n== {k}: {len(v)}')
        for item in v[:12]:
            print('   ', item)
        if len(v) > 12:
            print(f'    ... +{len(v) - 12} more')
    json.dump(report, open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        'chart_audit.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
