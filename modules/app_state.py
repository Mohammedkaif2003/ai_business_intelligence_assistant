import pandas as pd
import streamlit as st


def ensure_analysis_state():
    defaults = {
        "chat_history": [],
        "messages": [],
        "analysis_history": [],
        "result_history": [],
        "result_history_details": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, list) else value


def reset_analysis_state():
    for key in ("chat_history", "messages", "analysis_history", "result_history", "result_history_details"):
        st.session_state[key] = []


def append_message_pair(query: str, result):
    st.session_state.messages.append({"role": "user", "content": query})
    if isinstance(result, pd.DataFrame):
        preview = result.head(5).to_string(index=False)
        st.session_state.messages.append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
    elif isinstance(result, pd.Series):
        preview = result.head(5).to_string()
        st.session_state.messages.append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
    else:
        st.session_state.messages.append({"role": "assistant", "content": str(result)})


def store_analysis_outputs(query, result, chart_data, chart_figs, code, report_insight, ai_response, summary_list, suggestions, query_rejected, is_axes_result):
    st.session_state.analysis_result = result
    st.session_state.last_result = result
    st.session_state.last_query = query
    st.session_state.result_history.append(result)
    st.session_state.analysis_query = query

    if chart_data is not None:
        st.session_state.chart_data = chart_data
        st.session_state.report_charts = chart_figs

    if not query_rejected:
        st.session_state.analysis_history.append({
            "query": query,
            "result": result if not is_axes_result else None,
            "code": code,
            "insight": report_insight,
            "ai_response": ai_response,
            "charts": chart_figs,
            "summary": summary_list,
        })

    st.session_state.chat_history.append({
        "query": query,
        "result": result,
        "code": code if not query_rejected else "",
        "chart_data": chart_data if not query_rejected else None,
        "insight": report_insight if not query_rejected else "",
        "summary": summary_list if not query_rejected else [],
        "charts": chart_figs if not query_rejected else [],
        "ai_response": ai_response,
        "suggestions": suggestions if (not query_rejected and suggestions) else "",
        "query_rejected": query_rejected,
    })
