import json
import logging
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Do not include request bodies, headers, secrets, or exception text.
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "event": record.getMessage(),
            }
        )


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.getLogger().handlers = [handler]
    logging.getLogger().setLevel(level)
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
