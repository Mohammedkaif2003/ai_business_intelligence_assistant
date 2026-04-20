"""
Cache metrics tracker for monitoring response cache effectiveness.

Tracks hit rate, cache size on disk, age of cached entries, etc.
"""

import json
import os
import time
import logging
from typing import Any


_CACHE_STATS_FILE = "data/cache/cache_metrics.json"


def _stats_file_path() -> str:
    """Get path to cache metrics file."""
    project_root = os.path.dirname(os.path.dirname(__file__))
    cache_dir = os.path.join(project_root, "data", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "cache_metrics.json")


def _load_stats() -> dict[str, Any]:
    """Load cache statistics from disk."""
    path = _stats_file_path()
    if not os.path.exists(path):
        return {
            "total_cache_hits": 0,
            "total_cache_misses": 0,
            "total_api_calls": 0,
            "last_updated_ts": time.time(),
            "dataset_stats": {},
        }

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {
            "total_cache_hits": 0,
            "total_cache_misses": 0,
            "total_api_calls": 0,
            "last_updated_ts": time.time(),
            "dataset_stats": {},
        }


def _save_stats(stats: dict[str, Any]) -> None:
    """Save cache statistics to disk."""
    path = _stats_file_path()
    temp_path = f"{path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        os.replace(temp_path, path)
    except Exception as exc:
        logging.getLogger(__name__).exception("failed_saving_cache_metrics")


def record_cache_hit(dataset_key: str, query_hash: str) -> None:
    """Record a cache hit."""
    stats = _load_stats()
    stats["total_cache_hits"] = stats.get("total_cache_hits", 0) + 1
    stats["last_updated_ts"] = time.time()

    if dataset_key not in stats["dataset_stats"]:
        stats["dataset_stats"][dataset_key] = {"hits": 0, "misses": 0}

    stats["dataset_stats"][dataset_key]["hits"] = stats["dataset_stats"][dataset_key].get("hits", 0) + 1
    _save_stats(stats)


def record_cache_miss(dataset_key: str, query_hash: str) -> None:
    """Record a cache miss (triggers API call)."""
    stats = _load_stats()
    stats["total_cache_misses"] = stats.get("total_cache_misses", 0) + 1
    stats["total_api_calls"] = stats.get("total_api_calls", 0) + 1
    stats["last_updated_ts"] = time.time()

    if dataset_key not in stats["dataset_stats"]:
        stats["dataset_stats"][dataset_key] = {"hits": 0, "misses": 0}

    stats["dataset_stats"][dataset_key]["misses"] = stats["dataset_stats"][dataset_key].get("misses", 0) + 1
    _save_stats(stats)


def get_cache_stats() -> dict[str, Any]:
    """Get current cache statistics."""
    stats = _load_stats()
    total_requests = stats.get("total_cache_hits", 0) + stats.get("total_cache_misses", 0)

    if total_requests == 0:
        hit_rate = 0.0
    else:
        hit_rate = stats.get("total_cache_hits", 0) / total_requests

    return {
        "hit_rate": hit_rate,
        "total_hits": stats.get("total_cache_hits", 0),
        "total_misses": stats.get("total_cache_misses", 0),
        "total_api_calls": stats.get("total_api_calls", 0),
        "last_updated_ts": stats.get("last_updated_ts", time.time()),
        "dataset_stats": stats.get("dataset_stats", {}),
    }


def reset_stats() -> None:
    """Clear all cache statistics."""
    _save_stats(
        {
            "total_cache_hits": 0,
            "total_cache_misses": 0,
            "total_api_calls": 0,
            "last_updated_ts": time.time(),
            "dataset_stats": {},
        }
    )
