import unittest
from scripts.collect_keywords import extract_keywords, collect

class KeywordTests(unittest.TestCase):
    def test_real_example_structure_and_meta_exclusion(self):
        html = '<meta name="keywords" content="NKIS,검색"><li><em>주제어</em><span>제조업, 경기, 지역, 현황, 전망</span></li>'
        self.assertEqual(extract_keywords(html),{'status':'ok','keywords':['제조업','경기','지역','현황','전망']})

    def test_nested_entities_duplicate_and_spacing(self):
        html='<li><em> 주제어 </em><span><a>지역 관광</a>, 지역 관광;문화 &amp; 여가</span></li>'
        self.assertEqual(extract_keywords(html)['keywords'], ['지역 관광','문화 & 여가'])

    def test_empty_and_missing_are_distinct(self):
        self.assertEqual(extract_keywords('<li><em>주제어</em><span> </span></li>')['status'],'empty')
        self.assertEqual(extract_keywords('<html>로그인 또는 오류 화면</html>')['status'],'missing')

    def test_resume_and_request_limit(self):
        reports=[{'id':str(i),'year':2026,'title':'시험','url':f'https://nkis.re.kr/test/{i}'} for i in range(3)]
        cache={'reports':{}}
        calls=[]
        def fetch(url): calls.append(url);return '<li><em>주제어</em><span>관광</span></li>'
        list(collect(reports,cache,1,1.5,fetch=fetch,pause=lambda _:None))
        list(collect(reports,cache,1,1.5,fetch=fetch,pause=lambda _:None))
        self.assertEqual(len(calls),2)
        self.assertEqual(len(cache['reports']),2)
        self.assertNotEqual(calls[0],calls[1])

    def test_failure_can_retry(self):
        report={'id':'1','year':2026,'title':'시험','url':'https://nkis.re.kr/test'}
        cache={'reports':{}}
        def fail(_): raise RuntimeError('do not print raw responses')
        list(collect([report],cache,1,1.5,fetch=fail,pause=lambda _:None))
        self.assertEqual(cache['reports']['1']['status'],'failed')
        list(collect([report],cache,1,1.5,fetch=lambda _:'<li><em>주제어</em><span>관광</span></li>',pause=lambda _:None))
        self.assertEqual(cache['reports']['1']['status'],'ok')

if __name__=='__main__':unittest.main()
