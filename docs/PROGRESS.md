# Roop PROGRESS

하드웨어: MacBook Air M3 16GB · 로컬: `qwen2.5-coder:7b` (`num_ctx 8192`) · API: hard만
최종목표: 로컬이 초~중상 개발을 밤새 수행, 최상만 API.
엔진 동결 커밋: `d03a07a`

| 단계 | 상태 |
|------|------|
| 0~2b easy10 | 8/10(80%) @ `2321d78`. 실패 slugify, chunk-list |
| 2c/2d medium10 | 7B·14B 각 1/10 @ `87e0ead`. 통과는 graph-topo |
| 시험지 | easy·medium 정답 10/10, 빈 구현 0/10. 골든테스트 수정 없음 |
| 2e 측정 | easy 8/10(3분 1초), medium 1/10(20분 1초) @ `d03a07a`. API 호출 0 |

결론: 실패 본문·모듈 맵·로컬 4회 후에도 easy 80%, medium 10%. 점수는 그대로다.

동결: 골든테스트는 읽기 전용. easy·medium은 API를 호출하지 않는다. hard만 로컬 2회 실패 후 API.
운영: `docs/MAP.md` · 과거: `docs/HISTORY.md` · 체크: `make check`
다음 병목: 7B가 두 번째 src 파일을 빼먹거나, 틀린 파일을 같은 출력으로 반복한다.
