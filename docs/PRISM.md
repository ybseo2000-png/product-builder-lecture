# 문화체육관광부 정책연구 과제

## 요청과 수집

사용자가 제공한 엔드포인트와 목록/상세 JSON 예시를 바탕으로 구현했습니다. 공식 포털 문서는 접속 당시 HTTP 503으로 열리지 않았습니다. 실제 승인 키를 이용한 응답 확인은 GitHub Actions에서 진행합니다.

- 목록: https://apis.data.go.kr/1741000/prism_v3/getResearchList_v3
- 상세: 같은 기본 경로의 getResearchDetail_v3
- Secret: PRISM_API_KEY (GitHub Actions repository secret). 코드/HTML/JSON에 키를 기록하지 않습니다.
- 기관 1371000, 시작 20220101, 종료 20270101, 50건/페이지, 1페이지부터 올림(totalCount/50) 페이지까지 조회합니다. 50의 배수일 때 빈 페이지를 추가 요청하지 않습니다.
- 별도 JSON 형식 파라미터는 사용자 명세에 없어 추가하지 않았습니다. Accept: application/json 헤더를 보내고 실제 JSON 응답 및 resultCode=0을 검증합니다.
- 날짜는 API start_date/end_date 조회 조건 그대로입니다. 수행일/발행일 중 검색 기준과 종료일 포함 여부는 미확인입니다. 발행연도 필터는 별개입니다. 미래 종료일을 API가 거절하면 기간을 임의 변경하지 않고 실패를 보고합니다.
- 목록의 6개 필드와 reportInfo.url 배열의 file_url/file_name/file_type만 공개 데이터로 저장합니다. 연락처/연구개요/계약정보는 저장하지 않습니다.
- 여러 파일은 모두 보존하고, 동일 URL만 중복 제거합니다. 화면은 '보고서 원본' 또는 '보고서 원본 1, 2…'로 표시합니다.
- 상세 실패는 failed로 남겨 다음 실행 때 재시도합니다. 성공한 상세 결과는 재사용합니다. 제공처 파일 변경을 확인하려면 별도 상세 갱신 정책이 필요합니다. 현재 자동 상세 재조회 주기는 없습니다.
- 목록 실패 시 기존 공개 파일을 유지합니다. 상세 조회는 0.5초 간격이며 실패하더라도 나머지 과제를 계속 처리합니다. 첫 전체 상세 조회가 시간 제한으로 중단되면 완료 데이터는 갱신되지 않으며 재실행이 필요합니다.

## 실행과 배포

`Collect PRISM policy research`는 최초 코드 push 또는 Actions의 Run workflow로 실행됩니다. 자동 주기 실행은 아직 설정하지 않았습니다. 수집 → 데이터 검사 → GitHub 저장 → Publish website 배포 순서입니다.

로컬 실행은 환경에 PRISM_API_KEY가 있어야 합니다. 키를 명령줄 인자로 전달하거나 shell tracing으로 출력하지 마세요.

```sh
python3 -m unittest discover -s tests -p 'test_prism.py'
python3 scripts/collect_prism.py
python3 scripts/validate_prism.py
```

prism.html은 검색/발행연도 필터, 목록 건수, 최종 갱신 시각, 상세 조회 실패 건수를 표시합니다. 수집 대기는 0건 조회 결과와 구분합니다.
