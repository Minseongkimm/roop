# Roop PROGRESS

하드웨어: MacBook Air M3 16GB · 로컬: `qwen2.5-coder:7b` (요청 `num_ctx 8192`) · API: hard만
최종목표: 로컬이 초~중상 개발을 밤새 수행, 최상만 API.
엔진 동결 커밋: `d03a07a`

| 단계 | 상태 |
|------|------|
| 0~2b easy10 | 이전 8/10(80%) @ `2321d78`. 실패 slugify, chunk-list |
| 2c medium10 7B | 이전 1/10 @ `87e0ead`. 10분 46초. `api_skipped` 8 |
| 2d medium10 14B | 이전 1/10 @ `87e0ead`. 24분 11초. 통과 graph-topo |
| 시험지 | easy·medium 정답 10/10, 빈 구현 0/10. 골든테스트 수정 없음 |
| 2e 루프 | 동결 `d03a07a`. 실패 본문, 모듈 맵, ctx 8192, py_compile, 로컬 4회 |
| 2e 측정 | 아직. 측정 중에는 엔진을 고치지 않는다 |

결론: 7B→14B도 1/10이라 점수는 모델 크기가 아니라 엔진 한계였다. 이번 동결은 그 루프를 고친 뒤의 기준점이다.

동결: 골든테스트는 읽기 전용. easy·medium은 API를 호출하지 않는다. hard만 로컬 2회 실패 후 API.
운영: `docs/MAP.md` · 과거: `docs/HISTORY.md` · 체크: `make check`
다음 에이전트: MAP+PROGRESS만 읽고, 2e 측정이 끝나기 전에는 엔진을 고치지 마.
