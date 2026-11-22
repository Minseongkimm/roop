# Roop PROGRESS

하드웨어: MacBook Air M3 16GB · 모델: `qwen2.5-coder:7b`  
최종목표: 로컬이 초~중상 개발을 밤새 수행, 최상만 API.  
엔진 동결 커밋: `0afee23`

| 단계 | 상태 |
|------|------|
| 0~2a 루프/관측성/eval20 정의 | 완료 |
| 2b easy10 골든테스트 측정 | **완료(동결 후)** — 성공률 **0/10 (0%)** |
| 2c~6 medium/모델표/API/병렬/맥미니 | 미착수 |

측정 워크스페이스: `~/Desktop/roop-eval-easy10-freeze` · FAILURES.md 있음  
주실패: 모델이 `tests/**`를 수정 시도(allow=src only) → empty find / overwrite 거절; 일부는 구현 로직 FAIL  
운영: `docs/MAP.md` · 과거: `docs/HISTORY.md` · 체크: `make check`  
다음 에이전트: MAP+PROGRESS만 읽고, 엔진 수정 전 측정 결과부터 판단.
