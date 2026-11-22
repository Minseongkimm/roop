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

## 2026-11-22 medium10 7B vs 14B (`87e0ead`)
- 엔진 파일은 `87e0ead` 그대로. 모델 이름만 환경변수, 14B 컨텍스트는 Ollama Modelfile `num_ctx 8192` (`qwen2.5-coder:14b-8k`)
- 7B 런타임 컨텍스트는 요청에 `num_ctx`가 없어 Ollama 기본 4096. 14B는 측정 내내 8192, 상주 9.5GB, GPU 100%
- 워크스페이스: 7B `~/Desktop/roop-eval-medium10`, 14B `~/Desktop/roop-eval-medium10-14b`
- API 키 없음. 호출 0, 비용 0. 실패는 고치지 않음
- 성공률: 7B 1/10(10%), 14B 1/10(10%). 합산 시간: 7B 10분 46초, 14B 24분 11초
- 메모리 여유 11–18%. OOM·Ollama 오류로 끊긴 14B 시도는 없음. 14B는 약 2.2배 느림
- 시도 횟수는 로컬 모델 호출만. `api_skipped` 틱은 빼었다

| 태스크 | 7B 결과 | 7B 시도 | 7B 시간 | 7B 원인 | 14B 결과 | 14B 시도 | 14B 시간 | 14B 원인 |
|--------|---------|---------|---------|---------|----------|----------|----------|----------|
| money-ledger | api_skipped | 2 | 93s | ImportError | api_skipped | 2 | 142s | parse/format 테스트 실패 |
| csv-roundtrip | api_skipped | 2 | 37s | 중복 헤더·따옴표 테스트 실패 | api_skipped | 2 | 132s | ImportError |
| template-filters | api_skipped | 2 | 45s | render 테스트 실패 | api_skipped | 2 | 140s | filter/render 테스트 실패 |
| retry-backoff | api_skipped | 2 | 40s | retry 동작 실패 | api_skipped | 2 | 108s | retry 동작 실패 |
| ini-roundtrip | fail | 3 | 95s | ImportError + Ollama 500(token repeat) | api_skipped | 2 | 175s | ImportError |
| bounded-batch | api_skipped | 2 | 64s | push_many·drain 실패 | api_skipped | 2 | 179s | drain 실패 |
| interval-coverage | api_skipped | 2 | 46s | merge·coverage 실패 | api_skipped | 2 | 98s | merge 실패 |
| config-defaults | api_skipped | 2 | 65s | roundtrip·defaults 실패 | api_skipped | 2 | 172s | nested merge 실패 |
| graph-topo | local_pass | 2 | 82s | 1회 실패 후 통과 | local_pass | 1 | 103s | 1회에 통과 |
| query-url | api_skipped | 2 | 78s | query 파싱 실패 | api_skipped | 2 | 201s | query·split 실패 |

- 결론: 더 큰 모델과 더 긴 컨텍스트로도 통과 태스크가 늘지 않았다. 1/10은 7B 한계가 아니라 동결 엔진 한계다

## 2026-11-23 시험지 + 로컬 루프 (`d03a07a`)
- 골든테스트 수정 없음. 정답 구현은 easy·medium 각 10/10 GREEN, 빈 모듈은 0/10. `make check`에 포함
- 엔진: 실패 traceback을 다음 프롬프트에 넣음, 기대 import·시그니처·src 내용, `num_ctx 8192`, py_compile 선행, Ollama 500은 횟수 밖, 로컬 4회, 같은 출력은 중단. easy·medium은 API 없음
- 측정은 clean scratch, `qwen2.5-coder:7b`, 요청 컨텍스트 8192 확인. 측정 중 수정 없음. API 호출 0
- easy 8/10(80%), 3분 1초. medium 1/10(10%), 20분 1초. 합 23분 3초. 통과는 이전과 같은 태스크뿐
- 이전 easy 시간은 라운드에 없다. 이전 medium 시간은 `87e0ead` 7B 표

| 태스크 | 이전 결과 | 이전 시도 | 이전 시간 | 이전 원인 | 새 결과 | 새 시도 | 새 시간 | 새 원인 |
|--------|-----------|-----------|-----------|-----------|---------|---------|---------|---------|
| math-mean-median | local_pass | 1 | — | | local_pass | 1 | 19s | |
| clamp-util | local_pass | 1 | — | | local_pass | 1 | 9s | |
| slugify | fail | 3 | — | test_collapse, 동일 SAW | fail | 2 | 17s | `h-e-l-l-o-w-o-r-l-d`, 같은 출력 |
| stack-class | local_pass | 1 | — | | local_pass | 1 | 18s | |
| parse-kv | local_pass | 1 | — | | local_pass | 1 | 11s | |
| is-palindrome | local_pass | 1 | — | | local_pass | 1 | 10s | |
| chunk-list | fail | 3 | — | test_chunks, 동일 SAW | fail | 4 | 58s | size<1에서 ValueError 없음 |
| flatten-once | local_pass | 1 | — | | local_pass | 1 | 13s | |
| counter-top | local_pass | 1 | — | | local_pass | 1 | 16s | |
| safe-div | local_pass | 1 | — | | local_pass | 1 | 12s | |
| money-ledger | api_skipped | 2 | 93s | ImportError | fail | 4 | 151s | `src.ledger` 없음 |
| csv-roundtrip | api_skipped | 2 | 37s | 중복 헤더·따옴표 | fail | 4 | 363s | `src.csv_write` 없음 |
| template-filters | api_skipped | 2 | 45s | render 실패 | fail | 4 | 102s | `return` outside function |
| retry-backoff | api_skipped | 2 | 40s | retry 동작 실패 | fail | 3 | 78s | `backoff_ms(0)`, 같은 출력 |
| ini-roundtrip | fail | 3 | 95s | ImportError + Ollama 500 | fail | 2 | 43s | NotImplementedError, 같은 출력 |
| bounded-batch | api_skipped | 2 | 64s | push_many·drain 실패 | fail | 4 | 99s | `src.bqueue` 없음 |
| interval-coverage | api_skipped | 2 | 46s | merge·coverage 실패 | fail | 2 | 53s | 입력 리스트를 수정, 같은 출력 |
| config-defaults | api_skipped | 2 | 65s | nested merge 실패 | fail | 3 | 105s | data가 defaults에 덮임, 같은 출력 |
| graph-topo | local_pass | 2 | 82s | 1회 실패 후 통과 | local_pass | 1 | 45s | 1회에 통과 |
| query-url | api_skipped | 2 | 78s | query 파싱 실패 | fail | 4 | 163s | `%20`을 공백으로 안 풂 |
