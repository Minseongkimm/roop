const NODE_POSITIONS = {
  state: { x: 110, y: 180 },
  role: { x: 240, y: 90 },
  packet: { x: 405, y: 90 },
  model: { x: 540, y: 180 },
  harness: { x: 405, y: 270 },
  verify: { x: 245, y: 270 },
};

const TICKS = [
  {
    tick: 1,
    role: "Planner",
    node: "state",
    anatomy: 0,
    kicker: "tick 1 · observe",
    title: "큐와 상태를 읽습니다",
    body: "pending task: “로그인 리다이렉트 고쳐”. SQLite row + .agent/state + git status만 봅니다. 채팅 히스토리는 넣지 않습니다.",
    code: null,
    queue: "queue · pending 1 → running",
  },
  {
    tick: 1,
    role: "Planner",
    node: "role",
    anatomy: 1,
    kicker: "tick 1 · role",
    title: "이번 틱 역할 = Planner",
    body: "한 틱에 역할 하나. 계획과 코딩을 같은 프롬프트에 섞지 않습니다.",
    code: null,
    queue: "queue · running · role=Planner",
  },
  {
    tick: 1,
    role: "Planner",
    node: "packet",
    anatomy: 2,
    kicker: "tick 1 · packet",
    title: "Planner용 패킷만 조립",
    body: "짧은 시스템 프롬프트 + 목표 문장. 전체 레포 트리는 넣지 않습니다.",
    code: `{
  "goal": "로그인 리다이렉트 고쳐",
  "root": "~/apps/shop",
  "budget_tokens": 8000
}`,
    queue: "queue · packet ready",
  },
  {
    tick: 1,
    role: "Planner",
    node: "model",
    anatomy: 3,
    kicker: "tick 1 · model",
    title: "Ollama에 JSON 스키마 강제",
    body: "로컬 7–8B가 Task JSON을 반환합니다. 파싱 실패면 1회만 재생성합니다.",
    code: `{
  "tasks": [{
    "title": "auth redirect when session expired",
    "allow_paths": ["auth/**"],
    "ac": ["pytest tests/test_auth_redirect.py exits 0"]
  }]
}`,
    queue: "queue · planned 1 task",
  },
  {
    tick: 1,
    role: "Planner",
    node: "harness",
    anatomy: 4,
    kicker: "tick 1 · harness",
    title: "하니스가 Task를 기록",
    body: "모델이 파일을 직접 쓰지 않습니다. 도구가 SQLite에 task를 enqueue합니다.",
    code: null,
    queue: "queue · pending 1 (coder)",
  },
  {
    tick: 1,
    role: "Planner",
    node: "verify",
    anatomy: 5,
    kicker: "tick 1 · verify",
    title: "GREEN 조건을 코드 전에 고정",
    body: "AC와 테스트 명령을 Task에 박아 둡니다. 나중에 모델이 ‘완료’라고 말해도 Verifier는 exit code만 믿습니다.",
    code: null,
    queue: "queue · planner done",
  },
  {
    tick: 2,
    role: "Coder",
    node: "role",
    anatomy: 1,
    kicker: "tick 2 · role",
    title: "Coder 틱",
    body: "auth 관련 파일 슬라이스 + AC만 줍니다. 전체 파일 dump 금지.",
    code: null,
    queue: "queue · running · role=Coder",
  },
  {
    tick: 2,
    role: "Coder",
    node: "packet",
    anatomy: 2,
    kicker: "tick 2 · packet",
    title: "좁은 컨텍스트 패킷",
    body: "Feature Router가 고른 context.md와 rg로 자른 심볼 슬라이스만 포함합니다.",
    code: `allow_paths: ["auth/**"]
slice: auth/session.py:40-88
ac: pytest tests/test_auth_redirect.py`,
    queue: "queue · coder packet",
  },
  {
    tick: 2,
    role: "Coder",
    node: "model",
    anatomy: 3,
    kicker: "tick 2 · model",
    title: "짧은 diff hunk JSON",
    body: "출력 토큰을 짧게. 장문 설명 대신 patch hunk.",
    code: `{
  "patch": "auth/session.py",
  "hunk": "+ if expired: return redirect('/refresh')"
}`,
    queue: "queue · model output",
  },
  {
    tick: 2,
    role: "Coder",
    node: "harness",
    anatomy: 4,
    kicker: "tick 2 · harness",
    title: "허용 경로 안에서만 patch",
    body: "WriteGuard가 auth/**만 통과시킵니다. Phase 0 기본값은 .agent/**만 — 이후 단계에서 allow_paths로 확장.",
    code: null,
    queue: "queue · patch applied",
  },
  {
    tick: 3,
    role: "Tester",
    node: "role",
    anatomy: 1,
    kicker: "tick 3 · role",
    title: "Tester 틱",
    body: "해당 테스트 파일만 돌립니다. 전체 스위트는 기본이 아닙니다.",
    code: null,
    queue: "queue · running · role=Tester",
  },
  {
    tick: 3,
    role: "Tester",
    node: "harness",
    anatomy: 4,
    kicker: "tick 3 · harness",
    title: "run_test 도구 실행",
    body: "모델이 ‘테스트 통과’라고 적어도 무시합니다. 하니스가 실제 명령을 돌립니다.",
    code: `$ pytest tests/test_auth_redirect.py
exit_code: 1
SAW: AssertionError: expected /refresh`,
    queue: "queue · test red",
  },
  {
    tick: 3,
    role: "Tester",
    node: "verify",
    anatomy: 5,
    kicker: "tick 3 · verify",
    title: "Verifier: RED → 재시도",
    body: "새 SAW를 Coder 패킷에만 붙여 다음 틱. 같은 SAW가 두 번이면 Blocked. retry > 3이면 Blocked.",
    code: `EXPECTED: redirect /refresh
SAW: AssertionError
retry: 1`,
    queue: "queue · retry coder",
  },
  {
    tick: 4,
    role: "Coder",
    node: "packet",
    anatomy: 2,
    kicker: "tick 4 · feedback",
    title: "같은 프롬프트 반복 금지",
    body: "EXPECTED / SAW / DEAD_ENDS를 다음 Coder 패킷에 붙입니다. 맹목 재시도가 아닙니다.",
    code: null,
    queue: "queue · coder retry",
  },
  {
    tick: 4,
    role: "Coder",
    node: "harness",
    anatomy: 4,
    kicker: "tick 4 · harness",
    title: "수정 patch 적용",
    body: "만료 세션 분기에서 refresh 경로로 보냅니다.",
    code: null,
    queue: "queue · patch v2",
  },
  {
    tick: 5,
    role: "Tester",
    node: "verify",
    anatomy: 5,
    kicker: "tick 5 · green",
    title: "Verifier: GREEN",
    body: "exit 0 · allow_paths 준수. lessons에 한 줄 규칙만 저장하고 task를 done으로 닫습니다.",
    code: `exit_code: 0
lesson: "만료 세션이면 refresh 경로"`,
    queue: "queue · empty · done",
  },
];

