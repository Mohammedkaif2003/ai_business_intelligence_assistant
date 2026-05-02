import re
import html

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.text_utils import clean_text, structure_response
from modules.query_utils import extract_follow_up_questions
from modules.app_state import ensure_analysis_state
from ui_components import (
    render_assistant_bubble,
    render_chart_card,
    render_insight_card,
    render_structured_response,
    render_table_panel,
    render_user_bubble,
)


def init_analysis_state():
    ensure_analysis_state()


def _format_dataset_label(dataset_name: str | None) -> str:
    if not dataset_name:
        return "this dataset"

    dataset_label = re.sub(r"\.[^.]+$", "", str(dataset_name))
    dataset_label = re.sub(r"[_-]+", " ", dataset_label).strip()
    return dataset_label.title() if dataset_label else "this dataset"


def _generate_quick_prompts(
    df: pd.DataFrame,
    schema: dict | None = None,
    dataset_name: str | None = None,
) -> list[str]:
    schema = schema or {}
    numeric_cols = schema.get("numeric_columns", []) or df.select_dtypes(include="number").columns.tolist()
    categorical_cols = schema.get("categorical_columns", []) or df.select_dtypes(exclude="number").columns.tolist()
    datetime_cols = schema.get("datetime_columns", [])
    dataset_label = _format_dataset_label(dataset_name)

    prompts: list[str] = []

    if categorical_cols and numeric_cols:
        prompts.append(f"In {dataset_label}, what are the top 5 {categorical_cols[0]} by {numeric_cols[0]}?")

    if datetime_cols and numeric_cols:
        prompts.append(f"In {dataset_label}, what is the {numeric_cols[0]} trend over time?")
    elif "Date" in df.columns and numeric_cols:
        prompts.append(f"In {dataset_label}, what is the {numeric_cols[0]} trend over time?")
    elif len(numeric_cols) >= 2:
        prompts.append(f"In {dataset_label}, compare {numeric_cols[0]} with {numeric_cols[1]}.")

    if len(categorical_cols) >= 2 and numeric_cols:
        prompts.append(f"In {dataset_label}, show {numeric_cols[0]} by {categorical_cols[1]}.")
    elif categorical_cols and numeric_cols:
        prompts.append(f"In {dataset_label}, show {numeric_cols[0]} by {categorical_cols[0]}.")

    if not prompts and numeric_cols:
        prompts.extend([
            f"In {dataset_label}, what is the average {numeric_cols[0]}?",
            f"In {dataset_label}, what is the highest {numeric_cols[0]}?",
            f"In {dataset_label}, summarize {numeric_cols[0]}.",
        ])

    if not prompts:
        columns = schema.get("column_names", [])[:3] or df.columns.tolist()[:3]
        prompts.extend([
            f"In {dataset_label}, summarize {columns[0]}",
            f"In {dataset_label}, show records by {columns[0]}",
            f"Give an overview of {dataset_label}",
        ])

    deduped = []
    seen = set()
    for prompt in prompts:
        if prompt not in seen:
            deduped.append(prompt)
            seen.add(prompt)

    return deduped[:3]


def render_quick_prompt_buttons(df: pd.DataFrame, schema: dict | None = None, dataset_name: str | None = None):
    st.markdown("##### Quick Prompts")
    prompt_cols = st.columns(3)
    quick_prompts = _generate_quick_prompts(df, schema, dataset_name)
    for idx, prompt in enumerate(quick_prompts):
        with prompt_cols[idx]:
            if st.button(prompt, key=f"starter_prompt_{idx}", use_container_width=True):
                st.session_state.auto_query = prompt
                st.rerun()


def render_chart_collection(charts, key_prefix: str = ""):
    if not charts:
        return

    # Build a stable unique suffix from the key_prefix or fall back to object id
    uid = key_prefix or str(id(charts))

    if len(charts) > 1:
        chart_titles = []
        for idx, chart in enumerate(charts):
            if isinstance(chart, dict):
                chart_titles.append(chart.get("title") or f"Chart Option {idx + 1}")
            else:
                chart_titles.append(f"Chart Option {idx + 1}")
        selected_title = st.selectbox("Chart view", chart_titles, key=f"chart_selector_{uid}")
        selected_index = chart_titles.index(selected_title)
        render_chart_card(charts[selected_index], st, key_prefix=f"chart_sel_{uid}_{selected_index}")
        with st.expander("Show all chart options", expanded=False):
            for idx, chart in enumerate(charts):
                render_chart_card(chart, st, key_prefix=f"chart_all_{uid}_{idx}")
    else:
        render_chart_card(charts[0], st, key_prefix=f"chart_single_{uid}")


