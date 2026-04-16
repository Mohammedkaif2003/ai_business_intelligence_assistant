import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import modules.app_state as app_state


class _DummyStreamlit:
    def __init__(self):
        self.session_state = {}


def test_delete_chat_history_everywhere_cleans_cached_states(monkeypatch):
    dummy = _DummyStreamlit()
    # Prepare an in-memory chat history entry that should be removed
    entry = {
        "history_id": "hid-123",
        "cloud_history_id": "",
        "dataset_key": "test.csv",
        "created_at": "2026-04-16T10:00:00+00:00",
        "query": "What is total spend?",
        "ai_response": "Total spend is $1000",
    }

    dummy.session_state = {
        "chat_history": [entry.copy()],
    }

    monkeypatch.setattr(app_state, "st", dummy)

    # Mock cached dataset states to include the same entry under a different dataset key
    cached_states = {
        "ds_test": {"chat_history": [entry.copy()]}
    }

    called = {}

    def fake_get_all_cached_dataset_states():
        return cached_states

    def fake_save_cached_dataset_state(key, state):
        called['saved'] = (key, state)
        # Simulate successful save by updating the cached_states dict
        cached_states[key] = state
        return state

    monkeypatch.setattr(app_state, "get_all_cached_dataset_states", fake_get_all_cached_dataset_states)
    monkeypatch.setattr(app_state, "save_cached_dataset_state", fake_save_cached_dataset_state)

    # Execute deletion
    result = app_state.delete_chat_history_everywhere("hid-123")

    assert result is True
    # Ensure in-memory history cleared
    assert len(dummy.session_state.get("chat_history", [])) == 0
    # Ensure cached state was updated and saved
    assert "saved" in called
    saved_key, saved_state = called["saved"]
    assert saved_key == "ds_test"
    assert isinstance(saved_state.get("chat_history", []), list)
    assert len(saved_state.get("chat_history", [])) == 0
