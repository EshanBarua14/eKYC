"""
M65: Structured JSON Logging
BFIU Circular No. 29 — §5.1 audit trail integrity + observability

Pure stdlib implementation — no external deps required.
Outputs JSON lines to stdout for Docker log aggregation.
PII masking: NID, mobile, email fields auto-redacted.
Request-ID injected into every log record.
BST timestamps on all records.
"""
import json
import logging
import re
import sys
import traceback
from datetime import datetime, timezone, timedelta

BST = timezone(timedelta(hours=6))

# ── PII patterns to mask ──────────────────────────────────────────────────
_PII_PATTERNS = [
    (re.compile(r'("nid[_\s]*(number|hash)?"\s*:\s*")[^"]*"', re.I),
     lambda m: m.group(1) + "****REDACTED"),
    (re.compile(r'\b01[3-9]\d{8}\b'), lambda m: m.group(0)[:3] + "****" + m.group(0)[-3:]),
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
     lambda m: m.group(0).split("@")[0][:2] + "***@" + m.group(0).split("@")[1]),
]


def _mask_pii(text: str) -> str:
    for pattern, replacer in _PII_PATTERNS:
        text = pattern.sub(replacer, text)
    return text


class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON.
    Compatible with Docker log drivers, ELK, Loki, CloudWatch.
    """

    def format(self, record: logging.LogRecord) -> str:
        now_bst = datetime.now(BST)
        log_entry = {
            "timestamp": now_bst.isoformat(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Request context (injected by middleware)
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "role"):
            log_entry["role"] = record.role
        if hasattr(record, "institution_id"):
            log_entry["institution_id"] = record.institution_id

        # Exception info
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Extra fields
        for key, val in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName", "request_id", "user_id", "role", "institution_id",
            } and not key.startswith("_"):
                log_entry[key] = val

        line = json.dumps(log_entry, default=str, ensure_ascii=False)
        return _mask_pii(line)


class RequestContextFilter(logging.Filter):
    """Injects request context into every log record in the current thread."""

    _context: dict = {}

    @classmethod
    def set_context(cls, **kwargs):
        cls._context.update(kwargs)

    @classmethod
    def clear_context(cls):
        cls._context.clear()

    def filter(self, record: logging.LogRecord) -> bool:
        for key, val in self._context.items():
            setattr(record, key, val)
        return True


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    app_name: str = "ekyc",
) -> None:
    """
    Configure application-wide structured logging.
    Call once at app startup (app/main.py).

    json_output=True  → JSON lines (production/Docker)
    json_output=False → Human-readable (local dev)
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s %(request_id)s: %(message)s"
        handler.setFormatter(logging.Formatter(fmt))

    handler.addFilter(RequestContextFilter())
    root.addHandler(handler)

    # Silence noisy libs
    for lib in ["uvicorn.access", "httpx", "httpcore", "passlib"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.getLogger(app_name).info(
        "Logging configured",
        extra={"json_output": json_output, "level": level,
               "bfiu_ref": "BFIU Circular No. 29 §5.1"}
    )
