import logging
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_configured = False


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(level: str) -> None:
    global _configured
    resolved = getattr(logging, level.upper(), logging.INFO)
    if _configured:
        logging.getLogger().setLevel(resolved)
        return

    logging.basicConfig(
        level=resolved,
        format="%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
    )
    request_filter = RequestIdFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(request_filter)
    _configured = True
