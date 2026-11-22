# Roop HISTORY (archived session notes)

기준 이전 기록은 2026-11-22 세션에서 이관.

## 완료된 기반
- Stage0: playground `math_utils` Task #1 GREEN
- Stage1: JSONL rounds, night report, hard-stop wip (`87e88b3` 계열)
- Stage2a: eval suite 20 (easy10+medium10)
- 패치: empty-find→content, missing-path find/replace→create
- verifier ACTION 힌트, requirements 컨텍스트 축소
- identical SAW block을 `retry_count >= 2` 이후로 완화

## 실측 스냅샷
- clean scratch easy5 (정규화 전후): 약 60% (clamp/stack/safe-div GREEN; slugify/kv 이슈)
- literal `\\n` 정규화 후 slugify GREEN 재확인
- parse-kv는 혼합 개행/문자열 이슈로 별도 대응했다가, 측정 동결을 위해 `\\n` 조건 재좁힘

## 커밋 메모
- `fd16a7d` Stage1/2 관측성·eval·패치 정규화
- `d2b2475` literal `\\n` 정규화 (이후 조건 재좁힘 예정)
- `0afee23` 토큰절약 문서/`make check`/easy 골든테스트 동결 준비
- `aebea21` 동결 후 easy10 0%를 PROGRESS에 기록 (아래 측정은 무효)

## 2026-11-22 easy10 (`0afee23`) — 무효
- 워크스페이스: `~/Desktop/roop-eval-easy10-freeze` · 성공률 0/10 (0%)
- 원인: 7B 실력이 아니라 하네스 불일치. `tests/**`는 잠갔는데 프롬프트가 테스트 작성을 유도함
- 모델이 잠긴 tests를 쓰다 empty find / overwrite 거절로 실패 (format 6건). 이 0/10은 무효
- 다음 동결: `2321d78` (골든테스트 읽기 전용 + tests 쓰기 즉시 피드백)

## 2026-11-22 easy10 (`2321d78`) — 8/10
- 워크스페이스: `~/Desktop/roop-eval-easy10-freeze2` · 8/10 (80%)
- 실패 2개: slugify, chunk-list. 동일 SAW가 3회 반복되어 blocked. 엔진은 고치지 않음
- 통과 기준 70%를 넘김. 원인 요약은 medium10 측정 보고에 둔다

## PROGRESS에서 이관 (medium10 시작)
- 2b 재측정 대기는 `2321d78` 8/10으로 닫힘. 이전 0/10(`0afee23`)은 하네스 불일치로 무효
- 2c 이전의 medium 태스크는 모델에게 테스트 작성을 맡겼다. 고정 골든테스트로 교체한다