const els = {
  tickIndex: document.getElementById("tick-index"),
  rolePill: document.getElementById("role-pill"),
  queueMeta: document.getElementById("queue-meta"),
  panelKicker: document.getElementById("panel-kicker"),
  panelTitle: document.getElementById("panel-title"),
  panelBody: document.getElementById("panel-body"),
  panelCode: document.getElementById("panel-code"),
  runner: document.getElementById("runner"),
  traceList: document.getElementById("trace-list"),
  btnPlay: document.getElementById("btn-play"),
  btnStep: document.getElementById("btn-step"),
  btnReset: document.getElementById("btn-reset"),
  autoPlay: document.getElementById("auto-play"),
  anatomySteps: document.querySelectorAll("#anatomy-steps li"),
  nodes: document.querySelectorAll(".loop-svg .node"),
};

let cursor = -1;
let timerId = null;
let isPlaying = false;

function clearHighlights() {
  els.nodes.forEach((node) => node.classList.remove("is-active"));
  els.anatomySteps.forEach((step) => step.classList.remove("is-hot"));
}

function moveRunner(nodeKey) {
  const point = NODE_POSITIONS[nodeKey];
  if (!point) {
    return;
  }
  els.runner.setAttribute("cx", String(point.x));
  els.runner.setAttribute("cy", String(point.y));
}

