import streamlit as st
from datetime import datetime
from uuid import uuid4


MAX_TIMING_HISTORY = 30


def record_timing(metric_name: str, elapsed_ms: float):
    if "perf_session_id" not in st.session_state:
        st.session_state["perf_session_id"] = str(uuid4())
    if "perf_timings" not in st.session_state:
        st.session_state["perf_timings"] = {}
    if "perf_timings_history" not in st.session_state:
        st.session_state["perf_timings_history"] = {}
    if "perf_timing_events" not in st.session_state:
        st.session_state["perf_timing_events"] = []

    elapsed_value = round(float(elapsed_ms), 2)
    st.session_state["perf_timings"][metric_name] = elapsed_value

    metric_history = st.session_state["perf_timings_history"].setdefault(metric_name, [])
    metric_history.append(elapsed_value)
    if len(metric_history) > MAX_TIMING_HISTORY:
        del metric_history[:-MAX_TIMING_HISTORY]

    st.session_state["perf_timing_events"].append(
        {
            "session_id": st.session_state.get("perf_session_id", ""),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "dataset_name": st.session_state.get("dataset_name", ""),
            "metric": metric_name,
            "value_ms": elapsed_value,
        }
    )
    if len(st.session_state["perf_timing_events"]) > MAX_TIMING_HISTORY * 2:
        del st.session_state["perf_timing_events"][:-MAX_TIMING_HISTORY * 2]


def clear_timings():
    st.session_state["perf_timings"] = {}
    st.session_state["perf_timings_history"] = {}
    st.session_state["perf_timing_events"] = []
