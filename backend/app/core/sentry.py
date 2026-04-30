"""
Sentry error tracking — BFIU Circular No. 29 §4.5
Production observability: captures unhandled exceptions, slow transactions,
and FastAPI request context for debugging without exposing PII.

Usage:
  Set SENTRY_DSN=https://xxx@sentry.io/xxx in .env.production
  Set ENVIRONMENT=production in .env.production

PII protection:
  - NID numbers masked in breadcrumbs
  - No request bodies captured (contains biometric data)
  - IP addresses not sent (BFIU data residency §5.2)
"""
import logging
import re
from typing import Optional

log = logging.getLogger(__name__)

_NID_RE = re.compile(r'\b\d{10,17}\b')


def _before_send(event: dict, hint: dict) -> Optional[dict]:
    """Strip PII before sending to Sentry."""
    # mask NID-like numbers in all string values
    def _mask(obj):
        if isinstance(obj, str):
            return _NID_RE.sub("***NID***", obj)
        if isinstance(obj, dict):
            return {k: _mask(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_mask(i) for i in obj]
        return obj

    # remove request body (may contain biometric base64)
    if "request" in event:
        event["request"].pop("data", None)
        event["request"].pop("body", None)
        # remove IP
        event["request"].pop("env", None)
        if "headers" in event["request"]:
            hdrs = event["request"]["headers"]
            hdrs.pop("Authorization", None)
            hdrs.pop("authorization", None)
            hdrs.pop("X-Forwarded-For", None)

    # mask breadcrumbs
    if "breadcrumbs" in event:
        event["breadcrumbs"] = _mask(event["breadcrumbs"])

    return event


def init_sentry(dsn: str, environment: str, release: str, traces_sample_rate: float = 0.1) -> bool:
    """
    Initialise Sentry SDK with FastAPI integration.
    Returns True if initialised, False if DSN missing (dev mode).
    """
    if not dsn:
        log.info("[Sentry] DSN not set — error tracking disabled (set SENTRY_DSN in .env.production)")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        logging_integration = LoggingIntegration(
            level=logging.WARNING,   # capture WARNING and above as breadcrumbs
            event_level=logging.ERROR,  # send ERROR and above as Sentry events
        )

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                logging_integration,
            ],
            traces_sample_rate=traces_sample_rate,  # 10% of requests for perf monitoring
            profiles_sample_rate=0.0,               # no profiling (PII risk)
            send_default_pii=False,                 # BFIU §5.2 — no PII to external services
            before_send=_before_send,
            max_breadcrumbs=20,
            attach_stacktrace=True,
            # ignore expected errors
            ignore_errors=[
                KeyboardInterrupt,
            ],
        )
        log.info("[Sentry] Initialised — env=%s release=%s traces=%.0f%%",
                 environment, release, traces_sample_rate * 100)
        return True

    except ImportError:
        log.warning("[Sentry] sentry-sdk not installed — run: pip install sentry-sdk[fastapi]")
        return False
    except Exception as exc:
        log.warning("[Sentry] Init failed: %s", exc)
        return False
