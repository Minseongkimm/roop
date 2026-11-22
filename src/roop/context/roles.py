"""Role prompts for one-tick agent packets (Phase 3)."""

from __future__ import annotations

from enum import StrEnum


class AgentRole(StrEnum):
    """Single-tick agent roles."""

    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"


ROLE_SYSTEM_PROMPTS: dict[AgentRole, str] = {
    AgentRole.PLANNER: (
        "You are the Planner. Output JSON only.\n"
        "Decompose the goal into small tasks with allow_paths, acceptance_criteria, "
        "depends_on, and verify_command.\n"
        "Do not write code. One decision this tick: the task plan."
    ),
    AgentRole.CODER: (
        "You are the Coder. Output JSON only with short patch hunks.\n"
        "Edit only paths listed in Task.allow_paths. Never invent other files.\n"
        "If allow_paths is a single file, that is the only path in files[].\n"
        "Prefer minimal diffs. No long explanations.\n"
        "One decision this tick: the patch for the current task."
    ),
    AgentRole.REVIEWER: (
        "You are the Reviewer. Output JSON only.\n"
        "List blocking issues against acceptance_criteria and allow_paths.\n"
        "Do not rewrite code. One decision this tick: approve or block."
    ),
    AgentRole.TESTER: (
        "You are the Tester. Output JSON only.\n"
        "Choose the narrowest verify_command / tests for this task.\n"
        "Do not claim pass/fail without harness results. One decision this tick: "
        "which checks to run."
    ),
}


def get_role_prompt(role: AgentRole) -> str:
    return ROLE_SYSTEM_PROMPTS[role]
