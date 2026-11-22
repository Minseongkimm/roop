# Roop PROGRESS

하드웨어: MacBook Air M3 16GB · 모델: `qwen2.5-coder:7b`  
최종목표: 로컬이 초~중상 개발을 밤새 수행, 최상만 API.

| 단계 | 상태 |
|------|------|
| 0 루프 1회 GREEN | 완료 |
| 1 관측성 JSONL/night/wip | 완료 |
| 2a eval 20 정의 | 완료 |
| 2b easy 성공률 측정 | 진행 (골든 테스트·엔진 동결 후 재측정) |
| 2c~6 medium/모델표/API/병렬/맥미니 | 미착수 |

운영: Cursor=엔진 수정만 · 반복=`roop night` · 맵=`docs/MAP.md` · 과거=`docs/HISTORY.md`  
체크: `make check` · 실패모음: `scripts/collect_failures.py`  
다음 에이전트: MAP + 이 파일만 읽고 시작. 엔진 동결 후 easy10 측정 결과로 판단.
