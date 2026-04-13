"""
Tests for cache management and cleanup functionality.

Validates that caches have proper TTL and size limits to prevent memory leaks.
"""

import json
import os
import time
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from modules.prompt_cache import (
    cleanup_stale_cache,
    clear_cache_for_dataset,
    get_cached_response,
    save_cached_response,
)


@pytest.fixture
def mock_cache_file(tmp_path):
    """Mock the cache file path for testing."""
    cache_file = tmp_path / "ai_prompt_cache.json"
    
    with patch("modules.prompt_cache._cache_file_path") as mock_path:
        mock_path.return_value = str(cache_file)
        yield cache_file


def test_cleanup_stale_cache_respects_size_limit(mock_cache_file):
    """Test that cleanup removes excess cached responses."""
    # Create cache with 150 responses (exceeds 100 limit)
    cache_data = {
        "dataset_1": {
            "response_cache": {
                f"query_hash_{i}": {
                    "ai_response": f"Response {i}",
                    "last_api_call_ts": time.time() - (i * 100),  # Older timestamps
                }
                for i in range(150)
            }
        }
    }
    
    with open(mock_cache_file, "w") as f:
        json.dump(cache_data, f)
    
    # Run cleanup with max 100 per dataset
    cleanup_stale_cache(max_cache_entries_per_dataset=100, max_age_seconds=604800)
    
    # Verify cache was trimmed
    with open(mock_cache_file, "r") as f:
        cleaned = json.load(f)
    
    response_count = len(cleaned["dataset_1"]["response_cache"])
    assert response_count <= 100, f"Cache should have max 100 entries, got {response_count}"


def test_cleanup_stale_cache_respects_age_limit(mock_cache_file):
    """Test that cleanup removes expired cached responses."""
    now = time.time()
    cache_data = {
        "dataset_1": {
            "response_cache": {
                "recent_query": {
                    "ai_response": "Recent",
                    "last_api_call_ts": now - 1000,  # 1000 seconds old (within 7 days)
                },
                "old_query": {
                    "ai_response": "Old",
                    "last_api_call_ts": now - 700000,  # 700k seconds old (exceeds 7 days)
                },
            }
        }
    }
    
    with open(mock_cache_file, "w") as f:
        json.dump(cache_data, f)
    
    # Run cleanup with 604800 second (7 day) limit
    cleanup_stale_cache(max_cache_entries_per_dataset=100, max_age_seconds=604800)
    
    # Verify old entry was removed
    with open(mock_cache_file, "r") as f:
        cleaned = json.load(f)
    
    response_cache = cleaned["dataset_1"]["response_cache"]
    assert "recent_query" in response_cache, "Recent query should be kept"
    assert "old_query" not in response_cache, "Old query should be removed"


def test_clear_cache_for_dataset_removes_responses(mock_cache_file):
    """Test that clearing dataset cache invalidates all responses."""
    cache_data = {
        "dataset_1": {
            "response_cache": {
                "query_1": {"ai_response": "Response 1"},
                "query_2": {"ai_response": "Response 2"},
            },
            "try_asking_questions": ["Q1", "Q2"],
        },
        "dataset_2": {
            "response_cache": {
                "query_3": {"ai_response": "Response 3"},
            },
        }
    }
    
    with open(mock_cache_file, "w") as f:
        json.dump(cache_data, f)
    
    # Clear dataset_1 responses only
    clear_cache_for_dataset("dataset_1")
    
    # Verify dataset_1 responses cleared but questions kept
    with open(mock_cache_file, "r") as f:
        cleaned = json.load(f)
    
    assert len(cleaned["dataset_1"]["response_cache"]) == 0, "Responses should be cleared"
    assert cleaned["dataset_1"]["try_asking_questions"] == ["Q1", "Q2"], "Questions should be kept"
    assert cleaned["dataset_2"]["response_cache"]["query_3"], "Other datasets should be unaffected"


def test_clear_cache_for_nonexistent_dataset(mock_cache_file):
    """Test that clearing nonexistent dataset doesn't crash."""
    cache_data = {"dataset_1": {"response_cache": {}}}
    
    with open(mock_cache_file, "w") as f:
        json.dump(cache_data, f)
    
    # Should not crash
    clear_cache_for_dataset("nonexistent_dataset")
    
    # Cache should be unchanged
    with open(mock_cache_file, "r") as f:
        result = json.load(f)
    
    assert "dataset_1" in result, "Existing data should be unchanged"


def test_cleanup_preserves_non_response_fields(mock_cache_file):
    """Test that cleanup preserves other dataset fields."""
    cache_data = {
        "dataset_1": {
            "response_cache": {"q1": {"ai_response": "r1"}},
            "try_asking_questions": ["Q1", "Q2"],
            "custom_field": "custom_value",
        }
    }
    
    with open(mock_cache_file, "w") as f:
        json.dump(cache_data, f)
    
    cleanup_stale_cache()
    
    with open(mock_cache_file, "r") as f:
        cleaned = json.load(f)
    
    assert cleaned["dataset_1"]["try_asking_questions"] == ["Q1", "Q2"], "try_asking_questions should be preserved"
    assert cleaned["dataset_1"]["custom_field"] == "custom_value", "Custom fields should be preserved"


def test_cleanup_handles_malformed_cache(mock_cache_file):
    """Test that cleanup handles invalid JSON gracefully."""
    with open(mock_cache_file, "w") as f:
        f.write("not valid json {")
    
    # Should not crash, just load empty cache
    from modules.prompt_cache import _load_cache_data
    result = _load_cache_data()
    
    assert isinstance(result, dict), "Should return empty dict for invalid JSON"
