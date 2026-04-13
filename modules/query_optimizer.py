"""
Query optimization module for intelligent deduplication and compression.

Detects similar queries and reuses cached responses without calling API.
"""

import hashlib
from difflib import SequenceMatcher
from typing import Any


def _normalize_query(query: str) -> str:
    """
    Normalize query for comparison (case-insensitive, remove punctuation).
    
    Examples:
        "What is revenue?" -> "what is revenue"
        "Show me revenue" -> "show me revenue"
    """
    text = str(query or "").strip().lower()
    # Remove common question words and punctuation
    for word in ["what", "show", "tell", "give", "provide", "find", "get", "the"]:
        text = text.replace(f"{word} ", "")
    text = "".join(c for c in text if c.isalnum() or c == " ")
    return " ".join(text.split())[:50]  # Limit to 50 chars after normalization


def _similarity_score(query_a: str, query_b: str) -> float:
    """
    Calculate similarity between two queries (0.0-1.0).
    
    Returns:
        float: Similarity score where 1.0 = identical, 0.0 = completely different
    """
    norm_a = _normalize_query(query_a)
    norm_b = _normalize_query(query_b)
    
    if not norm_a or not norm_b:
        return 0.0
    
    # SequenceMatcher ratio is efficient and good for this use case
    return SequenceMatcher(None, norm_a, norm_b).ratio()


def find_similar_cached_response(
    current_query: str,
    cached_responses: dict[str, Any],
    similarity_threshold: float = 0.75,
) -> tuple[str | None, Any | None]:
    """
    Find a cached response that's similar enough to the current query.
    
    Args:
        current_query: User's current query
        cached_responses: Dict of query_hash -> response payload
        similarity_threshold: Minimum similarity (0-1) to consider a match
    
    Returns:
        Tuple of (similar_query_text, cached_response_payload) or (None, None)
    """
    if not cached_responses:
        return None, None
    
    best_match = None
    best_score = 0.0
    best_response = None
    
    for cached_query_hash, response in cached_responses.items():
        # Attempt to extract original query from cache metadata
        # (if available, otherwise skip)
        cached_query = response.get("_original_query") if isinstance(response, dict) else None
        if not cached_query:
            continue
        
        score = _similarity_score(current_query, cached_query)
        if score > best_score and score >= similarity_threshold:
            best_score = score
            best_match = cached_query
            best_response = response
    
    return best_match, best_response


def compress_dataset_context(
    context: str,
    max_length: int = 800,
) -> str:
    """
    Compress dataset context while preserving key information.
    
    Removes redundant whitespace and truncates gracefully.
    
    Args:
        context: Full dataset context string
        max_length: Maximum output length
    
    Returns:
        Compressed context string
    """
    if not context:
        return ""
    
    # Remove extra whitespace
    compressed = " ".join(context.split())
    
    # If already short enough, return as-is
    if len(compressed) <= max_length:
        return compressed
    
    # Truncate at word boundary
    truncated = compressed[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated.strip() + "..."


def get_query_dedup_key(query: str) -> str:
    """
    Get a deduplication key for similar queries.
    
    Queries with same dedup key are considered equivalent for caching.
    """
    normalized = _normalize_query(query)
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


class QueryCompressionStats:
    """Track compression effectiveness."""
    
    def __init__(self):
        self.queries_compared = 0
        self.similar_found = 0
        self.tokens_saved = 0
    
    def record_similarity_check(self, found: bool):
        self.queries_compared += 1
        if found:
            self.similar_found += 1
    
    def record_compression(self, original_len: int, compressed_len: int):
        # Rough estimate: ~4 chars = 1 token
        self.tokens_saved += (original_len - compressed_len) // 4
    
    def get_stats(self) -> dict:
        """Get compression statistics."""
        hit_rate = (self.similar_found / self.queries_compared * 100) if self.queries_compared > 0 else 0
        return {
            "queries_compared": self.queries_compared,
            "similar_found": self.similar_found,
            "hit_rate_pct": hit_rate,
            "estimated_tokens_saved": self.tokens_saved,
        }
