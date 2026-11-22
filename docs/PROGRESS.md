# Roop PROGRESS

하드웨어: MacBook Air M3 16GB · 로컬: `qwen2.5-coder:7b` (`num_ctx 8192`) · API: hard만
최종목표: 로컬 easy 90%, medium 80%. 검증용 실패로는 엔진을 고치지 않는다.
엔진 동결 커밋: `d03a07a` (비교 직전 커밋으로 다시 동결)

| 단계 | 상태 |
|------|------|
| 0~2e | easy 8/10, medium 1/10 @ `d03a07a`. API 호출 0 |
| 1 시험지 | easy 30, medium 30. 연습 15(기존 10 포함) / 검증 15. 정답 GREEN, 빈 구현 RED |
| 2 Best-of-5 | 독립 생성 5회(온도 0.0–0.8). 수리 4회는 곱하지 않음. 태스크당 600초. 점수표는 1회/5회 |
| 3 Aider | 아직 |
| 4 비교 | 아직 |

동결: 골든테스트는 읽기 전용. easy·medium은 API를 호출하지 않는다.
운영: `docs/MAP.md` · 과거: `docs/HISTORY.md` · 체크: `make check`
