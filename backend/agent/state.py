"""Graph state for the analyst agent (agent/graph.py).

messages : the whole conversation; the add_messages reducer appends instead of overwriting
trips    : model to tool round trips used so far; the loop is capped at MAX_TOOL_TRIPS (agent/guardrails.py)
blocked  : an input guard refused the question
error    : why it was refused, when it was
flags    : guardrail events, for the audit trail
"""
from __future__ import annotations

from typing import Annotated, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    trips: int
    blocked: bool
    error: Optional[str]
    flags: list[str]
