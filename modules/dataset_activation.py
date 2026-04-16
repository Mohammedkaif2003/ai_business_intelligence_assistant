import pandas as pd
import streamlit as st

from modules.dataset_analyzer import analyze_dataset


def activate_dataset(dataset_key: str, dataframe: pd.DataFrame, dataset_fingerprint: str | None = None) -> bool:
    if dataframe is None or dataframe.empty or len(dataframe.columns) == 0:
        return False

    current_key = st.session_state.get("active_dataset_key")
    next_cache_key = dataset_fingerprint or dataset_key
    current_cache_key = st.session_state.get("active_dataset_cache_key") or current_key
    if current_key == dataset_key and current_cache_key == next_cache_key and st.session_state.get("df") is not None:
        return False

    st.session_state["df"] = dataframe
    st.session_state["active_dataset_key"] = dataset_key
    st.session_state["active_dataset_cache_key"] = next_cache_key
    st.session_state["dataset_name"] = dataset_key
    st.session_state["schema"] = analyze_dataset(dataframe)
    return True
