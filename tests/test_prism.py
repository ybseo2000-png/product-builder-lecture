import unittest
from scripts.collect_prism import get_list, detail_files, collect, PrismError

def row(i):
 return {'research_id':f'1371000-{i}', 'research_name':f'과제 {i}', 'charge_person_department':'','research_organName':'기관','researcher_name':'수행자','issued_year':'2023'}
def listing(total,page):
 return {'resultCode':'0','organ_id':'1371000','start_date':'20220101','end_date':'20270101','totalCount':total,'research':[row(i) for i in range((page-1)*50,min(page*50,total))]}
class PrismTests(unittest.TestCase):
 def test_exact_multiple_no_extra_page(self):
  calls=[]
  def fetch(key,operation,params):calls.append(params);return listing(100,params['pageNo'])
  items,total=get_list('fixture',fetch,lambda _:None)
  self.assertEqual(total,100);self.assertEqual(len(items),100);self.assertEqual([p['pageNo'] for p in calls],[1,2])
  self.assertTrue(all(p['numOfRows']==50 and p['organ_id']=='1371000' and p['start_date']=='20220101' and p['end_date']=='20270101' for p in calls))
 def test_partial_last_page_and_empty_list(self):
  for total in [0,1,51]:
   items,n=get_list('fixture',lambda k,o,p:listing(total,p['pageNo']),lambda _:None)
   self.assertEqual(len(items),total);self.assertEqual(n,total)
 def test_error_and_duplicate_rejected(self):
  bad=listing(2,1);bad['research']=[row(1),row(1)]
  for payload in [bad,{'resultCode':'1'},dict(listing(1,1),organ_id='1320000')]:
   with self.assertRaises(PrismError):get_list('fixture',lambda *_:payload,lambda _:None)
 def test_multiple_files_and_unsafe_url(self):
  detail={'resultCode':'0','research_id':'1371000-1','reportInfo':{'url':[{'file_url':'https://api.prism.go.kr/one','file_name':'one.pdf'},{'file_url':'https://api.prism.go.kr/two'},{'file_url':'https://api.prism.go.kr/one'}]}}
  self.assertEqual(len(detail_files(detail,'1371000-1')),2)
  detail['reportInfo']['url']=[{'file_url':'javascript:alert(1)'}]
  with self.assertRaises(PrismError):detail_files(detail,'1371000-1')
 def test_missing_file_and_wrong_id(self):
  self.assertEqual(detail_files({'resultCode':'0','research_id':'1371000-1','reportInfo':''},'1371000-1'),[])
  with self.assertRaises(PrismError):detail_files({'resultCode':'0','research_id':'other'},'1371000-1')
 def test_failed_details_retry_and_success_cache(self):
  calls=[]
  def fetch(k,o,p):
   if o=='getResearchList_v3':return listing(2,1)
   calls.append(p['research_id'])
   if p['research_id']=='1371000-0':raise PrismError('fixture failure')
   return {'resultCode':'0','research_id':p['research_id'],'reportInfo':None}
  first=collect('fixture',fetch=fetch,pause=lambda _:None)
  self.assertEqual(first['detailFailed'],1)
  calls.clear();second=collect('fixture',previous=first,fetch=fetch,pause=lambda _:None)
  self.assertEqual(calls,['1371000-0']);self.assertEqual(second['items'][1]['detailStatus'],'ok')
