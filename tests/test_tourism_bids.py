import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_tourism_bids import months,normalize,collect_month,LinkError
class MonthlyTests(unittest.TestCase):
 def test_calendar(self):
  m=list(months());self.assertEqual(len(m),60)
  self.assertEqual(m[0],('2022-01','202201010000','202201312359'))
  self.assertEqual(m[25][2],'202402292359');self.assertEqual(m[-1][2],'202612312359')
 def test_pages_and_exact_multiple(self):
  calls=[]
  def fetch(key,begin,end,page):
   calls.append(page)
   return 20,[dict(bidNtceNo=str(n),bidNtceOrd='000',bidNtceNm='관광 연구',bidNtceDt='2022-01-05 12:00',ntceInsttNm='시청') for n in range((page-1)*10,page*10)]
  result=collect_month('secret','202201010000','202201312359',fetch,lambda _:None)
  self.assertEqual(calls,[1,2]);self.assertEqual(len(result),20);self.assertEqual(result[0]['agency'],'시청')
 def test_empty(self):
  self.assertEqual(collect_month('k','202201010000','202201312359',lambda *a:(0,[])),[])
 def test_duplicate_rejected(self):
  row=dict(bidNtceNo='1',bidNtceNm='관광',bidNtceDt='2022-01-01')
  with self.assertRaises(LinkError):collect_month('k','202201010000','202201312359',lambda *a:(2,[row,row]))
 def test_wrong_month_rejected(self):
  row=dict(bidNtceNo='1',bidNtceNm='관광',bidNtceDt='2020-01-01')
  with self.assertRaises(LinkError):collect_month('k','202201010000','202201312359',lambda *a:(1,[row]))
if __name__=='__main__':unittest.main()
