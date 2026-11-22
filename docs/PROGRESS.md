# Roop 진척 체크포인트

기준: 2026-11-22 21:55 (Asia/Seoul)  
하드웨어: MacBook Air M3 16GB (맥미니 아직 아님)  
모델: `qwen2.5-coder:7b` (로컬 Ollama)

## 최종목표
로컬 LLM이 초~중상 개발을 밤새 수행하고, 최상만 API로 넘기는 개인용 자율 코딩 루프.  
Cursor는 엔진 수정용, 반복 실험은 로컬 Roop.

## 전체 프로세스 vs 현재

| 단계 | 내용 | 상태 |
|------|------|------|
| 0 | 파이프라인 1바퀴 GREEN (실파일+unittest) | **완료** — playground `math_utils` Task #1 done |
| 1 | 관측성: JSONL / night report / hard-stop `wip/` | **거의 완료** — 코드·테스트 있음, 커밋 전 |
| 2a | eval suite 20개 정의 (easy10+medium10) | **완료** — `evals/v1/manifest.json` |
| 2b | easy 성공률 안정 측정 | **진행중** — 신규파일 find/replace 정규화 추가, 성공률 재측정은 다음 |
| 2c | medium 성공률 측정 | **일부만** — merge/lru GREEN, 나머지 미완/중단 |
| 3 | 모델 크기 표 (7B / 에어최대 / 27B API) | **미착수** |
| 4 | Escape Hatch (막힐 때만 API) | **미착수** |
| 5 | Worktree 병렬 | **미착수** |
| 6 | 맥미니 구매 게이트 | **미착수** |

## 이번 세션에서 만든 것 (미커밋)
- `empty find` → 신규파일 `content` 정규화
- **없는 경로 + find/replace → replace를 content로 생성** (blocked 주원인 1)
- verifier `ACTION` 수리 힌트 + requirements.txt 컨텍스트 축소 (FastAPI 헛소리 완화)
- identical SAW 조기 block 완화 (`retry_count >= 2`)
- `src/roop/telemetry/` (rounds JSONL, wip)
- `src/roop/eval/` + CLI (`eval list/enqueue/run/scorecard`)
- `.cursorignore`, `docs/CURSOR_BUDGET.md`
- Roop pytest: **58 passed**

## playground 실측 요약
- validation Task #1: **done** (mean/median)
- 살아 있는 코드 예: `clamp`, `stack`, `chunk`, `flatten`, `merge`, `lru`, `math_utils`
- eval 대략: easy ~30–50%대 (DB별), blocked 다수 = 모델 실패+동일에러 재시도
- night3: 강제 중단됨 → running 잔여를 pending으로 복구함

## 운영 규칙 (토큰)
- Cursor: 하루 1목표 / 새 채팅 / `.cursorignore` 유지
- 실험: Cursor 끄고 터미널 `roop night` + `eval scorecard`
- 템플릿: `docs/CURSOR_BUDGET.md`

## 커밋/푸시 정책
- 의미 있는 체크포인트마다 에이전트가 커밋·푸시 가능 (사용자 승인됨)
- 권장: Cursor 세션 1~2개 묶어서 **하루 1~2커밋**
- 최신 푸시: `fd16a7d` — Stage1/2 관측성·eval·패치 정규화 (2026-11-22)

## 다음 Cursor 세션 (1줄만)
**목표:** 로컬 터미널에서 easy 5개 `night` + scorecard만 (Cursor 거의 끔).  
**하지 말 것:** night 전체 20, medium 일괄, API/맥미니.
