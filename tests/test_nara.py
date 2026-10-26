import tempfile
from pathlib import Path
import unittest
try:
 from openpyxl import Workbook
except ImportError:
 raise unittest.SkipTest("엑셀 변환 테스트에는 선택 의존성 openpyxl이 필요합니다")
from scripts.import_nara import parse_row,build,HEADERS

ROW=['일반용역','내자','취소공고','R26BK0001-001','<script>실행되면 안 됨</script>','문화체육관광부','문화체육관광부','2026/10/12 13:26(2026/10/23 10:00)']
class NaraTests(unittest.TestCase):
 def test_dates_and_cancellation_preserved(self):
  r=parse_row(ROW);self.assertEqual(r['year'],2026);self.assertEqual(r['month'],10);self.assertEqual(r['noticeType'],'취소공고');self.assertEqual(r['deadline'],'2026-10-23T10:00:00+09:00')
 def test_wrong_agency_or_date_rejected(self):
  for index,value in [(5,'다른기관'),(7,'잘못된 날짜'),(3,'')]:
   row=ROW.copy();row[index]=value
   with self.assertRaises(ValueError):parse_row(row)
 def test_multiple_files_deduplicate_but_keep_notice_versions(self):
  with tempfile.TemporaryDirectory() as folder:
   paths=[]
   for i in range(2):
    w=Workbook();s=w.active;s.append(HEADERS);s.append(ROW)
    if i:
     version=ROW.copy();version[3]='R26BK0001-002';s.append(version)
    p=Path(folder)/f'{i}.xlsx';w.save(p);paths.append(p)
   result=build(paths);self.assertEqual(result['totalCount'],2);self.assertEqual(result['duplicatesRemoved'],1);self.assertFalse(result['industryVerified']);self.assertFalse(result['hasOriginalUrls'])
 def test_conflicting_same_id_fails(self):
  with tempfile.TemporaryDirectory() as folder:
   w=Workbook();s=w.active;s.append(HEADERS);s.append(ROW);changed=ROW.copy();changed[4]='다른 내용';s.append(changed);p=Path(folder)/'a.xlsx';w.save(p)
   with self.assertRaises(ValueError):build([p])