def render_dataframe_result(dataframe: pd.DataFrame, key_prefix: str, title: str = "Data Table", max_rows: int = 500):
    display_df = dataframe
    if len(dataframe) > max_rows:
        display_df = dataframe.head(max_rows)
    render_table_panel(title, display_df, key_prefix, max_rows=max_rows)


def render_dict_result(result: dict, key_prefix: str):
    has_displayable = False
    
    for key, value in result.items():
        try:
            if "<Axes:" in str(value) or "<AxesSubplot" in str(value):
                continue
            
            # Start the container ONLY when we find the first displayable item
            if not has_displayable:
                st.markdown('<div class="glass-card" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
            
            df_result = pd.DataFrame(value).reset_index()
            if df_result.shape[1] == 2:
                df_result.columns = ["Category", "Value"]
            st.markdown(f"**{html.escape(str(key))}**")
            render_table_panel(str(key), df_result, f"{key_prefix}_{key}", max_rows=200)
            fig = px.bar(df_result, x=df_result.columns[0], y=df_result.columns[1], title=str(key))
            render_chart_card(fig, st)
            has_displayable = True
        except Exception:
            continue
            
    if has_displayable:
        st.markdown("</div>", unsafe_allow_html=True)
    return has_displayable


def render_follow_up_buttons(raw_suggestions: str, key_prefix: str):
    parsed_questions = extract_follow_up_questions(raw_suggestions)
    for idx, q in enumerate(parsed_questions):
        clean_q = clean_text(q).replace("`", "")
        if st.button(clean_q, key=f"{key_prefix}_fq_{idx}", use_container_width=True):
            st.session_state.auto_query = clean_q
            st.rerun()
    if not parsed_questions:
        st.caption("No follow-up questions available.")


def render_follow_up_section(raw_suggestions: str, key_prefix: str):
    if not raw_suggestions:
        return

    with st.expander("Suggested Follow-Up Questions", expanded=False):
        render_follow_up_buttons(raw_suggestions, key_prefix)


def render_chat_history_entry(entry: dict, entry_index: int = 0):
    """Render a single chat history entry.

    ``entry_index`` must be a stable integer (e.g. the list position inside
    ``st.session_state.chat_history``) so that Streamlit widget keys remain
    constant across reruns and charts / buttons do not disappear.
    """
    stable_key = f"h{entry_index}"
    render_user_bubble(entry["query"])

    if entry.get("query_rejected"):
        render_assistant_bubble(clean_text(entry.get("ai_response", "")))
        return

    if not (entry.get("ai_response") or entry.get("chart_data") is not None or entry.get("result") is not None):
        return

    if entry.get("ai_response"):
        clean_response = clean_text(entry["ai_response"])
        structured = structure_response(clean_response)
        if structured and any(structured.values()):
            render_structured_response(structured)
        else:
            render_assistant_bubble(clean_response)

    chart_data = entry.get("chart_data")
    if chart_data is not None:
        render_dataframe_result(chart_data, f"history_table_{stable_key}")
        render_chart_collection(entry.get("charts", []), key_prefix=f"hist_{stable_key}")
    else:
        result = entry.get("result")
        if isinstance(result, dict):
            render_dict_result(result, f"history_dict_{stable_key}")
        elif not entry.get("ai_response") and str(result) != "None":
            st.markdown('<div class="glass-card" style="margin-bottom: 16px; padding: 16px;">', unsafe_allow_html=True)
            st.write(str(result))
            st.markdown("</div>", unsafe_allow_html=True)

    # Re-render inline charts stored alongside the message
    inline_charts = entry.get("inline_charts", [])
    if inline_charts:
        render_chart_collection(inline_charts, key_prefix=f"inline_hist_{stable_key}")

    insight = entry.get("insight", "")
    if insight:
        render_insight_card(insight)

    summary_list = entry.get("summary", [])
    if summary_list:
        with st.expander("Answer Summary", expanded=False):
            for line in summary_list:
                st.write("-", line)

    if entry.get("suggestions"):
        render_follow_up_section(entry["suggestions"], f"suggest_{stable_key}")

    if entry.get("rephrases"):
        st.markdown("**Suggested Rephrases**")
        for idx, suggestion in enumerate(entry["rephrases"]):
            if st.button(suggestion, key=f"history_rephrase_{stable_key}_{idx}", use_container_width=True):
                st.session_state.auto_query = suggestion
                st.rerun()
