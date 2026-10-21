"""인공 XML fixture 테스트이며 실제 API 성공을 의미하지 않습니다."""
import unittest
from scripts.collect_nkis import collect, parse_page


def xml(total=1, year='2026', identifier='OTP_TEST'):
    return f'''<root><TOTAL_COUNT>{total}</TOTAL_COUNT><items><item>
    <OTP_ID>{identifier}</OTP_ID><OTP_SEQ>0</OTP_SEQ>
    <OTP_HAN_NM>테스트 보고서</OTP_HAN_NM><PUBAGC>테스트 기관</PUBAGC>
    <PBL_YY>{year}</PBL_YY></item></items></root>'''.encode()


class CollectorTests(unittest.TestCase):
    def test_parse(self):
        total, items = parse_page(xml())
        self.assertEqual(total, 1)
        self.assertEqual(items[0]['year'], 2026)
        self.assertNotIn('serviceKey', items[0]['url'])

    def test_error_and_unknown_schema(self):
        for payload in [b'<root><error>200</error></root>', b'<html/>', xml(year='2021')]:
            with self.assertRaises(ValueError): parse_page(payload)

    def test_pagination(self):
        calls = []
        def fetch(key, page, rows):
            calls.append(page)
            return parse_page(xml(total=2, identifier=f'OTP_{page}'))
        data = collect('test-not-a-real-key', 2, rows=1, fetch=fetch, pause=lambda _:None)
        self.assertEqual(len(data['items']), 2)
        self.assertEqual(calls, [1, 2])

    def test_incomplete_and_duplicate_fail(self):
        fetch = lambda *_: parse_page(xml(total=2))
        for pages in [1, 2]:
            with self.assertRaises(ValueError):
                collect('fixture', pages, rows=1, fetch=fetch, pause=lambda _:None)


if __name__ == '__main__': unittest.main()
