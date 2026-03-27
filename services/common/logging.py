from __future__ import annotations

import logging
from typing import Any

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _CONFIGURED = True


class StructuredAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        extra = self.extra or {}
        context = " ".join(f"{k}={v}" for k, v in extra.items() if v is not None and v != "")
        if context:
            msg = f"{msg} | {context}"
        return msg, kwargs


def get_logger(name: str, **context: Any) -> StructuredAdapter:
    configure_logging()
    return StructuredAdapter(logging.getLogger(name), context)

