import json
import os
import threading
import time
from typing import Any


_CACHE_LOCK = threading.Lock()


def _cache_file_path() -> str:
    project_root = os.path.dirname(os.path.dirname(__file__))
    cache_dir = os.path.join(project_root, "data", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "ai_prompt_cache.json")


def _load_cache_data() -> dict[str, Any]:
    path = _cache_file_path()
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception("failed_loading_prompt_cache", exc_info=True)
        return {}


def _save_cache_data(payload: dict[str, Any]) -> None:
    path = _cache_file_path()
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def get_cached_try_asking_questions(dataset_cache_key: str) -> list[str]:
    dataset_cache_key = str(dataset_cache_key or "").strip()
    if not dataset_cache_key:
        return []

    with _CACHE_LOCK:
        cache = _load_cache_data()
        entry = cache.get(dataset_cache_key, {})
        questions = entry.get("try_asking_questions", []) if isinstance(entry, dict) else []
        if isinstance(questions, list):
            return [str(item).strip() for item in questions if str(item).strip()][:5]
    return []


def save_cached_try_asking_questions(dataset_cache_key: str, questions: list[str]) -> list[str]:
    dataset_cache_key = str(dataset_cache_key or "").strip()
    clean_questions = [str(item).strip() for item in (questions or []) if str(item).strip()][:5]
    if not dataset_cache_key or not clean_questions:
        return clean_questions

    with _CACHE_LOCK:
        cache = _load_cache_data()
        entry = cache.get(dataset_cache_key, {}) if isinstance(cache.get(dataset_cache_key, {}), dict) else {}
        entry["try_asking_questions"] = clean_questions
        cache[dataset_cache_key] = entry
        _save_cache_data(cache)

    return clean_questions


def get_cached_dataset_state(dataset_cache_key: str) -> dict[str, Any]:
    dataset_cache_key = str(dataset_cache_key or "").strip()
    if not dataset_cache_key:
        return {}

    with _CACHE_LOCK:
        cache = _load_cache_data()
        entry = cache.get(dataset_cache_key, {})
        return entry if isinstance(entry, dict) else {}


def get_all_cached_dataset_states() -> dict[str, Any]:
    """Return the entire cache mapping of dataset_cache_key -> state dict.

    This is used to enumerate persisted dataset states (for 'All Datasets' history view).
    """
    with _CACHE_LOCK:
        cache = _load_cache_data()
        return cache if isinstance(cache, dict) else {}


def save_cached_dataset_state(dataset_cache_key: str, state: dict[str, Any]) -> dict[str, Any]:
    dataset_cache_key = str(dataset_cache_key or "").strip()
    if not dataset_cache_key or not isinstance(state, dict):
        return state if isinstance(state, dict) else {}

    with _CACHE_LOCK:
        cache = _load_cache_data()
        entry = cache.get(dataset_cache_key, {}) if isinstance(cache.get(dataset_cache_key, {}), dict) else {}
        for key, value in state.items():
            entry[key] = value
        cache[dataset_cache_key] = entry
        _save_cache_data(cache)

    return state


def get_cached_response(dataset_cache_key: str, query_hash: str) -> dict[str, Any] | None:
    """Retrieve cached AI response for a specific query on a dataset."""
    dataset_cache_key = str(dataset_cache_key or "").strip()
    query_hash = str(query_hash or "").strip()
    if not dataset_cache_key or not query_hash:
        return None

    with _CACHE_LOCK:
        cache = _load_cache_data()
        entry = cache.get(dataset_cache_key, {})
        if not isinstance(entry, dict):
            return None
        
        response_cache = entry.get("response_cache", {})
        if not isinstance(response_cache, dict):
            return None
        
        response = response_cache.get(query_hash)
        return response if isinstance(response, dict) else None


