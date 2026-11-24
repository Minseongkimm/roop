"""Prove each v2 golden test accepts the reference and rejects fixture and stub.

Reference and stub trees under evals/v2 are overlays: copy the shared fixture
first, then write those files on top. Hidden tests are never part of the fixture.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from roop.engines.base import EngineGeneration, EngineRequest
from roop.eval.retry_eval import run_retry_eval
from roop.eval.runner import install_fixture, install_golden_tests
from roop.eval.suite import EvalSuite, EvalTask, load_suite

V2_ROOT: Path = Path(__file__).resolve().parents[1] / "evals" / "v2"
V2_MANIFEST: Path = V2_ROOT / "manifest.json"


def test_v2_manifest_shape_and_fixture() -> None:
    suite: EvalSuite = load_suite(V2_MANIFEST)
    assert suite.name == "roop-eval-v2"
    assert suite.fixture == "fixture"
    assert len(suite.tasks) == 10
    assert {item.difficulty for item in suite.tasks} == {"single", "multi"}
    assert all(item.split == "heldout" for item in suite.tasks)
    singles: list[EvalTask] = suite.by_difficulty("single")
    multis: list[EvalTask] = suite.by_difficulty("multi")
    assert len(singles) == 5
    assert len(multis) == 5
    for item in suite.tasks:
        assert item.allow_paths == "src/**"
        assert item.src_files
        assert item.golden_test
        assert (V2_ROOT / item.golden_test).is_file()
        assert (V2_ROOT / "reference" / item.id).is_dir()
        assert (V2_ROOT / "stubs" / item.id).is_dir()
        for relative in item.src_files:
            reference = V2_ROOT / "reference" / item.id / relative
            assert reference.is_file(), f"missing reference file {relative} for {item.id}"


def test_install_fixture_copies_src_but_not_tests(tmp_path: Path) -> None:
    suite: EvalSuite = load_suite(V2_MANIFEST)
    written: list[Path] = install_fixture(project_root=tmp_path, suite=suite)
    assert any(path.name == "service.py" for path in written)
    assert (tmp_path / "src" / "service.py").is_file()
    assert not (tmp_path / "tests").exists()
    install_golden_tests(project_root=tmp_path, suite=suite, task_ids=["item-validate"])
    assert (tmp_path / "tests" / "test_item_validate.py").is_file()


def test_retry_eval_installs_v2_fixture_before_the_engine(tmp_path: Path) -> None:
    suite: EvalSuite = load_suite(V2_MANIFEST)
    seen: list[Path] = []

    class IdleEngine:
        name: str = "idle"

        def generate(self, request: EngineRequest) -> EngineGeneration:
            seen.append(request.workdir)
            return EngineGeneration(format_ok=False, format_error="no edit")

    rows: list[dict[str, object]] = run_retry_eval(
        engine=IdleEngine(),
        suite=suite,
        workspace=tmp_path,
        split="heldout",
        task_ids=["item-validate"],
        max_local_attempts=1,
    )
    task_dir: Path = tmp_path / "item-validate"
    assert rows[0]["task_id"] == "item-validate"
    assert seen == [task_dir]
    fixture_service: bytes = (V2_ROOT / "fixture" / "src" / "service.py").read_bytes()
    assert (task_dir / "src" / "service.py").read_bytes() == fixture_service
    assert (task_dir / "src" / "models.py").is_file()
    assert (task_dir / "tests" / "test_item_validate.py").is_file()
    assert "item-validate" in (tmp_path / "summary.txt").read_text(encoding="utf-8")


def test_v1_suite_has_no_fixture() -> None:
    from roop.eval.suite import default_suite_path

    suite: EvalSuite = load_suite(default_suite_path())
    assert suite.fixture == ""


def test_each_v2_task_is_green_on_reference_and_red_on_fixture_and_stub() -> None:
    suite: EvalSuite = load_suite(V2_MANIFEST)
    failures: list[str] = []
    for task in suite.tasks:
        for kind, should_pass in (
            ("reference", True),
            ("fixture", False),
            ("stub", False),
        ):
            code, detail = _run(suite, task, kind)
            passed: bool = code == 0
            if passed != should_pass:
                failures.append(
                    f"{task.id} {kind}: expected pass={should_pass} got code={code}\n{detail}"
                )
    assert failures == []


def _run(suite: EvalSuite, task: EvalTask, kind: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory(prefix=f"roop-v2-{task.id}-{kind}-") as temporary:
        project: Path = Path(temporary)
        install_fixture(project_root=project, suite=suite)
        if kind in {"reference", "stub"}:
            overlay: Path = V2_ROOT / ("reference" if kind == "reference" else "stubs") / task.id
            _overlay(overlay, project)
        install_golden_tests(project_root=project, suite=suite, task_ids=[task.id])
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            task.verify_command,
            cwd=project,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        detail: str = (completed.stderr or completed.stdout)[-800:]
        return completed.returncode, detail


def _overlay(source: Path, project: Path) -> None:
    src: Path = source / "src"
    if not src.is_dir():
        return
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        target: Path = project / "src" / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
