from __future__ import annotations

from functools import wraps
from typing import Any, Callable

try:
    from langsmith import traceable
except Exception:  # pragma: no cover
    traceable = None


def traced(name: str):
    def decorator(fn: Callable[..., Any]):
        if traceable is not None:
            try:
                return traceable(name=name)(fn)
            except Exception:
                pass

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        return wrapper
    return decorator
