"""v3.4 NPPES resolution: ambulance market participants -> organizational NPIs.

Resolves two groups of names against the public NPPES NPI Registry API v2.1
(https://npiregistry.cms.hhs.gov/api/):

  named_participant  explicit participant list (Modivcare carried as a
                     NEMT-adjacent boundary reference, not a ground comparator)
  registry           operator names from v34_seed.json 'registry_names';
                     grouped labels are split into constituent searchable
                     names, non-operator rows are skipped, and geographically
                     scoped constituents (Omaha locals, NE/IA fire) carry a
                     state filter recorded in the entry's params.

Each query = organization_name={name}* / enumeration_type=NPI-2 / limit=200,
address_purpose omitted. Per hit we keep NPI, org name, other names, taxonomy
codes+descriptions (flagging ground-ambulance 341600000X and 3416* subcodes),
practice-location city/state/ZIP, and enumeration date. Match confidence per
hit: EXACT (normalized, corporate-suffix-stripped equality), PREFIX (result
starts with query at a word boundary), FUZZY (query tokens are a subset of
result tokens), else OTHER (e.g. matched via an Other Name). Zero hits is a
recorded result. Name->NPI registry lookup only; public data.

Artifacts: cache key 'nppes_participant_resolution' (list of entries) plus a
flat crosswalk SCRATCH/nppes_crosswalk.json for downstream builders.
"""
import json
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull import CACHE, SCRATCH, get, load_manifest, log, record  # noqa: E402

NPPES_API = 'https://npiregistry.cms.hhs.gov/api/'
SLEEP = 0.3          # ~0.3s between API calls
TRIES = 4            # 1 attempt + 3 retries with exponential backoff (pull.get)
LIMIT = 200
CROSSWALK = os.path.join(SCRATCH, 'nppes_crosswalk.json')

NAMED_PARTICIPANTS = [
    'Royal Ambulance', 'Priority Ambulance', 'American Medical Response',
    'Global Medical Response', 'MedSpeed', 'Meditransport', 'Medadvance',
    'NORCAL Ambulance', 'Advantage Ambulance', 'Century Ambulance',
    'American Ambulance', 'AdventHealth EMS', 'Superior Air-Ground Ambulance',
    'Acadian Ambulance', 'Falck', 'PatientCare EMS', 'DocGo', 'Ambulnz',
    'Modivcare',
]

NAME_NOTES = {
    'Modivcare': 'NEMT-adjacent boundary reference (scope marker, not a '
                 'ground-ambulance comparator)',
}

CORP_SUFFIX = {'INC', 'LLC', 'CORP', 'CORPORATION', 'INCORPORATED', 'CO',
               'COMPANY', 'LTD', 'LP', 'LLP', 'PLLC', 'PC'}
CONF_RANK = {'EXACT': 3, 'PREFIX': 2, 'FUZZY': 1, 'OTHER': 0}