function renderStep(index) {
  const step = TICKS[index];
  clearHighlights();
  const activeNode = document.querySelector(`.loop-svg .node[data-node="${step.node}"]`);
  if (activeNode) {
    activeNode.classList.add("is-active");
  }
  const anatomy = els.anatomySteps[step.anatomy];
  if (anatomy) {
    anatomy.classList.add("is-hot");
  }
  moveRunner(step.node);
  els.tickIndex.textContent = String(step.tick);
  els.rolePill.textContent = step.role;
  els.queueMeta.textContent = step.queue;
  els.panelKicker.textContent = step.kicker;
  els.panelTitle.textContent = step.title;
  els.panelBody.textContent = step.body;
  if (step.code) {
    els.panelCode.hidden = false;
    els.panelCode.textContent = step.code;
  } else {
    els.panelCode.hidden = true;
    els.panelCode.textContent = "";
  }
  const item = document.createElement("li");
  item.className = "is-latest";
  item.innerHTML = `<span class="tick-tag">t${step.tick} · ${step.role}</span><span>${step.title}</span>`;
  els.traceList.querySelectorAll("li").forEach((node) => node.classList.remove("is-latest"));
  els.traceList.prepend(item);
}

function stopTimer() {
  if (timerId !== null) {
    window.clearTimeout(timerId);
    timerId = null;
  }
}

function setPlaying(next) {
  isPlaying = next;
  els.btnPlay.textContent = next ? "일시정지" : "재생";
}

function stepOnce() {
  if (cursor >= TICKS.length - 1) {
    setPlaying(false);
    stopTimer();
    return false;
  }
  cursor += 1;
  renderStep(cursor);
  return cursor < TICKS.length - 1;
}

function scheduleNext() {
  stopTimer();
  if (!isPlaying || !els.autoPlay.checked) {
    return;
  }
  timerId = window.setTimeout(() => {
    const hasMore = stepOnce();
    if (hasMore) {
      scheduleNext();
    } else {
      setPlaying(false);
    }
  }, 1700);
}

function reset() {
  stopTimer();
  setPlaying(false);
  cursor = -1;
  clearHighlights();
  els.traceList.innerHTML = "";
  els.tickIndex.textContent = "0";
  els.rolePill.textContent = "idle";
  els.queueMeta.textContent = "queue · pending 1";
  els.panelKicker.textContent = "대기";
  els.panelTitle.textContent = "재생을 누르면 첫 틱이 시작합니다";
  els.panelBody.textContent =
    "Orchestrator는 큐에서 pending task 하나를 집어 이번 틱의 역할만 고릅니다. 계획·코딩·테스트를 한 프롬프트에 넣지 않습니다.";
  els.panelCode.hidden = true;
  els.panelCode.textContent = "";
  moveRunner("state");
}

els.btnStep.addEventListener("click", () => {
  stopTimer();
  setPlaying(false);
  stepOnce();
});

els.btnPlay.addEventListener("click", () => {
  if (isPlaying) {
    setPlaying(false);
    stopTimer();
    return;
  }
  if (cursor >= TICKS.length - 1) {
    reset();
  }
  setPlaying(true);
  if (cursor < 0) {
    stepOnce();
  }
  scheduleNext();
});

els.btnReset.addEventListener("click", () => {
  reset();
});

els.autoPlay.addEventListener("change", () => {
  if (isPlaying && els.autoPlay.checked) {
    scheduleNext();
  } else {
    stopTimer();
  }
});

reset();