def save_cached_response(dataset_cache_key: str, query_hash: str, response: dict[str, Any]) -> None:
    """Save AI response to disk cache by dataset and query hash."""
    dataset_cache_key = str(dataset_cache_key or "").strip()
    query_hash = str(query_hash or "").strip()
    if not dataset_cache_key or not query_hash or not isinstance(response, dict):
        return

    with _CACHE_LOCK:
        cache = _load_cache_data()
        entry = cache.get(dataset_cache_key, {}) if isinstance(cache.get(dataset_cache_key, {}), dict) else {}
        
        response_cache = entry.get("response_cache", {})
        if not isinstance(response_cache, dict):
            response_cache = {}
        
        response_to_store = dict(response)
        if "_original_query" not in response_to_store:
            response_to_store["_original_query"] = str(response.get("query", "") or "")

        response_cache[query_hash] = response_to_store
        entry["response_cache"] = response_cache
        cache[dataset_cache_key] = entry
        _save_cache_data(cache)


def cleanup_stale_cache(max_cache_entries_per_dataset: int = 100, max_age_seconds: int = 604800) -> None:
    """
    Cleanup cache to prevent unbounded growth.
    
    Args:
        max_cache_entries_per_dataset: Max responses per dataset (keeps newest)
        max_age_seconds: Max age of cached entries (604800 = 7 days)
    """
    with _CACHE_LOCK:
        cache = _load_cache_data()
        now = time.time()
        
        for dataset_key, entry in list(cache.items()):
            if not isinstance(entry, dict):
                continue
            
            # Clean up old responses
            response_cache = entry.get("response_cache", {})
            if isinstance(response_cache, dict) and len(response_cache) > max_cache_entries_per_dataset:
                # Keep only newest N responses (trim oldest)
                sorted_items = sorted(
                    response_cache.items(),
                    key=lambda x: x[1].get("last_api_call_ts", 0) if isinstance(x[1], dict) else 0,
                    reverse=True
                )
                response_cache = dict(sorted_items[:max_cache_entries_per_dataset])
                entry["response_cache"] = response_cache
            
            # Remove entries older than max_age_seconds
            if isinstance(response_cache, dict):
                entry["response_cache"] = {
                    k: v for k, v in response_cache.items()
                    if isinstance(v, dict) and (now - v.get("last_api_call_ts", now)) < max_age_seconds
                }
            
            cache[dataset_key] = entry
        
        _save_cache_data(cache)


def clear_cache_for_dataset(dataset_cache_key: str) -> None:
    """Invalidate all cached responses for a specific dataset (after re-upload)."""
    dataset_cache_key = str(dataset_cache_key or "").strip()
    if not dataset_cache_key:
        return
    
    with _CACHE_LOCK:
        cache = _load_cache_data()
        if dataset_cache_key in cache:
            entry = cache.get(dataset_cache_key, {})
            if isinstance(entry, dict):
                entry["response_cache"] = {}  # Clear responses but keep try_asking_questions
                cache[dataset_cache_key] = entry
                _save_cache_data(cache)


def get_global_state_value(key: str):
    """Get a global app-level persisted value from the cache file.

    This is stored under a reserved top-level key `_global` in the cache file.
   """
    key = str(key or "").strip()
    if not key:
        return None

    with _CACHE_LOCK:
        cache = _load_cache_data()
        global_state = cache.get("_global", {}) if isinstance(cache.get("_global", {}), dict) else {}
        return global_state.get(key)


def save_global_state_value(key: str, value) -> None:
    """Persist a single global app-level key/value to the cache file.

    Uses a reserved top-level key `_global` in the same JSON cache used
    for per-dataset persistence.
   """
    key = str(key or "").strip()
    if not key:
        return

    with _CACHE_LOCK:
        cache = _load_cache_data()
        global_state = cache.get("_global", {}) if isinstance(cache.get("_global", {}), dict) else {}
        global_state[key] = value
        cache["_global"] = global_state
        _save_cache_data(cache)