def norm_name(s):
    s = (s or '').upper().replace('&', ' AND ')
    s = re.sub(r'[^A-Z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def strip_suffix(n):
    toks = n.split()
    while toks and toks[-1] in CORP_SUFFIX:
        toks.pop()
    return ' '.join(toks)


def classify(query, names):
    """Best confidence of query vs any of the org's names."""
    nq = norm_name(query)
    nqs = strip_suffix(nq)
    qtok = set(nq.split())
    best = 'OTHER'
    for nm in names:
        nn = norm_name(nm)
        if strip_suffix(nn) == nqs:
            return 'EXACT'
        if nn == nq or nn.startswith(nq + ' '):
            c = 'PREFIX'
        elif qtok and qtok <= set(nn.split()):
            c = 'FUZZY'
        else:
            c = 'OTHER'
        if CONF_RANK[c] > CONF_RANK[best]:
            best = c
    return best


def expand_registry_label(label):
    """Registry label -> list of (query, extra_params, note, searchable).

    Returns None for non-operator rows (category/total/caveat/recipe rows).
    Grouped labels are split into constituent searchable names; Omaha locals
    and NE/IA fire constituents carry a state filter (recorded in params).
    """
    ne = {'state': 'NE'}
    if label.startswith('American Medical Response'):
        return [('American Medical Response', None, None, True)]
    if label.startswith('AmeriPro Health'):
        return [('AmeriPro Health', None, None, True),
                ('Priority Medical Transport', None, None, True)]
    if label.startswith('Omaha private locals'):
        return [(q, dict(ne), None, True) for q in
                ('American Ambulance', 'Eastern', 'Pioneer', 'Papio',
                 'Heartland EMS', '9 Line')]
    if label == 'Siouxland Paramedics':
        return [('Siouxland Paramedics', None, None, True)]
    if label.startswith('Fire-based 911'):
        return [('Omaha Fire Department', dict(ne), None, True),
                ('Lincoln Fire', dict(ne),
                 'covers Lincoln Fire & Rescue / Lincoln Fire and Rescue', True),
                ('Sarpy', dict(ne), 'Sarpy County departments (bare prefix, '
                 'state-scoped)', True),
                ('Council Bluffs Fire', {'state': 'IA'}, None, True)]
    if label.startswith('Hospital-owned (Children'):
        return [("Children's Nebraska", None, None, True),
                ('CHI Health Good Samaritan', None,
                 'label shorthand "CHI Good Samaritan" searched under its '
                 'NPPES-style name', True),
                ('Regional West', dict(ne), None, True),
                ('rural IA hospital squads', None, 'parked: descriptive label, '
                 'not a searchable operator name', False)]
    if label.startswith('Air medical (LifeNet'):
        return [('LifeNet', None, None, True),
                ('Air Methods', None, None, True),
                ('Med-Trans', None, None, True),
                ('EagleMed', None, None, True),
                ('Guardian Flight', None, 'label says "Guardian"; searched as '
                 'the air-medical operator name "Guardian Flight" (bare '
                 '"Guardian" is not resolvable)', True),
                ('Apollo MedFlight', None, None, True)]
    return None


def build_specs():
    specs = [{'query': n, 'group': 'named_participant', 'source_label': n,
              'extra': None, 'note': NAME_NOTES.get(n), 'searchable': True}
             for n in NAMED_PARTICIPANTS]
    seed = json.load(open(os.path.join(SCRATCH, 'v34_seed.json')))
    uniq = list(dict.fromkeys(seed['registry_names']))
    skipped = []
    for label in uniq:
        exp = expand_registry_label(label)
        if exp is None:
            skipped.append(label)
            continue
        for q, extra, note, searchable in exp:
            specs.append({'query': q, 'group': 'registry',
                          'source_label': label, 'extra': extra, 'note': note,
                          'searchable': searchable})
    return specs, skipped


def nppes_search(name, extra=None):
    params = {'version': '2.1', 'enumeration_type': 'NPI-2',
              'organization_name': name + '*', 'limit': str(LIMIT)}
    if extra:
        params.update(extra)
    url = NPPES_API + '?' + urllib.parse.urlencode(params)
    data = json.loads(get(url, tries=TRIES).decode())
    time.sleep(SLEEP)
    if data.get('Errors'):
        raise RuntimeError(f'NPPES error payload: {str(data["Errors"])[:200]}')
    return data, params


def make_hit(query, r):
    basic = r.get('basic') or {}
    org = basic.get('organization_name') or ''
    others = [o.get('organization_name') for o in r.get('other_names') or []
              if o.get('organization_name')]
    tax = [{'code': t.get('code'), 'desc': t.get('desc'),
            'primary': t.get('primary')} for t in r.get('taxonomies') or []]
    amb = any((t['code'] or '').startswith('3416') for t in tax)
    addrs = r.get('addresses') or []
    loc = next((a for a in addrs if a.get('address_purpose') == 'LOCATION'),
               addrs[0] if addrs else {})
    return {'npi': r.get('number'), 'org_name': org, 'other_names': others,
            'confidence': classify(query, [org] + others),
            'taxonomies': tax, 'ambulance_taxonomy': amb,
            'city': loc.get('city'), 'state': loc.get('state'),
            'zip': loc.get('postal_code'),
            'enumeration_date': basic.get('enumeration_date')}


def run_specs(specs):
    entries, api_cache, calls = [], {}, 0
    for sp in specs:
        base = {'query': sp['query'], 'group': sp['group'],
                'source_label': sp['source_label']}
        if sp.get('note'):
            base['note'] = sp['note']
        if not sp['searchable']:
            log(f"PARKED (not searched): {sp['query']!r} — {sp.get('note')}")
            entries.append({**base, 'searched': False, 'params': None,
                            'result_count': 0, 'truncated': False, 'hits': [],
                            'confidence_summary': {},
                            'best_confidence': 'PARKED'})
            continue
        ck = (sp['query'], tuple(sorted((sp['extra'] or {}).items())))
        try:
            if ck in api_cache:
                data, params = api_cache[ck]
            else:
                data, params = nppes_search(sp['query'], sp['extra'])
                api_cache[ck] = (data, params)
                calls += 1
        except Exception as e:  # noqa: BLE001 — park, never stall
            log(f"QUERY FAILED (parked): {sp['query']!r}: "
                f'{type(e).__name__}: {str(e)[:160]}')
            entries.append({**base, 'searched': True,
                            'params': {'organization_name': sp['query'] + '*',
                                       'enumeration_type': 'NPI-2',
                                       'limit': LIMIT,
                                       **(sp['extra'] or {})},
                            'error': f'{type(e).__name__}: {str(e)[:200]}',
                            'result_count': 0, 'truncated': False, 'hits': [],
                            'confidence_summary': {},
                            'best_confidence': 'ERROR'})
            continue
        hits = [make_hit(sp['query'], r) for r in data.get('results') or []]
        summ = {}
        for h in hits:
            summ[h['confidence']] = summ.get(h['confidence'], 0) + 1
        best = (max((h['confidence'] for h in hits),
                    key=lambda c: CONF_RANK[c]) if hits else 'NONE')
        rc = data.get('result_count', len(hits))
        entries.append({**base, 'searched': True,
                        'params': {k: v for k, v in params.items()
                                   if k != 'version'},
                        'result_count': rc, 'truncated': rc >= LIMIT,
                        'hits': hits, 'confidence_summary': summ,
                        'best_confidence': best})
        st = (sp['extra'] or {}).get('state', '')
        log(f"{sp['group']:<17} {sp['query']!r}{' [' + st + ']' if st else ''}: "
            f"{len(hits)} hits, best={best}, "
            f"amb_tax={sum(1 for h in hits if h['ambulance_taxonomy'])}"
            + (' TRUNCATED' if rc >= LIMIT else ''))
    return entries, calls


def crosswalk_key(entry):
    st = (entry.get('params') or {}).get('state')
    return entry['query'] + (f' ({st})' if st else '')


def build_crosswalk(entries):
    xwalk = {}
    for e in entries:
        k = crosswalk_key(e)
        best = e['best_confidence']
        best_npis = [h['npi'] for h in e['hits'] if h['confidence'] == best]
        best_amb = [h['npi'] for h in e['hits']
                    if h['confidence'] == best and h['ambulance_taxonomy']]
        if k in xwalk:  # same query in both groups (identical params/hits)
            g = xwalk[k]['group']
            if e['group'] not in g.split('+'):
                xwalk[k]['group'] = g + '+' + e['group']
            continue
        val = {'group': e['group'], 'best_npis': best_npis,
               'n_hits': len(e['hits']), 'confidence': best,
               'best_ambulance_npis': best_amb,
               'n_ambulance_taxonomy': sum(1 for h in e['hits']
                                           if h['ambulance_taxonomy'])}
        if e.get('note'):
            val['note'] = e['note']
        xwalk[k] = val
    return xwalk


def resolution_meta(entries, api_calls, n_skipped):
    best = [e['best_confidence'] for e in entries]
    hist = {c: best.count(c) for c in
            ('EXACT', 'PREFIX', 'FUZZY', 'OTHER', 'NONE', 'PARKED', 'ERROR')
            if best.count(c)}
    return {
        'dataset': 'NPPES NPI Registry Public Search API v2.1 — '
                   'ambulance market participant name->NPI resolution',
        'endpoint': NPPES_API + '?version=2.1',
        'filters': {'enumeration_type': 'NPI-2',
                    'organization_name': '{name}* (wildcard prefix)',
                    'limit': LIMIT, 'address_purpose': 'omitted',
                    'state': 'only on geographically scoped registry '
                             'constituents (recorded per entry)'},
        'rows': len(entries), 'api_calls': api_calls,
        'names_attempted': sum(1 for e in entries if e['searched']),
        'best_confidence_histogram': hist,
        'truncated_queries': [crosswalk_key(e) for e in entries
                              if e.get('truncated')],
        'skipped_registry_rows': n_skipped,
        'note': 'Public NPPES registry lookup only (name->NPI). '
                'Confidence: EXACT=normalized suffix-stripped equality; '
                'PREFIX=result starts with query at word boundary; '
                'FUZZY=query tokens subset of result tokens; OTHER=e.g. '
                'matched via Other Name. hits=[] is a recorded result. '
                'ambulance_taxonomy flags 341600000X/3416* codes. '
                'Modivcare is a NEMT-adjacent boundary reference.'}


def pull_nppes_resolution(man):
    key = 'nppes_participant_resolution'
    path = os.path.join(CACHE, key + '.json')
    if key in man:
        log(f'{key} already cached; rebuilding crosswalk from cache')
        entries = json.load(open(path))
    elif os.path.exists(path):
        # payload landed but the manifest entry was lost to a concurrent
        # writer (sibling pull holding an older in-memory manifest copy);
        # re-register from the existing payload without re-querying NPPES.
        log(f'{key}: payload exists, manifest entry missing; re-registering')
        entries = json.load(open(path))
        _, skipped = build_specs()
        meta = resolution_meta(entries, 0, len(skipped))
        meta['reregistered_from_cache'] = True
        record(man, key, entries, meta)
    else:
        specs, skipped = build_specs()
        for s in skipped:
            log(f'registry row skipped (non-operator): {s[:90]!r}')
        log(f'{len(specs)} query specs ({len(skipped)} registry rows skipped)')
        entries, calls = run_specs(specs)
        record(man, key, entries, resolution_meta(entries, calls, len(skipped)))
    xwalk = build_crosswalk(entries)
    tmp = CROSSWALK + '.tmp'
    json.dump(xwalk, open(tmp, 'w'), indent=1, sort_keys=True)
    os.replace(tmp, CROSSWALK)
    log(f'crosswalk written: {CROSSWALK} ({len(xwalk)} queries)')


STAGES = [pull_nppes_resolution]

if __name__ == '__main__':
    man = load_manifest()
    only = sys.argv[1:] or None
    for stage in STAGES:
        if only and stage.__name__ not in only:
            continue
        log(f'=== {stage.__name__} ===')
        try:
            stage(man)
        except Exception as e:  # noqa: BLE001
            log(f'STAGE FAILED {stage.__name__}: {type(e).__name__}: {e}')
    log('ALL DONE 11')
