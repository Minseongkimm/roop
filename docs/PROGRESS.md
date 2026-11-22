# Roop PROGRESS

하드웨어: MacBook Air M3 16GB · 로컬: `qwen2.5-coder:7b` · API 기본: `gpt-4o-mini`
최종목표: 로컬이 초~중상 개발을 밤새 수행, 최상만 API.
엔진 동결 커밋: `87e0ead`

| 단계 | 상태 |
|------|------|
| 0~2b easy10 | 완료 8/10(80%) @ `2321d78`. 실패 slugify, chunk-list |
| 2c medium10 + API 폴백 | 동결 후 clean scratch 측정 |
| 3~6 모델표/병렬/맥미니 | 미착수 |

동결: 골든테스트는 읽기 전용. 로컬 검증 2회 실패 시 API. 키는 `ROOP_API_KEY`(없으면 `OPENAI_API_KEY`). 없으면 `api_skipped`.
운영: `docs/MAP.md` · 과거: `docs/HISTORY.md` · 체크: `make check`
다음 에이전트: MAP+PROGRESS만 읽고, 엔진 수정 전 측정 결과부터 판단.
