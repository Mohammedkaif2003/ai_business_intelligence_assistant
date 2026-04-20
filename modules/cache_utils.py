import logging

def safe_clear_cache(dataset_key: str | None = None) -> bool:
    """Safely clear cache.

    Avoid clearing the global Streamlit cache unless a specific dataset
    key is provided. This prevents wide-ranging side effects from
    delete operations.

    Returns True if a clear was attempted, False otherwise.
    """
    try:
        import streamlit as st
    except Exception as exc:
        logging.getLogger(__name__).debug("streamlit_unavailable_for_cache_clear")
        return False

    if not dataset_key:
        logging.getLogger(__name__).info("skip_global_cache_clear_no_dataset")
        return False

    try:
        # No fine-grained invalidation API for st.cache_data; fall back
        # to a global clear when a dataset key is explicitly provided.
        st.cache_data.clear()
        logging.getLogger(__name__).info("cleared_cache_for_dataset", extra={"dataset_key": dataset_key})
        return True
    except Exception as exc:
        logging.getLogger(__name__).exception("failed_clearing_cache_for_dataset", extra={"dataset_key": dataset_key})
        return False
