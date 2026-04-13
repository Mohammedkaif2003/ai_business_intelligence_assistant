import pandas as pd
import streamlit as st
import time

from modules.prompt_cache import get_cached_dataset_state, save_cached_dataset_state
from modules.supabase_service import fetch_cloud_chat_history, save_cloud_chat_history


def ensure_analysis_state():
    defaults = {
        "chat_history": [],
        "messages": [],
        "analysis_history": [],
        "result_history": [],
        "result_history_details": [],
        "recent_activity": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, list) else value


def _active_dataset_cache_key() -> str:
    return str(st.session_state.get("active_dataset_cache_key") or st.session_state.get("active_dataset_key") or st.session_state.get("dataset_name") or "").strip()


def _history_entry_id(entry: dict) -> str:
    if not isinstance(entry, dict):
        return ""
    return str(entry.get("history_id") or entry.get("cloud_history_id") or "").strip()


def _ensure_chat_history_ids(entries: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        normalized_entry = dict(entry)
        history_id = _history_entry_id(normalized_entry)
        if not history_id:
            history_id = str(time.time_ns())
        normalized_entry["history_id"] = history_id
        normalized.append(normalized_entry)
    return normalized


def restore_persisted_analysis_state() -> None:
    dataset_cache_key = _active_dataset_cache_key()
    if not dataset_cache_key:
        return

    cached_state = get_cached_dataset_state(dataset_cache_key)
    if not isinstance(cached_state, dict):
        return

    for key in ("chat_history", "analysis_history", "result_history", "result_history_details", "recent_activity", "messages"):
        value = cached_state.get(key)
        if isinstance(value, list):
            st.session_state[key] = value.copy()

    if isinstance(st.session_state.get("chat_history"), list):
        st.session_state["chat_history"] = _ensure_chat_history_ids(st.session_state["chat_history"])


def _cloud_row_to_chat_entry(row: dict) -> dict:
    row_id = str(row.get("id", "") or "").strip()
    summary_value = row.get("summary", []) if isinstance(row, dict) else []
    if not isinstance(summary_value, list):
        summary_value = []

    source_columns_value = row.get("source_columns", []) if isinstance(row, dict) else []
    if not isinstance(source_columns_value, list):
        source_columns_value = []

    return {
        "history_id": row_id or str(time.time_ns()),
        "cloud_history_id": row_id or "",
        "created_at": row.get("created_at"),
        "query": str(row.get("query", "") or ""),
        "result": str(row.get("ai_response", "") or row.get("insight", "") or ""),
        "code": "",
        "chart_data": None,
        "insight": str(row.get("insight", "") or ""),
        "summary": summary_value,
        "charts": [],
        "ai_response": str(row.get("ai_response", "") or ""),
        "suggestions": "",
        "query_rejected": False,
        "confidence": row.get("confidence"),
        "source_columns": source_columns_value,
        "intent": row.get("intent"),
        "rephrases": [],
    }


def restore_cloud_analysis_state() -> bool:
    user_id = str(st.session_state.get("supabase_user_id", "") or "").strip()
    access_token = str(st.session_state.get("supabase_access_token", "") or "").strip()
    if not user_id or not access_token:
        return False

    dataset_key = _active_dataset_cache_key()
    rows = fetch_cloud_chat_history(user_id, access_token, dataset_key=dataset_key, limit=100)
    if not rows:
        return False

    current_history = _ensure_chat_history_ids(list(st.session_state.get("chat_history", [])))
    existing_ids = {
        _history_entry_id(entry)
        for entry in current_history
        if _history_entry_id(entry)
    }
    cloud_entries = [_cloud_row_to_chat_entry(row) for row in rows if str(row.get("id", "") or "").strip() not in existing_ids]

    if cloud_entries:
        st.session_state["chat_history"] = _ensure_chat_history_ids(current_history + cloud_entries)

        if not st.session_state.get("messages"):
            st.session_state["messages"] = []
        for entry in cloud_entries:
            query = str(entry.get("query", "") or "").strip()
            answer = str(entry.get("ai_response", "") or entry.get("insight", "") or "").strip()
            if query:
                st.session_state["messages"].append({"role": "user", "content": query})
            if answer:
                st.session_state["messages"].append({"role": "assistant", "content": answer})

        if not st.session_state.get("analysis_history"):
            st.session_state["analysis_history"] = []
        for entry in cloud_entries:
            st.session_state["analysis_history"].append(
                {
                    "query": str(entry.get("query", "") or ""),
                    "result": str(entry.get("ai_response", "") or entry.get("insight", "") or ""),
                    "code": "",
                    "insight": str(entry.get("insight", "") or ""),
                    "ai_response": str(entry.get("ai_response", "") or ""),
                    "charts": [],
                    "summary": entry.get("summary", []) if isinstance(entry.get("summary", []), list) else [],
                    "intent": entry.get("intent"),
                    "confidence": entry.get("confidence"),
                    "source_columns": entry.get("source_columns", []) if isinstance(entry.get("source_columns", []), list) else [],
                }
            )

        if not st.session_state.get("result_history"):
            st.session_state["result_history"] = []
        st.session_state["result_history"].extend([str(entry.get("ai_response", "") or entry.get("insight", "") or "") for entry in cloud_entries])

        if not st.session_state.get("result_history_details"):
            st.session_state["result_history_details"] = []
        st.session_state["result_history_details"].extend(
            [{"query": str(entry.get("query", "") or ""), "history_id": _history_entry_id(entry)} for entry in cloud_entries]
        )

    return True


def delete_chat_history_entry(history_id: str) -> bool:
    history_id = str(history_id or "").strip()
    if not history_id:
        return False

    chat_history = st.session_state.get("chat_history", [])
    remaining_history = [entry for entry in chat_history if _history_entry_id(entry) != history_id]
    if len(remaining_history) == len(chat_history):
        return False

    st.session_state["chat_history"] = remaining_history

    st.session_state["analysis_history"] = [
        {
            "query": str(entry.get("query", "") or ""),
            "result": entry.get("result"),
            "code": entry.get("code", ""),
            "insight": entry.get("insight", ""),
            "ai_response": entry.get("ai_response", ""),
            "charts": entry.get("charts", []) if isinstance(entry.get("charts", []), list) else [],
            "summary": entry.get("summary", []) if isinstance(entry.get("summary", []), list) else [],
            "intent": entry.get("intent"),
            "confidence": entry.get("confidence"),
            "source_columns": entry.get("source_columns", []) if isinstance(entry.get("source_columns", []), list) else [],
        }
        for entry in remaining_history
    ]

    st.session_state["result_history"] = [entry.get("result") for entry in remaining_history]
    st.session_state["result_history_details"] = [
        {"query": entry.get("query", ""), "history_id": _history_entry_id(entry)}
        for entry in remaining_history
    ]
    messages: list[dict[str, str]] = []
    for entry in remaining_history:
        query = str(entry.get("query", "") or "").strip()
        answer = str(entry.get("ai_response", "") or entry.get("insight", "") or "").strip()
        if query:
            messages.append({"role": "user", "content": query})
        if answer:
            messages.append({"role": "assistant", "content": answer})
    st.session_state["messages"] = messages

    selected_history_id = str(st.session_state.get("selected_chat_history_id", "") or "").strip()
    if selected_history_id == history_id:
        st.session_state["selected_chat_history_id"] = remaining_history[-1]["history_id"] if remaining_history else ""

    persist_dataset_state()
    return True


def persist_dataset_state() -> None:
    dataset_cache_key = _active_dataset_cache_key()
    if not dataset_cache_key:
        return

    save_cached_dataset_state(
        dataset_cache_key,
        {
            "chat_history": st.session_state.get("chat_history", []),
            "analysis_history": st.session_state.get("analysis_history", []),
            "result_history": st.session_state.get("result_history", []),
            "result_history_details": st.session_state.get("result_history_details", []),
            "recent_activity": st.session_state.get("recent_activity", []),
            "messages": st.session_state.get("messages", []),
        },
    )


def reset_analysis_state():
    for key in ("chat_history", "messages", "analysis_history", "result_history", "result_history_details", "recent_activity"):
        st.session_state[key] = []

    persist_dataset_state()


def add_recent_activity(kind: str, description: str, limit: int = 8):
    if "recent_activity" not in st.session_state:
        st.session_state["recent_activity"] = []

    st.session_state["recent_activity"].insert(0, {"kind": kind, "description": description})
    st.session_state["recent_activity"] = st.session_state["recent_activity"][:limit]


def get_recent_activity():
    return st.session_state.get("recent_activity", [])


def append_message_pair(query: str, result):
    st.session_state["messages"].append({"role": "user", "content": query})
    if isinstance(result, pd.DataFrame):
        preview = result.head(5).to_string(index=False)
        st.session_state["messages"].append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
    elif isinstance(result, pd.Series):
        preview = result.head(5).to_string()
        st.session_state["messages"].append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
    else:
        st.session_state["messages"].append({"role": "assistant", "content": str(result)})


def store_analysis_outputs(query, result, chart_data, chart_figs, code, report_insight, ai_response, summary_list, suggestions, query_rejected, is_axes_result):
    history_id = str(time.time_ns())
    created_at = pd.Timestamp.now("UTC").isoformat()
    st.session_state["analysis_result"] = result
    st.session_state["last_result"] = result
    st.session_state["last_query"] = query
    st.session_state["result_history"].append(result)
    st.session_state["analysis_query"] = query

    if chart_data is not None:
        st.session_state["chart_data"] = chart_data
        st.session_state["report_charts"] = chart_figs

    if not query_rejected:
        st.session_state["analysis_history"].append({
            "query": query,
            "result": result if not is_axes_result else None,
            "code": code,
            "insight": report_insight,
            "ai_response": ai_response,
            "charts": chart_figs,
            "summary": summary_list,
        })

    st.session_state["chat_history"].append({
        "history_id": history_id,
        "created_at": created_at,
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

    persist_dataset_state()


def persist_analysis_cycle(
    *,
    query: str,
    result,
    chart_data,
    chart_figs,
    code: str,
    insight: str,
    ai_response: str,
    summary_list: list,
    suggestions: str,
    query_rejected: bool,
    is_axes_result: bool,
    intent: str | None,
    rephrases: list,
    result_history_entry: dict,
    confidence: float | None = None,
    source_columns: list[str] | None = None,
):
    history_id = str(time.time_ns())
    created_at = pd.Timestamp.now("UTC").isoformat()
    st.session_state["messages"].append({"role": "user", "content": query})
    if isinstance(result, pd.DataFrame):
        preview = result.head(5).to_string(index=False)
        st.session_state["messages"].append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
    elif isinstance(result, pd.Series):
        preview = result.head(5).to_string()
        st.session_state["messages"].append({"role": "assistant", "content": f"Here are the top results:\n\n{preview}"})
    else:
        st.session_state["messages"].append({"role": "assistant", "content": str(result)})

    st.session_state["analysis_result"] = result
    st.session_state["last_result"] = result
    st.session_state["last_query"] = query

    if "result_history" not in st.session_state:
        st.session_state["result_history"] = []
    if "result_history_details" not in st.session_state:
        st.session_state["result_history_details"] = []

    st.session_state["result_history"].append(result)
    st.session_state["result_history_details"].append(result_history_entry)
    st.session_state["analysis_query"] = query

    if chart_data is not None:
        st.session_state["chart_data"] = chart_data
        st.session_state["report_charts"] = chart_figs

    report_insight = insight if insight else (ai_response if ai_response else "Analysis completed.")
    if "<Axes:" in str(report_insight) or "<AxesSubplot" in str(report_insight):
        report_insight = ai_response if ai_response else "Analysis completed - see AI response for details."

    if not query_rejected:
        st.session_state["analysis_history"].append(
            {
                "query": query,
                "result": result if not is_axes_result else None,
                "code": code,
                "insight": report_insight,
                "ai_response": ai_response,
                "charts": chart_figs,
                "summary": summary_list,
                "intent": intent,
                "confidence": confidence,
                "source_columns": source_columns or [],
            }
        )

    st.session_state["chat_history"].append(
        {
            "history_id": history_id,
            "created_at": created_at,
            "query": query,
            "result": result,
            "code": code if not query_rejected else "",
            "chart_data": chart_data if not query_rejected else None,
            "insight": insight if not query_rejected else "",
            "summary": summary_list if not query_rejected else [],
            "charts": chart_figs if not query_rejected else [],
            "ai_response": ai_response,
            "suggestions": suggestions if (not query_rejected and suggestions) else "",
            "query_rejected": query_rejected,
            "confidence": confidence,
            "source_columns": source_columns or [],
            "intent": intent,
            "rephrases": rephrases,
        }
    )

    user_id = str(st.session_state.get("supabase_user_id", "") or "").strip()
    access_token = str(st.session_state.get("supabase_access_token", "") or "").strip()
    if user_id:
        latest_entry = st.session_state["chat_history"][-1]
        ok, cloud_history_id = save_cloud_chat_history(user_id, access_token, _active_dataset_cache_key(), latest_entry)
        if ok and cloud_history_id:
            latest_entry["cloud_history_id"] = cloud_history_id

    persist_dataset_state()
