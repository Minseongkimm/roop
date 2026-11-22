"""Phase 3 context packet builder."""

from roop.context.builder import BuildResult, CodeSlice, ContextBuilder, ContextPacket
from roop.context.roles import AgentRole, get_role_prompt

__all__ = [
    "AgentRole",
    "BuildResult",
    "CodeSlice",
    "ContextBuilder",
    "ContextPacket",
    "get_role_prompt",
]
