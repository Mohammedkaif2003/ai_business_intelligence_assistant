import modules.app_perf as app_perf


class _DummyStreamlit:
    def __init__(self):
        self.session_state = {}


def test_record_timing_stores_latest_and_history(monkeypatch):
    dummy = _DummyStreamlit()
    dummy.session_state = {"dataset_name": "sales.csv"}
    monkeypatch.setattr(app_perf, "st", dummy)

    app_perf.record_timing("chat_execution_ms", 10.123)
    app_perf.record_timing("chat_execution_ms", 20.456)

    assert dummy.session_state["perf_timings"]["chat_execution_ms"] == 20.46
    assert dummy.session_state["perf_timings_history"]["chat_execution_ms"] == [10.12, 20.46]
    assert len(dummy.session_state["perf_timing_events"]) == 2
    assert "perf_session_id" in dummy.session_state
    assert dummy.session_state["perf_timing_events"][0]["session_id"] == dummy.session_state["perf_session_id"]
    assert dummy.session_state["perf_timing_events"][0]["dataset_name"] == "sales.csv"
    assert dummy.session_state["perf_timing_events"][0]["metric"] == "chat_execution_ms"
    assert dummy.session_state["perf_timing_events"][0]["timestamp"]


def test_record_timing_trims_history_to_max(monkeypatch):
    dummy = _DummyStreamlit()
    monkeypatch.setattr(app_perf, "st", dummy)

    for index in range(app_perf.MAX_TIMING_HISTORY + 5):
        app_perf.record_timing("upload_load_ms", float(index))

    history = dummy.session_state["perf_timings_history"]["upload_load_ms"]
    assert len(history) == app_perf.MAX_TIMING_HISTORY
    assert history[0] == 5.0


def test_clear_timings_resets_maps(monkeypatch):
    dummy = _DummyStreamlit()
    dummy.session_state = {
        "perf_timings": {"x": 1.0},
        "perf_timings_history": {"x": [1.0]},
        "perf_timing_events": [{"metric": "x", "value_ms": 1.0}],
    }
    monkeypatch.setattr(app_perf, "st", dummy)

    app_perf.clear_timings()

    assert dummy.session_state["perf_timings"] == {}
    assert dummy.session_state["perf_timings_history"] == {}
    assert dummy.session_state["perf_timing_events"] == []
