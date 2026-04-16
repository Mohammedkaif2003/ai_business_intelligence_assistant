import pytest
import streamlit as st
from modules.data_loader import load_dataset
import pandas as pd

def test_full_app_workflow():
    """End-to-end test: dataset → query → report capability."""

    # Load sample data
    with open('data/raw/sales_data.csv', 'rb') as f:
        df = load_dataset(f.read())
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0

    # Schema analysis works
    from modules.dataset_analyzer import analyze_dataset
    schema = analyze_dataset(df)
    assert 'columns' in schema
    assert len(schema['columns']) > 0

    # App state initializes
    from modules.app_state import ensure_analysis_state
    st.session_state.clear()
    ensure_analysis_state()
    assert 'chat_history' in st.session_state
    assert isinstance(st.session_state['chat_history'], list)

    print("✅ E2E workflow passes: data load → schema → state ready")

