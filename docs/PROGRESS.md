# Roop PROGRESS

하드웨어: MacBook Air M3 16GB · 로컬 `qwen2.5-coder:7b` · 이번 측정은 Groq 무료 `groq/qwen/qwen3.8-27b` · 엔진 동결 `e656e3f`
목표: 로컬 easy 90%, medium 80%. 검증용 실패로는 엔진을 고치지 않는다.

| 단계 | 상태 |
|------|------|
| 시험지 | easy 30, medium 30. 연습 15 / 검증 15 |
| 검증 Roop 7B | easy 1회 8/15(53%), 5회 10/15(67%). medium 1회 2/15(13%), 5회 4/15(27%) |
| 검증 Aider 7B | easy 1회 8/15(53%), 5회 11/15(73%). medium 1회 5/15(33%), 5회 8/15(53%) |
| 검증 Aider Groq 27B | medium 평균 33/45(73%), any-of-3 12/15. 인프라 0, 형식 오류 0 |

7B+Aider 기준선(33%) 대비 +40%p. 맥미니 기준은 평균 53% 이상(+20%p), 60% 근처면 분명한 구매.
API 정밀도는 로컬 Q4보다 높을 수 있어 결과를 조금 할인해서 볼 것. 3회 모두 실패: html-attr, span-contains, level-filter.
운영: `docs/MAP.md` · 과거: `docs/HISTORY.md` · 체크: `make check`
