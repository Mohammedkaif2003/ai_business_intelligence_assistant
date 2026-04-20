import json
import os
import threading
from typing import List

_LOCK = threading.Lock()


def _cache_file_path() -> str:
    project_root = os.path.dirname(os.path.dirname(__file__))
    cache_dir = os.path.join(project_root, "data", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "ai_prompt_cache.json")


def _load_cache_data() -> dict:
    path = _cache_file_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("load_deleted_history_cache_failed", exc_info=True)
        return {}


def _save_cache_data(payload: dict) -> None:
    path = _cache_file_path()
    temp = f"{path}.tmp"
    with open(temp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(temp, path)


def get_global_deleted_history_ids() -> List[str]:
    with _LOCK:
        cache = _load_cache_data()
        ids = cache.get("global_deleted_history_ids", [])
        if isinstance(ids, list):
            return [str(i).strip() for i in ids if str(i).strip()]
    return []


def add_global_deleted_history_id(hid: str) -> None:
    hid = str(hid or "").strip()
    if not hid:
        return
    with _LOCK:
        cache = _load_cache_data()
        ids = cache.get("global_deleted_history_ids", [])
        if not isinstance(ids, list):
            ids = []
        if hid not in ids:
            ids.append(hid)
            cache["global_deleted_history_ids"] = ids
            _save_cache_data(cache)
