"""
Tests for chat response field extraction and handling.

Validates that confidence and source_columns fields are properly extracted
from chat_handler responses and available for UI rendering.
"""

import time
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from modules.chat_handler import chat_handler


@pytest.fixture
def sample_dataframe():
    """Create a sample dataframe for testing."""
    return pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "revenue": [100, 150, 200],
        "region": ["North", "South", "North"],
    })


@pytest.fixture
def sample_schema():
    """Create a sample schema."""
    return {
        "numeric_columns": ["revenue"],
        "categorical_columns": ["region"],
        "datetime_columns": ["date"],
    }


def test_chat_handler_returns_confidence_field(sample_dataframe, sample_schema):
    """Test that chat_handler response includes confidence field."""
    with patch("modules.chat_handler.call_groq_json") as mock_groq:
        mock_groq.return_value = {
            "ok": True,
            "content": """{
                "intent": "analysis",
                "query_rejected": false,
                "confidence": 0.85,
                "source_columns": ["revenue", "region"],
                "response": "The data shows revenue increasing over time",
                "summary": ["Revenue increased by 100%"],
                "follow_ups": [],
                "rephrases": []
            }"""
        }
        
        result = chat_handler(
            query="What is the revenue?",
            df=sample_dataframe,
            schema=sample_schema,
            dataset_name="test_dataset",
            logger=None,
            last_api_call_ts=time.time(),
            min_call_interval_seconds=1.0,
        )
        
        assert "confidence" in result, "Response must include 'confidence' field"
        assert isinstance(result["confidence"], float), "Confidence must be a float"
        assert 0.0 <= result["confidence"] <= 1.0, "Confidence must be between 0 and 1"


def test_chat_handler_returns_source_columns_field(sample_dataframe, sample_schema):
    """Test that chat_handler response includes source_columns field."""
    with patch("modules.chat_handler.call_groq_json") as mock_groq:
        mock_groq.return_value = {
            "ok": True,
            "content": """{
                "intent": "analysis",
                "query_rejected": false,
                "confidence": 0.90,
                "source_columns": ["revenue", "region", "date"],
                "response": "Analysis complete",
                "summary": [],
                "follow_ups": [],
                "rephrases": []
            }"""
        }
        
        result = chat_handler(
            query="Analyze the dataset",
            df=sample_dataframe,
            schema=sample_schema,
            dataset_name="test_dataset",
            logger=None,
            last_api_call_ts=time.time(),
            min_call_interval_seconds=1.0,
        )
        
        assert "source_columns" in result, "Response must include 'source_columns' field"
        assert isinstance(result["source_columns"], list), "source_columns must be a list"


def test_chat_handler_confidence_defaults_to_zero_on_parse_error(sample_dataframe, sample_schema):
    """Test that confidence defaults to 0.3 if JSON parsing fails."""
    with patch("modules.chat_handler.call_groq_json") as mock_groq:
        mock_groq.return_value = {
            "ok": True,
            "content": "Invalid JSON that cannot be parsed"
        }
        
        result = chat_handler(
            query="Test query",
            df=sample_dataframe,
            schema=sample_schema,
            dataset_name="test_dataset",
            logger=None,
            last_api_call_ts=time.time(),
            min_call_interval_seconds=1.0,
        )
        
        # Default confidence on parse error is 0.3 (partial fallback)
        assert result["confidence"] == 0.3, "Default confidence should be 0.3 on parse error"


def test_chat_handler_source_columns_defaults_to_empty_list(sample_dataframe, sample_schema):
    """Test that source_columns defaults to empty list on parse error."""
    with patch("modules.chat_handler.call_groq_json") as mock_groq:
        mock_groq.return_value = {
            "ok": True,
            "content": "Invalid JSON"
        }
        
        result = chat_handler(
            query="Test query",
            df=sample_dataframe,
            schema=sample_schema,
            dataset_name="test_dataset",
            logger=None,
            last_api_call_ts=time.time(),
            min_call_interval_seconds=1.0,
        )
        
        assert isinstance(result["source_columns"], list), "source_columns should be a list"
        assert len(result["source_columns"]) == 0, "source_columns should be empty on error"


