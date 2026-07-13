"""Merge the psps_mod2 pull manifest (a list) into the cache manifest (a dict),
computing sha256 + file + retrieved_utc so the Pull_Manifest tab renders the new
artifacts exactly like every other cached pull."""
import json, hashlib, os
CACHE='ift_v3_cache'
man=json.load(open(os.path.join(CACHE,'manifest.json')))
add=json.load(open('psps_mod2_manifest.json'))
n=0
for e in add:
    key=e['key']; fn=key+'.json'; path=os.path.join(CACHE,fn)
    sha=hashlib.sha256(open(path,'rb').read()).hexdigest()
    man[key]={'dataset':e['dataset'],'data_year':e['data_year'],
              'endpoint':e['endpoint'],'filters':e.get('filters',{}),
              'pages':e.get('pages'),'rows':e.get('rows'),
              'sha256':sha,'retrieved_utc':e['accessed']+'T00:00:00+00:00',
              'file':fn,'uuid':e['uuid'],'aggregation':e['aggregation']}
    n+=1
json.dump(man,open(os.path.join(CACHE,'manifest.json'),'w'),indent=1)
print(f'merged {n} psps_mod2 manifest entries; manifest now {len(man)} keys')
