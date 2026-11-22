# Roop PROGRESS

하드웨어: MacBook Air M3 16GB · 로컬: `qwen2.5-coder:7b` / `14b`(ctx 8192) · API: `gpt-4o-mini`
최종목표: 로컬이 초~중상 개발을 밤새 수행, 최상만 API.
엔진 동결 커밋: `87e0ead` (main `8da2628`)

| 단계 | 상태 |
|------|------|
| 0~2b easy10 | 완료 8/10(80%) @ `2321d78`. 실패 slugify, chunk-list |
| 2c medium10 7B | 1/10(10%) @ `87e0ead`. 10분 46초. API 호출 0. `api_skipped` 8, fail 1 |
| 2d medium10 14B | 1/10(10%) @ `87e0ead`. 24분 11초. ctx 8192. 호출 0. `api_skipped` 9. 통과 graph-topo |
| 3~6 모델표/병렬/맥미니 | 미착수 |

결론: 7B→14B도 1/10(통과는 graph-topo뿐)이라 이 점수는 7B 한계가 아니라 동결 엔진 한계다.

동결: 골든테스트는 읽기 전용. 로컬 검증 2회 실패 시 API. 키는 `ROOP_API_KEY`(없으면 `OPENAI_API_KEY`). 없으면 `api_skipped`.
운영: `docs/MAP.md` · 과거: `docs/HISTORY.md` · 체크: `make check`
다음 에이전트: MAP+PROGRESS만 읽고, 엔진 수정 전 측정 결과부터 판단.
