from __future__ import annotations

from fastapi.exceptions import RequestValidationError


class QueryAPIError(Exception):
    def __init__(self, code: str, status_code: int, message: str, hint: str | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message
        self.hint = hint


def build_query_error_payload(
    *,
    code: str,
    message: str,
    request_id: str,
    hint: str | None = None,
) -> dict[str, str | None]:
    return {
        "code": code,
        "message": message,
        "hint": hint,
        "request_id": request_id,
        "detail": message,
    }


def build_validation_hint(exc: RequestValidationError) -> str:
    if not exc.errors():
        return "요청 본문 형식을 확인하세요."

    first = exc.errors()[0]
    loc_items = [str(item) for item in first.get("loc", []) if str(item) != "body"]
    loc = ".".join(loc_items)
    msg = first.get("msg", "요청 본문 형식이 올바르지 않습니다.")
    if loc == "query":
        return "query는 1자 이상 입력해야 합니다."
    if loc:
        return f"{loc}: {msg}"
    return str(msg)
