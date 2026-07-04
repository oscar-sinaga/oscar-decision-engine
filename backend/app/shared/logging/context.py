"""Request-scoped correlation context propagated via ``contextvars``.

The correlation middleware sets these at request start; runtime services,
trace persistence, and audit writers read them without threading identifiers
through every function signature.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("oscar_request_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("oscar_correlation_id", default=None)


def get_request_id() -> str | None:
    return _request_id.get()


def get_correlation_id() -> str | None:
    return _correlation_id.get()


@contextmanager
def set_correlation_context(request_id: str, correlation_id: str) -> Iterator[None]:
    token_req = _request_id.set(request_id)
    token_corr = _correlation_id.set(correlation_id)
    try:
        yield
    finally:
        _request_id.reset(token_req)
        _correlation_id.reset(token_corr)
