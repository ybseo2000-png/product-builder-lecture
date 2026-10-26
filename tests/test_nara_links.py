import unittest
from scripts.collect_nara_links import split_notice,parse_response,match_link,collect,AuthError,LinkError

NUMBER='R26BK01776995'
URL=f'https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo={NUMBER}&bidPbancOrd=000'
def response(rows):return {'response':{'header':{'resultCode':'00','resultMsg':'정상'},'body':{'totalCount':len(rows),'items':rows}}}
def item(order='000',url=URL):return {'bidNtceNo':NUMBER,'bidNtceOrd':order,'bidNtceDtlUrl':url}
class LinkTests(unittest.TestCase):
 def test_split_new_and_legacy_numbers(self):
  self.assertEqual(split_notice(NUMBER+'-000'),(NUMBER,'000'))
  self.assertEqual(split_notice('20220238607-001'),('20220238607','001'))
 def test_example_response_and_matching(self):
  total,rows=parse_response(response([item()]));self.assertEqual(total,1);self.assertEqual(match_link(rows,NUMBER,'000'),{'status':'ok','url':URL})
 def test_wrong_order_not_linked(self):
  self.assertEqual(match_link([item()],NUMBER,'001')['status'],'not_found')
 def test_missing_url_distinct(self):
  self.assertEqual(match_link([item(url='')],NUMBER,'000')['status'],'no_url')
 def test_unsafe_or_mismatching_url_rejected(self):
  for url in ['javascript:alert(1)','https://example.com/',URL.replace('bidPbancOrd=000','bidPbancOrd=001')]:
   with self.assertRaises(LinkError):match_link([item(url=url)],NUMBER,'000')
 def test_auth_error_and_empty_response(self):
  self.assertEqual(parse_response(response([])),(0,[]))
  with self.assertRaises(AuthError):parse_response({'response':{'header':{'resultCode':'30'},'body':{}}})
 def test_fetch_base_once_for_multiple_orders_and_cache_success(self):
  data={'items':[{'id':NUMBER+'-000'},{'id':NUMBER+'-001'}]};calls=[]
  def fetch(key,number,page):
   calls.append((number,page));return response([item(),item('001',URL.replace('Ord=000','Ord=001'))])
  result=collect(data,'fixture',fetch=fetch,pause=lambda _:None)
  self.assertEqual(calls,[(NUMBER,1)]);self.assertEqual(result['counts']['ok'],2)
  def nofetch(*_):raise AssertionError('successful results should be reused')
  second=collect(data,'fixture',previous=result,fetch=nofetch,pause=lambda _:None)
  self.assertEqual(second['counts']['ok'],2)
