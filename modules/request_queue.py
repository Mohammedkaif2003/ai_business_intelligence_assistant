"""
Request queue manager for handling rate-limited API calls.

When Groq returns 429 (rate limit), queue the request and retry after a delay
instead of immediately failing the user.
"""

import time
import threading
from typing import Any, Callable
from collections import deque


_QUEUE_LOCK = threading.Lock()
_REQUEST_QUEUE: deque[dict[str, Any]] = deque(maxlen=50)  # Max 50 queued requests
_QUEUE_ENABLED = True
_MIN_INTERVAL_BETWEEN_RETRIES = 8.0  # Seconds between queued request attempts
_LAST_QUEUE_ATTEMPT_TS = 0.0


def enable_queue():
    """Enable request queuing on rate limits."""
    global _QUEUE_ENABLED
    _QUEUE_ENABLED = True


def disable_queue():
    """Disable request queuing (requests will fail immediately)."""
    global _QUEUE_ENABLED
    _QUEUE_ENABLED = False


def is_queue_enabled() -> bool:
    """Check if request queuing is enabled."""
    return _QUEUE_ENABLED


def get_queue_length() -> int:
    """Get number of waiting requests in queue."""
    with _QUEUE_LOCK:
        return len(_REQUEST_QUEUE)


def queue_request(
    request_id: str,
    query: str,
    executor_func: Callable[..., Any],
    executor_kwargs: dict[str, Any],
) -> None:
    """
    Queue a request for later retry.

    Args:
        request_id: Unique ID for this request (timestamped)
        query: Original user query (for logging)
        executor_func: Function to call when retrying (e.g., chat_handler)
        executor_kwargs: Arguments to pass to executor_func
    """
    if not _QUEUE_ENABLED:
        return

    request_item = {
        "request_id": request_id,
        "query": query[:100],  # Truncate for logging
        "executor_func": executor_func,
        "executor_kwargs": executor_kwargs,
        "queued_at_ts": time.time(),
        "retry_count": 0,
    }

    with _QUEUE_LOCK:
        _REQUEST_QUEUE.append(request_item)


def try_process_queue(logger=None) -> dict[str, Any] | None:
    """
    Try to process next request in queue if enough time has passed.

    Returns the result dict if a request was processed, None otherwise.
    """
    global _LAST_QUEUE_ATTEMPT_TS

    if not _QUEUE_ENABLED:
        return None

    with _QUEUE_LOCK:
        if not _REQUEST_QUEUE:
            return None

        # Check if enough time has passed since last attempt
        now = time.time()
        if now - _LAST_QUEUE_ATTEMPT_TS < _MIN_INTERVAL_BETWEEN_RETRIES:
            return None

        request_item = _REQUEST_QUEUE[0]

    # Attempt to process request
    try:
        executor_func = request_item["executor_func"]
        executor_kwargs = request_item["executor_kwargs"]

        if logger:
            logger.info(
                "queue_processing_attempt",
                extra={
                    "request_id": request_item["request_id"],
                    "retry_count": request_item["retry_count"],
                    "queue_length": len(_REQUEST_QUEUE),
                },
            )

        result = executor_func(**executor_kwargs)

        # If successful, remove from queue
        if result and result.get("ok"):
            with _QUEUE_LOCK:
                _REQUEST_QUEUE.popleft()
            _LAST_QUEUE_ATTEMPT_TS = time.time()

            if logger:
                logger.info(
                    "queue_processing_success",
                    extra={
                        "request_id": request_item["request_id"],
                        "retry_count": request_item["retry_count"],
                    },
                )
            return result

        # Still rate-limited, increment retry count and keep in queue
        request_item["retry_count"] += 1
        _LAST_QUEUE_ATTEMPT_TS = time.time()

        if logger:
            logger.warning(
                "queue_processing_still_limited",
                extra={
                    "request_id": request_item["request_id"],
                    "retry_count": request_item["retry_count"],
                },
            )
        return None

    except Exception as exc:
        if logger:
            logger.error(
                "queue_processing_error",
                extra={"request_id": request_item["request_id"], "error": str(exc)},
            )
        return None


def clear_queue() -> int:
    """Clear all queued requests. Returns count of cleared items."""
    with _QUEUE_LOCK:
        size = len(_REQUEST_QUEUE)
        _REQUEST_QUEUE.clear()
    return size


def get_queue_stats() -> dict[str, Any]:
    """Get queue statistics for UI display."""
    with _QUEUE_LOCK:
        if not _REQUEST_QUEUE:
            return {"length": 0, "oldest_wait_ms": 0, "status": "empty"}

        oldest_item = _REQUEST_QUEUE[0]
        wait_ms = (time.time() - oldest_item["queued_at_ts"]) * 1000

        return {
            "length": len(_REQUEST_QUEUE),
            "oldest_wait_ms": wait_ms,
            "oldest_request_id": oldest_item["request_id"],
            "oldest_retry_count": oldest_item["retry_count"],
            "status": "processing" if wait_ms > _MIN_INTERVAL_BETWEEN_RETRIES * 1000 else "waiting",
        }


def is_api_unavailable(max_retries_before_fallback: int = 10) -> bool:
    """
    Check if API appears to be unavailable (too many retries).
    
    Returns True if oldest queued request has been retried many times,
    indicating that the API is likely down or severely rate-limited.
    
    Args:
        max_retries_before_fallback: Threshold for marking API as unavailable
    
    Returns:
        True if API appears unavailable, False otherwise
    """
    with _QUEUE_LOCK:
        if not _REQUEST_QUEUE:
            return False
        
        oldest_item = _REQUEST_QUEUE[0]
        return oldest_item["retry_count"] >= max_retries_before_fallback

