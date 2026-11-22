# Cursor 사용량 예산 (Roop)

## 원칙
- Cursor = 엔진 수정·설계만
- 로컬 Ollama + `roop night` = 반복 실험
- 하루 Cursor 세션 1~2회, 세션당 목표 1줄

## 하루 세션 템플릿 (복붙)

```text
오늘 목표(1줄): …
범위: 파일/모듈 …
하지 말 것: night 전체 돌리기, 관련 없는 리팩터, 커밋/푸시(요청 전)
완료 기준: …
끝나면 멈춰. 추가 작업 제안만 하고 실행하지 마.
```

## 로컬 실험 (Cursor 끄고)

```bash
cd ~/Desktop/roop-api-playground
../roop/.venv/bin/python -m roop.cli night --project . --db .agent/roop-eval.sqlite3 --max-ticks 10
../roop/.venv/bin/python -m roop.cli eval scorecard --project . --db .agent/roop-eval.sqlite3
```

## 사용량 확인
- Cursor 대시보드 Spending / Usage
- 미사용분 이월 없음 → 주/월 균등 분배
