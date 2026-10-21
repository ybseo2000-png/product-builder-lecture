# NKIS 연결: 사용자 설정과 확인 방법

## 공식 확인 결과 (2026-10-21)

- 소개: https://nkis.re.kr/openDesc.do
- API 목록: https://nkis.re.kr/openSvcList.do
- 연구보고서 명세: https://nkis.re.kr/openSvcDtl1.do?sApiCd=OA-1010&factorCd1=OA-1010&factorCd2=OA-1020&resultCd1=OA-2010&resultCd2=OA-2020
- 목록 API: https://nkis.re.kr/nkisApi/search/ReportList.do
- 인증 없이 요청한 결과: HTTP 200이지만 XML error=200, '필수 입력값이 누락되었습니다.' 따라서 HTTP 200만으로 성공 판정하지 않습니다.
- serviceKey 필수, pageNo/rowCnt 페이지 처리, pblYyBegin/pblYyEnd 발행연도 범위 지원.
- 출력: TOTAL_COUNT, OTP_ID, OTP_SEQ, OTP_HAN_NM, PUBAGC, PBL_YY, ORG_LINK 등.
- 이 API는 연구보고서 목록입니다. 수행 연구과제 전체 목록이 아닙니다. 공식 목록 안내는 26개 소관기관 보고서를 설명하며, 연구회 자체 보고서까지 모두 제공되는지는 실제 결과로 추가 확인해야 합니다.
- 이제 NKIS 사이트는 이 클라우드에서 접속됩니다. 앞선 네트워크 차단 상태와 달라졌습니다.

## 사용자 절차

1. NKIS 회원가입/로그인 → 게시판 → 오픈API에서 연구보고서 API 활용을 신청합니다. 공식 소개에는 기관 검토 및 승인 후 키를 발급한다고 안내되어 있습니다.
2. GitHub 저장소 Settings → Secrets and variables → Actions → New repository secret.
3. Name에 NKIS_API_KEY, Secret에 NKIS에서 발급받은 인증키 원문을 입력합니다. 전체 요청 URL 또는 URL 인코딩한 키가 아닌 발급받은 원문을 사용합니다. 키는 채팅, 코드, 문서에 적지 않습니다.
4. 저장소 Settings → Pages → Build and deployment → Source를 GitHub Actions로 변경합니다. 이 작업은 기존 브랜치 배포에서 Actions 배포로 전환합니다. Actions의 기본 토큰으로 만든 커밋은 별도 Pages 빌드를 시작하지 않으므로 수집 workflow가 직접 배포하도록 구성했습니다.
5. 저장소 Actions → Collect NKIS reports → Run workflow → main을 선택해 실행합니다.
6. collect와 deploy 두 작업의 성공 여부를 확인합니다. 실패 시 키가 포함된 URL/원문 응답을 공유하지 말고 실패한 단계 이름만 알려주세요.
7. 성공 후 연구보고서 페이지의 최종 수집 시각과 건수를 확인하고 공식 원문과 표본 대조합니다. 기관 누락, 과거 자료 범위, 원문 이동도 검증해야 합니다.

현재는 workflow_dispatch 수동 실행만 지원합니다. 최초 실제 수집 및 이용 한도 확인 후 정기 실행을 추가할 예정입니다. 브랜치 보호/Actions 조직 정책이 있으면 커밋이나 배포가 제한될 수 있습니다.

## 코드와 처리 과정

- scripts/collect_nkis.py: NKIS_API_KEY를 환경에서 읽고 2022~2026년 발행 보고서를 페이지별로 수집합니다. 기본 10건/페이지, 0.3초 간격이며 실제 호출 제한은 승인 조건을 확인해야 합니다.
- XML 태그 문서상 필드 기준으로 행을 판별합니다. 실제 승인 응답의 XML 컨테이너 구조는 아직 확인하지 못했습니다. 미인식 형식은 수집 실패로 처리합니다.
- 모든 페이지의 총 건수 일치와 식별자 중복을 검사하고 완료됐을 때만 data/research.json을 원자적으로 갱신합니다. 실행 제한은 최대 10,000페이지/180분입니다. 변경 중인 데이터로 총 건수/중복이 달라지면 중단하며 이후 재실행이 필요합니다.
- 각 보고서는 NKIS 홈페이지에서 확인한 subject_view1.do 주소 형식을 사용합니다. 실제 보고서 원문 링크 이동은 수집 후 확인해야 합니다.
- API URL, 키, 원본 응답은 로그나 공개 데이터에 저장하지 않습니다. 공개 필드는 보고서 ID, 발행연도, 제목, 기관, NKIS 상세 링크입니다.
- 인증키를 포함한 요청을 다른 호스트로 리다이렉트하지 않으며 HTTPS 인증서 검증을 유지합니다.
- .github/workflows/collect-nkis.yml: 수동 실행 → 테스트 → 수집 → 데이터 형식 검사 → 커밋 → 공개 파일만 Pages에 배포.

## 검증 범위

인공 XML fixture 기반 테스트 4개와 데이터 계약 테스트를 실행했습니다. 이것은 실제 API 인증, 실자료 수집 성공, GitHub Actions 실행 및 공개 배포 성공을 의미하지 않습니다. 키 등록 후 최초 실제 실행 결과 확인이 남아 있습니다.

## 수집 실패 시 진단

기존 `Process completed with exit code 1`만으로는 원인을 알 수 없습니다. 최신 코드는 키와 요청 URL을 숨기면서 다음을 구분합니다.

- Secret 미등록: `NKIS_API_KEY Secret이 필요합니다`.
- API_ERROR: NKIS가 오류 XML을 반환함. 승인 상태/서비스 사용 권한 확인.
- HTTP_ERROR: HTTP 상태만 출력. 접근 제한이나 서버 오류 확인.
- NETWORK_ERROR / TIMEOUT / TLS_ERROR: 연결 단계 실패.
- XML_ERROR / SCHEMA_TOTAL / SCHEMA_ROWS / SCHEMA_RECORD: 실제 응답이 예상 XML/명세와 다름.
- 그 외 중복, 총 건수 변경, 수집 제한 도달: 원인을 고정 문구로 표시하고 이전 자료 유지.

오류 문구는 진단 범주이며, 예를 들어 API_ERROR만으로 키가 틀렸다고 확정하지 않습니다.
수정 후에는 예전 실행의 Re-run 대신 Actions → Collect NKIS reports → Run workflow → main으로 새 실행을 만드세요. 예전 실행을 다시 돌리면 예전 코드로 실행될 수 있습니다.

런너는 ubuntu-24.04로 고정했고 checkout/setup-node/setup-python을 공식 v6 태그로 갱신했습니다. 기존 Node 20 경고와 Ubuntu 마이그레이션 안내는 수집 실패 원인과 별개의 항목입니다.

### 추가 진단과 한국어 인코딩

UNEXPECTED_ERROR가 보고되어 예외 메시지를 숨긴 채 예외 클래스 이름과 수집기 내부 함수/줄번호만 출력하도록 보강했습니다. 접속 후 HTTP 상태, 응답 크기 및 XML 해석 시작도 구분합니다. 요청 URL/키/원본 응답/지역변수는 출력하지 않습니다.

ElementTree가 EUC-KR XML bytes를 직접 파싱할 때 ValueError를 내는 문제를 인공 응답으로 재현했습니다. 선언된 UTF-8/EUC-KR/CP949 인코딩을 엄격히 디코딩하도록 수정했습니다. 이것이 사용자 실행의 실제 원인이었는지는 아직 확인되지 않았습니다. HTTP 프로토콜 오류도 별도로 구분합니다.
