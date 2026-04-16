import pandas as pd

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import modules.app_state as app_state


class _DummyStreamlit:
    def __init__(self):
        self.session_state = {}


def test_ensure_analysis_state_initializes_defaults(monkeypatch):
    dummy = _DummyStreamlit()
    monkeypatch.setattr(app_state, "st", dummy)

    app_state.ensure_analysis_state()

    assert "chat_history" in dummy.session_state
    assert "messages" in dummy.session_state
    assert "analysis_history" in dummy.session_state
    assert "result_history" in dummy.session_state
    assert "result_history_details" in dummy.session_state


def test_persist_analysis_cycle_writes_expected_state(monkeypatch):
    dummy = _DummyStreamlit()
    dummy.session_state = {
        "messages": [],
        "analysis_history": [],
        "chat_history": [],
        "result_history": [],
        "result_history_details": [],
    }
    monkeypatch.setattr(app_state, "st", dummy)

    result_df = pd.DataFrame({"Revenue": [100, 120]})
    app_state.persist_analysis_cycle(
        query="total revenue",
        result=result_df,
        chart_data=result_df,
        chart_figs=[],
        code="result = df",
        insight="Revenue increased",
        ai_response="Revenue increased",
        summary_list=["Revenue trend is up"],
        suggestions="1. Compare by region?",
        query_rejected=False,
        is_axes_result=False,
        intent="analysis",
        rephrases=[],
        result_history_entry={"query": "total revenue", "result_type": "dataframe"},
    )

    assert len(dummy.session_state["messages"]) == 2
    assert len(dummy.session_state["analysis_history"]) == 1
    assert len(dummy.session_state["chat_history"]) == 1
    assert len(dummy.session_state["result_history"]) == 1
    assert len(dummy.session_state["result_history_details"]) == 1


def test_get_sidebar_history_entries_deduplicates_cloud_and_local(monkeypatch):
    dummy = _DummyStreamlit()
    dummy.session_state = {
        "chat_history": [
            {
                "history_id": "local-123",
                "cloud_history_id": "cloud-abc",
                "dataset_key": "sales_data.csv",
                "created_at": "2026-04-15T10:00:00+00:00",
                "query": "Show top 10 by Quantity",
                "ai_response": "Top 10 generated",
            }
        ],
        "supabase_user_id": "user-1",
        "supabase_access_token": "token-1",
    }
    monkeypatch.setattr(app_state, "st", dummy)

    monkeypatch.setattr(
        app_state,
        "fetch_cloud_chat_history",
        lambda user_id, access_token, dataset_key=None, limit=200: [
            {
                "id": "cloud-abc",
                "dataset_key": "sales_data.csv",
                "created_at": "2026-04-15T10:00:00+00:00",
                "query": "Show top 10 by Quantity",
                "ai_response": "Top 10 generated",
                "insight": "",
                "summary": [],
                "source_columns": ["Quantity"],
            }
        ],
    )

    entries = app_state.get_sidebar_history_entries(scope="all", limit=200)

    assert len(entries) == 1
    assert str(entries[0].get("cloud_history_id", "")) == "cloud-abc"


def test_get_sidebar_history_entries_uses_cloud_dataset_label(monkeypatch):
    dummy = _DummyStreamlit()
    dummy.session_state = {
        "chat_history": [],
        "supabase_user_id": "user-1",
        "supabase_access_token": "token-1",
    }
    monkeypatch.setattr(app_state, "st", dummy)

    monkeypatch.setattr(
        app_state,
        "fetch_cloud_chat_history",
        lambda user_id, access_token, dataset_key=None, limit=200: [
            {
                "id": "cloud-1",
                "dataset_key": "d65eb36392b637c914962e82a568cba28929daebe71f1059f1e5000a617730b3",
                "created_at": "2026-04-15T10:30:00+00:00",
                "query": "Show top 10 by Quantity",
                "ai_response": "Top 10 generated",
                "insight": "",
                "summary": [],
                "source_columns": ["Quantity"],
                "metadata": {"dataset_label": "sales_data.csv"},
            }
        ],
    )

    entries = app_state.get_sidebar_history_entries(scope="all", limit=200)

    assert len(entries) == 1
    assert entries[0].get("dataset_label") == "sales_data.csv"
