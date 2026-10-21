"""인공 XML fixture 테스트이며 실제 API 성공을 의미하지 않습니다."""
import unittest
from unittest.mock import patch
import contextlib
import io
from urllib.error import HTTPError
from http.client import IncompleteRead
from scripts.collect_nkis import CollectorError, collect, main, parse_page


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

    def test_korean_xml_encodings(self):
        for encoding in ['euc-kr', 'cp949', 'utf-8']:
            payload = ('<?xml version="1.0" encoding="' + encoding + '"?>').encode() + xml().decode().encode(encoding)
            total, records = parse_page(payload)
            self.assertEqual(total, 1)
            self.assertEqual(records[0]['title'], '테스트 보고서')

    def test_reject_bad_encoding(self):
        with self.assertRaises(CollectorError):
            parse_page(b'<?xml version="1.0" encoding="unknown"?><root/>')
        with self.assertRaises(CollectorError):
            parse_page(b'<?xml version="1.0" encoding="utf-8"?><root>\xff</root>')

    def test_error_and_unknown_schema(self):
        for payload in [b'<root><error>200</error></root>', b'<html/>', xml(year='2021')]:
            with self.assertRaises(CollectorError): parse_page(payload)

    def test_pagination(self):
        calls = []
        def fetch(key, page, rows):
            calls.append(page)
            return parse_page(xml(total=2, identifier=f'OTP_{page}'))
        data = collect('test-not-a-real-key', 2, rows=1, fetch=fetch, pause=lambda _:None)
        self.assertEqual(len(data['items']), 2)
        self.assertEqual(calls, [1, 2])

    def test_diagnostics_hide_key_and_url(self):
        secret = 'private-fixture-key-not-real'
        errors = [HTTPError('https://example.invalid/?serviceKey='+secret,403,secret,None,None),
                  RuntimeError(secret), IncompleteRead(secret.encode(), 100), CollectorError('SCHEMA_TOTAL: required field absent')]
        for error in errors:
            stderr = io.StringIO()
            with patch.dict('os.environ', {'NKIS_API_KEY': secret}), patch('sys.argv', ['collect_nkis']), patch('scripts.collect_nkis.collect', side_effect=error), contextlib.redirect_stderr(stderr):
                self.assertEqual(main(), 1)
            self.assertNotIn(secret, stderr.getvalue())
            self.assertNotIn('example.invalid', stderr.getvalue())
            self.assertIn('기존 데이터 파일은 교체하지 않았습니다', stderr.getvalue())

    def test_incomplete_and_duplicate_fail(self):
        fetch = lambda *_: parse_page(xml(total=2))
        for pages in [1, 2]:
            with self.assertRaises(CollectorError):
                collect('fixture', pages, rows=1, fetch=fetch, pause=lambda _:None)


if __name__ == '__main__': unittest.main()
