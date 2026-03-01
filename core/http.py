from __future__ import annotations

from uuid import uuid4

from fastapi import Request


def get_or_create_request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    if isinstance(existing, str) and existing.strip():
        return existing.strip()

    header_value = request.headers.get("X-Request-ID", "").strip()
    request_id = header_value or str(uuid4())
    request.state.request_id = request_id
    return request_id
