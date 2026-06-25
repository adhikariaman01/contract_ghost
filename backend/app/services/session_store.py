"""Simple in-memory session store for LangGraph states."""
from __future__ import annotations

import threading
from typing import Optional
from app.models.state import ContractState

_lock = threading.Lock()
_sessions: dict[str, ContractState] = {}


def save_state(session_id: str, state: ContractState) -> None:
    with _lock:
        _sessions[session_id] = state


def get_state(session_id: str) -> Optional[ContractState]:
    with _lock:
        return _sessions.get(session_id)


def delete_state(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)


def list_sessions() -> list[str]:
    with _lock:
        return list(_sessions.keys())
