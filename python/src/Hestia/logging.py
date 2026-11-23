"""Optional Livy output for Hestia's diagnostic logging."""

import logging
from pathlib import Path

from Auctor.Livy import Livy


class _LivyHandler(logging.Handler):
    def __init__(self, livy: Livy, previous_level: int) -> None:
        super().__init__()
        self.livy = livy
        self.previous_level = previous_level

    def emit(self, record: logging.LogRecord) -> None:
        try:
            category = self.livy.create_category(record.name)
            message = record.getMessage()
            if record.exc_info and record.exc_info[1] is not None:
                category.exception(record.exc_info[1], message)
            elif record.levelno >= logging.ERROR:
                category.error(message)
            elif record.levelno >= logging.WARNING:
                category.warning(message)
            elif record.levelno >= logging.INFO:
                category.info(message)
            else:
                category.debug(message)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        self.livy.shutdown()
        super().close()


def configure_logging(path: str | Path, *, level: int = logging.DEBUG) -> Livy:
    """Route Hestia diagnostics to a Livy file, replacing any previous route.

    Standard logging propagation remains enabled; call shutdown_logging to stop.
    """
    livy = Livy("Hestia", path=path)
    if not livy.initialize():
        failure = livy.get_last_failure()
        raise OSError(failure.message if failure else "Could not initialize Livy")
    logger = logging.getLogger("Hestia")
    shutdown_logging()
    logger.addHandler(_LivyHandler(livy, logger.level))
    logger.setLevel(level)
    return livy


def shutdown_logging() -> None:
    """Detach and close Hestia's Livy logging route."""
    logger = logging.getLogger("Hestia")
    for handler in logger.handlers[:]:
        if isinstance(handler, _LivyHandler):
            logger.removeHandler(handler)
            logger.setLevel(handler.previous_level)
            handler.close()