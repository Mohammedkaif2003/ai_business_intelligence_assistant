from modules.app_logging import get_logger


def log_event(event_name: str, **kwargs) -> None:
    """Lightweight telemetry hook that logs events for observability.

    Non-blocking, writes to application logger. Meant to be safe for tests.
    """
    try:
        logger = get_logger("telemetry")
        logger.info(f"telemetry:{event_name}", extra={"meta": kwargs or {}})
    except Exception:
        # Telemetry must never raise
        pass