def test_chat_handler_clamps_confidence_to_0_to_1_range(sample_dataframe, sample_schema):
    """Test that confidence is clamped to [0, 1] range."""
    with patch("modules.chat_handler.call_groq_json") as mock_groq:
        mock_groq.return_value = {
            "ok": True,
            "content": """{
                "intent": "analysis",
                "query_rejected": false,
                "confidence": 1.5,
                "source_columns": [],
                "response": "Test",
                "summary": [],
                "follow_ups": [],
                "rephrases": []
            }"""
        }
        
        result = chat_handler(
            query="Test",
            df=sample_dataframe,
            schema=sample_schema,
            dataset_name="test_dataset",
            logger=None,
            last_api_call_ts=time.time(),
            min_call_interval_seconds=1.0,
        )
        
        # Should be clamped to 1.0
        assert result["confidence"] <= 1.0, "Confidence should be clamped to max 1.0"


def test_chat_handler_confidence_negative_clamped(sample_dataframe, sample_schema):
    """Test that negative confidence is clamped to 0."""
    with patch("modules.chat_handler.call_groq_json") as mock_groq:
        mock_groq.return_value = {
            "ok": True,
            "content": """{
                "intent": "analysis",
                "query_rejected": false,
                "confidence": -0.5,
                "source_columns": [],
                "response": "Test",
                "summary": [],
                "follow_ups": [],
                "rephrases": []
            }"""
        }
        
        result = chat_handler(
            query="Test",
            df=sample_dataframe,
            schema=sample_schema,
            dataset_name="test_dataset",
            logger=None,
            last_api_call_ts=time.time(),
            min_call_interval_seconds=1.0,
        )
        
        # Should be clamped to 0.0
        assert result["confidence"] >= 0.0, "Confidence should be clamped to min 0.0"


def test_chat_handler_source_columns_cleaned(sample_dataframe, sample_schema):
    """Test that source_columns are cleaned of empty strings."""
    with patch("modules.chat_handler.call_groq_json") as mock_groq:
        mock_groq.return_value = {
            "ok": True,
            "content": """{
                "intent": "analysis",
                "query_rejected": false,
                "confidence": 0.75,
                "source_columns": ["revenue", "", "region", null],
                "response": "Test",
                "summary": [],
                "follow_ups": [],
                "rephrases": []
            }"""
        }
        
        result = chat_handler(
            query="Test",
            df=sample_dataframe,
            schema=sample_schema,
            dataset_name="test_dataset",
            logger=None,
            last_api_call_ts=time.time(),
            min_call_interval_seconds=1.0,
        )
        
        source_cols = result["source_columns"]
        # Empty strings and null values should be filtered
        assert all(col for col in source_cols), "source_columns should not contain empty strings"


def test_chat_handler_normalizes_string_summary_field(sample_dataframe, sample_schema):
    """String summary payload should not be rendered as character-by-character bullets."""
    with patch("modules.chat_handler.call_groq_json") as mock_groq:
        mock_groq.return_value = {
            "ok": True,
            "content": """{
                "intent": "analysis",
                "query_rejected": false,
                "confidence": 1.0,
                "source_columns": ["Quantity"],
                "response": "Sorted top 10 by Quantity.",
                "summary": "Top 10 by Quantity",
                "follow_ups": [],
                "rephrases": []
            }""",
        }

        result = chat_handler(
            query="Show top 10 by quantity",
            df=sample_dataframe,
            schema=sample_schema,
            dataset_name="test_dataset",
            logger=None,
            last_api_call_ts=time.time(),
            min_call_interval_seconds=1.0,
        )

        assert result["summary_list"] == ["Top 10 by Quantity"]


def test_chat_handler_normalizes_string_structured_sections(sample_dataframe, sample_schema):
    """String structured fields should become one bullet item, not per-character bullets."""
    with patch("modules.chat_handler.call_groq_json") as mock_groq:
        mock_groq.return_value = {
            "ok": True,
            "content": """{
                "intent": "analysis",
                "query_rejected": false,
                "confidence": 0.9,
                "source_columns": ["revenue"],
                "response": "Revenue is increasing.",
                "summary": [],
                "executive_insight": "Revenue increased over the selected period",
                "key_findings": "North region contributes the most",
                "follow_ups": [],
                "rephrases": []
            }""",
        }

        result = chat_handler(
            query="Summarize revenue trend",
            df=sample_dataframe,
            schema=sample_schema,
            dataset_name="test_dataset",
            logger=None,
            last_api_call_ts=time.time(),
            min_call_interval_seconds=1.0,
        )

        structured = result.get("structured_response", {})
        assert structured.get("EXECUTIVE INSIGHT") == ["Revenue increased over the selected period"]
        assert structured.get("KEY FINDINGS") == ["North region contributes the most"]
