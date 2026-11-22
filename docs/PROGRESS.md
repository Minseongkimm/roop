# Roop PROGRESS

하드웨어: MacBook Air M3 16GB · 로컬: `qwen2.5-coder:7b` (`num_ctx 8192`) · API 호출 0
목표: 로컬 easy 90%, medium 80%. 검증용 실패로는 엔진을 고치지 않는다.
동결: `e656e3f`. 상한: 독립 생성 5회(온도 0.0/0.2/0.4/0.6/0.8). 수리 4회는 곱하지 않음. 생성 240초, 태스크 600초.

| 단계 | 상태 |
|------|------|
| 시험지 | easy 30, medium 30. 연습 15(기존 10 포함) / 검증 15. 정답 GREEN, 빈 구현 RED |
| 검증 Roop | easy 1회 8/15(53%), 5회 10/15(67%), 평균 28초. medium 1회 2/15(13%), 5회 4/15(27%), 평균 124초 |
| 검증 Aider | easy 1회 8/15(53%), 5회 11/15(73%), 평균 39초. medium 1회 5/15(33%), 5회 8/15(53%), 평균 145초 |

형식 오류: Roop 0/103, Aider 0/86. 실패 상위 3: assertion 14, syntax 8, missing module 3.
측정: Roop 38분 + Aider 46분 = 1시간 24분. 측정 중 수정 없음. 목표는 아직 못 넘김.
운영: `docs/MAP.md` · 과거: `docs/HISTORY.md` · 체크: `make check`
