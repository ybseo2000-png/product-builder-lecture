import json
from pathlib import Path
from urllib.parse import urlsplit
from collect_prism import FIELDS

def validate(data):
 assert data['status'] in {'pending','ready'} and data['organId']=='1371000'
 assert data['startDate']=='20220101' and data['endDate']=='20270101'
 assert isinstance(data['items'],list)
 if data['status']=='pending':assert not data['items'];return
 assert data['totalCount']==len(data['items'])
 ids=set()
 for row in data['items']:
  assert all(isinstance(row.get(field),str) for field in FIELDS)
  assert row['research_id'].startswith('1371000-') and row['research_id'] not in ids
  ids.add(row['research_id'])
  assert row['detailStatus'] in {'ok','failed'} and isinstance(row['downloads'],list)
  for f in row['downloads']:
   u=urlsplit(f['url']);assert u.scheme in {'http','https'} and u.hostname and not u.username and not u.password
 assert data['detailFailed']==sum(row['detailStatus']=='failed' for row in data['items'])

if __name__=='__main__':
 data=json.loads(Path('data/prism.json').read_text(encoding='utf-8'));validate(data);print('PRISM public data schema OK:',data['status'],len(data['items']))
