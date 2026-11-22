from pathlib import Path

from roop.context.builder import ContextBuilder
from roop.orchestrator.tasks import TaskStore


def _build_packet(project: Path, token_budget: int = 2000):
    store = TaskStore(project / ".agent" / "tasks.sqlite3")
    task = store.create_task("implement authentication")
    builder = ContextBuilder(project, token_budget=token_budget)
    return builder.build(task, "coder", include_code_slices=False)


def test_discovers_python_project_metadata(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# Sample API\nA FastAPI authentication service.",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "fastapi\nsqlalchemy\npwdlib[argon2]\nPyJWT\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "sample-api"\n',
        encoding="utf-8",
    )

    packet = _build_packet(tmp_path)

    assert "FastAPI" in packet.project_context
    assert "sqlalchemy" in packet.project_context
    assert "pwdlib" in packet.project_context
    assert "pyproject.toml" in packet.project_context


def test_discovers_node_project_metadata(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"name":"sample-web","dependencies":{"react":"^19.0.0","next":"^15.0.0"}}',
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions":{"strict":true}}',
        encoding="utf-8",
    )

    packet = _build_packet(tmp_path)

    assert "sample-web" in packet.project_context
    assert "react" in packet.project_context
    assert "tsconfig.json" in packet.project_context


def test_discovers_context_without_existing_source_code(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "fastapi\nsqlalchemy\n",
        encoding="utf-8",
    )

    packet = _build_packet(tmp_path)

    assert "fastapi" in packet.project_context
    assert packet.estimated_tokens <= packet.token_budget


def test_project_context_respects_token_budget(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Project overview " * 1000, encoding="utf-8")
    (tmp_path / "requirements.txt").write_text(
        "\n".join(f"package-{i}" for i in range(300)),
        encoding="utf-8",
    )

    packet = _build_packet(tmp_path, token_budget=500)

    assert packet.estimated_tokens <= packet.token_budget
    assert packet.project_context
