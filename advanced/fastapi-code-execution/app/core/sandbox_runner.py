import ast
import io
import time
from typing import Any

from app.core.exceptions import AppError, PayloadTooLargeError

_ALLOWED_CALLS = frozenset({"print", "range", "len", "sum", "min", "max", "abs"})
_FORBIDDEN_SNIPPETS = (
    "import",
    "__",
    "open(",
    "exec(",
    "eval(",
    "compile(",
    "globals(",
    "locals(",
    "getattr(",
    "setattr(",
    "delattr(",
    "subprocess",
    "os.",
    "sys.",
    "time.",
)


def validate_source(source: str, *, max_bytes: int) -> None:
    encoded = source.encode("utf-8")
    if len(encoded) > max_bytes:
        raise PayloadTooLargeError(f"Source exceeds max size of {max_bytes} bytes")
    lowered = source.casefold()
    for snippet in _FORBIDDEN_SNIPPETS:
        if snippet in lowered:
            raise AppError(f"Forbidden construct in source: {snippet!r}")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise AppError("Imports are not allowed in sandboxed Python")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id not in _ALLOWED_CALLS:
                raise AppError(f"Function call {node.func.id!r} is not allowed")


def run_python(source: str) -> tuple[int, str, str, int]:
    buffer = io.StringIO()

    def sandbox_print(*args: Any, **kwargs: Any) -> None:
        kwargs.pop("file", None)
        print(*args, file=buffer, **kwargs)

    safe_builtins = {
        "print": sandbox_print,
        "range": range,
        "len": len,
        "sum": sum,
        "min": min,
        "max": max,
        "abs": abs,
    }
    namespace: dict[str, Any] = {"__builtins__": safe_builtins}
    started = time.perf_counter()
    try:
        exec(source, namespace, namespace)  # noqa: S102 — intentional sandbox sample
        runtime_ms = int((time.perf_counter() - started) * 1000)
        return 0, buffer.getvalue(), "", runtime_ms
    except Exception as exc:  # noqa: BLE001 — surface user errors as stderr
        runtime_ms = int((time.perf_counter() - started) * 1000)
        return 1, buffer.getvalue(), str(exc), runtime_ms
