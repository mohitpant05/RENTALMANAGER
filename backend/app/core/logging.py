import logging
from contextvars import ContextVar

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
_request_path_ctx: ContextVar[str] = ContextVar("request_path", default="")


def get_request_id() -> str:
    return _request_id_ctx.get()


def get_request_path() -> str:
    return _request_path_ctx.get()


def set_request_context(request_id: str, path: str) -> None:
    _request_id_ctx.set(request_id)
    _request_path_ctx.set(path)


def clear_request_context() -> None:
    _request_id_ctx.set("")
    _request_path_ctx.set("")


class RequestLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def _fmt(self, msg: str, **kwargs) -> str:
        rid = get_request_id()
        path = get_request_path()
        parts = []
        if rid:
            parts.append(f"[req={rid}]")
        if path:
            parts.append(f"[path={path}]")
        parts.append(msg)
        prefix = " ".join(parts)
        if kwargs:
            extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
            return f"{prefix} | {extra}"
        return prefix

    def info(self, msg: str, **kwargs) -> None:
        self._logger.info(self._fmt(msg, **kwargs))

    def warn(self, msg: str, **kwargs) -> None:
        self._logger.warning(self._fmt(msg, **kwargs))

    def error(self, msg: str, **kwargs) -> None:
        self._logger.error(self._fmt(msg, **kwargs))

    def debug(self, msg: str, **kwargs) -> None:
        self._logger.debug(self._fmt(msg, **kwargs))


def get_logger(name: str) -> RequestLogger:
    return RequestLogger(name)
