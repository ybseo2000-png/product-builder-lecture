# 나라장터 엑셀 목록

사용자 제공 NaraJanter.xlsx의 Sheet1에서 234건을 변환했습니다. 게시일 범위는 2022-02-28~2026-10-12이며, 모든 공고기관/수요기관은 문화체육관광부입니다. 5건의 취소공고와 변경/재공고를 포함합니다. 공고번호는 차수까지 보존하며 서로 다른 차수를 임의로 합치지 않습니다.

업종 및 원문 URL 칼럼이 없으므로 학술·연구용역(1169) 조건이나 원문 이동을 검증하지 못했습니다. 원문 링크를 추측해 생성하지 않고 공식 나라장터 홈페이지 링크와 공고번호 복사를 제공합니다. 전체 기간의 모든 공고를 빠짐없이 수집했다는 의미가 아닙니다.

## 파일 추가/갱신

변환 실행 환경에 openpyxl이 필요합니다. 사이트 방문자에게는 필요하지 않으며 별도 API 키도 사용하지 않습니다.

```sh
python3 scripts/import_nara.py /path/to/file.xlsx
# 월별 여러 파일을 합칠 때 기존 파일도 함께 전달
python3 scripts/import_nara.py /path/to/2022.xlsx /path/to/2023.xlsx /path/to/new.xlsx
python3 -m unittest discover -s tests -p 'test_nara.py'
```

출력 파일은 data/nara.json입니다. 입력 파일 전체를 다시 변환하는 방식이므로 일부 월 파일만 입력하면 기존 다른 월은 포함되지 않습니다. 기존 파일을 모두 전달하거나 전체 기간을 포함하는 엑셀을 사용하세요. 동일 번호·동일 내용은 중복 제거하고 동일 번호·다른 내용은 검토를 위해 실패 처리합니다. 사이트는 엑셀을 직접 내려받거나 실행하지 않으며 변환한 JSON만 사용합니다.

원본 엑셀은 GitHub에 업로드하지 않았습니다. 출처 파일명과 SHA-256만 메타데이터로 남깁니다. 월별 새 파일을 받으면 변환 후 data/nara.json을 커밋하면 Publish website가 자동 배포합니다. 자동 API 갱신은 없습니다.

bids.html에 제목/번호/기관 검색, 게시연도·월·공고 구분 필터를 제공합니다. 공고번호 복사는 브라우저 Clipboard API를 이용하고, 지원되지 않으면 번호를 직접 복사하도록 안내합니다. 조회일 기준 자동 마감/진행 여부는 판단하지 않습니다.

## API 상세 링크 보강

사용자가 제공한 실제 JSON 응답의 `response.body.items[].bidNtceDtlUrl`을 수집합니다. `scripts/collect_nara_links.py`가 엑셀의 전체 공고번호를 본번호/차수로 나누고, inqryDiv=2, bidNtceNo=본번호, type=json, numOfRows=100, pageNo=1부터 조회합니다. totalCount에 따라 추가 페이지를 읽으며 정확한 본번호/차수 일치 결과만 사용합니다. 예시 응답의 공고는 엑셀 목록에 임의 추가하지 않습니다.

`data/nara-links.json`은 엑셀 변환 결과와 별도 보관해 새 파일 수입 시 링크를 덮어쓰지 않습니다. 기본 CLI는 정상 링크를 재사용할 수 있으나, 현재 workflow는 `--refresh`로 성공 캐시까지 포함해 전체 본번호를 다시 조회합니다. 목록과 일치하는 항목만 화면에 표시합니다.

`Collect Nara notice detail links` Actions가 최초 코드 push, data/nara.json 갱신, 수동 실행 시 동작합니다. 기존 `PRISM_API_KEY` Secret만 직접 사용합니다. 별도의 NARA_API_KEY를 등록할 필요가 없습니다. 같은 공공데이터포털 인증키를 사용할 수 있더라도 **조달청 나라장터 입찰공고정보서비스의 활용 승인**은 별도 필요할 수 있습니다. 권한이 없으면 NARA_AUTH 메시지를 남기고 이전 자료를 보존합니다. 키 값은 채팅/코드/공개 JSON에 넣지 않습니다.

검증된 URL은 조회 칼럼에 '공고 세부 정보 보기' 링크로 표시합니다. not_found/no_url/failed/미수집을 구분하고 공고번호 복사를 유지합니다. 링크는 공식 g2b.go.kr 도메인만 허용합니다. 공고차수가 다른 링크를 임의로 연결하거나 추정 URL로 대체하지 않습니다. 웹사이트는 API를 직접 호출하지 않습니다.

공고번호 `R26BK01765062-000`의 요청 `bidNtceNo`는 `R26BK01765062`입니다. `-000`은 전달하지 않으며, 원본 번호와 차수는 응답 대응 및 링크 검증을 위해 내부에 보존합니다.

## 담당부서

공고번호/차수 일치 응답의 refNo 원문과 department를 함께 저장합니다. department는 원문의 문자·공백만 남기고 숫자·기호를 제거한 값입니다. 예: 국제관광서비스과-6280 → 국제관광서비스과. 빈 값이나 숫자/기호만 있는 값은 null로 저장하고 화면에는 —를 표시합니다. 세부 URL이 없는 응답이라도 refNo가 있으면 부서를 수집합니다. 기존 refNo가 없는 링크 캐시도 다시 조회하며, workflow는 전체 재조회합니다.

## 장애 진단과 중간 저장 (최신 동작)

기존 실행의 'API 연결 또는 JSON 해석 실패' 로그만으로는 시간 초과와 비JSON 응답을 구분할 수 없었습니다. 현재는 HTTP 상태/응답 종류(JSON/XML/HTML/OTHER)/바이트 수를 기록하고, TIMEOUT/NETWORK_ERROR/TLS_ERROR/HTTP_ERROR/NON_JSON/INVALID_JSON을 구분합니다. 키·요청 URL·응답 원문은 출력하지 않습니다. TLS 검증은 유지합니다.

스크립트/워크플로 변경 push는 예시 공고 R26BK01687571-000 한 건을 한 번만 진단합니다. 이 모드는 공개 데이터 수정/배포를 하지 않습니다. 전체 수집은 Actions → Collect Nara notice detail links → Run workflow → mode=full일 때만 실행됩니다. 기본 수동 모드는 diagnose입니다. 한 건 진단의 결과/오류는 GitHub Annotation에 안전한 메시지로 남깁니다.

전체 수집에서는 성공 건마다 JSON을 원자적으로 저장하고, 실패 시 기존 정상 링크를 유지합니다. 연속 3건 실패 시 중단합니다. refNo/담당부서 확보 여부도 로그에 따로 표시합니다. 정상 링크 저장 여부만 나타내는 ok를 담당부서 수집 성공으로 해석하지 않습니다.

중간 결과에 processedCount/totalTargets/completed/departmentCount가 포함됩니다. full 작업의 always 단계에서 체크포인트 artifact와 GitHub 커밋을 시도합니다. 강제 종료나 러너 장애로 always 단계가 실행되지 못하면 미저장 진행분 복구를 보장하지 않습니다. full이 정상 완료된 경우만 자동 배포합니다. 실패 시 이전 링크를 덮어쓰지 않으며, 저장된 진행 결과는 이후 수동 실행에서 재사용합니다. refresh를 선택하면 성공 캐시도 다시 조회합니다.
