from __future__ import annotations

from pathlib import Path


class WriteGuard:
    """Allow writes only under <project>/.agent/**."""

    def __init__(self, project_root: Path) -> None:
        self.project_root: Path = project_root.resolve()
        self.agent_root: Path = self.project_root / ".agent"

    def is_allowed_write(self, target: Path) -> bool:
        resolved: Path = target.resolve()
        try:
            resolved.relative_to(self.agent_root)
            return True
        except ValueError:
            return False

    def assert_allowed_write(self, target: Path) -> None:
        if not self.is_allowed_write(target):
            raise PermissionError(
                f"Write blocked outside .agent/: {target} (project={self.project_root})"
            )

    def write_text(self, target: Path, content: str) -> None:
        self.assert_allowed_write(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
