import pandas as pd

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
