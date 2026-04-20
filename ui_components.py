import html
import re
from html import unescape

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from modules.chat_queue import queue_query
from modules.auto_visualizer import (
    build_graph_follow_up_suggestions,
    chart_download_bytes,
)


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = unescape(str(text))
    text = re.sub(r"</?[^>]+>", "", text)
    text = re.sub(r"<div\s+style=\"?", "", text, flags=re.IGNORECASE)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped in {'">', '"}', "</div>", "<div style=\"", "<div style="}:
            continue
        if stripped.lower().startswith("div style="):
            continue
        if re.match(r"^(background|padding|border-radius|max-width|font-size|line-height|color|border)\s*:", stripped):
            continue
        lines.append(stripped)
    text = "\n".join(lines)
    return text.strip()


def render_user_bubble(message: str):
    clean_msg = html.escape(clean_text(message)).replace("\n", "<br>")

    st.markdown(
        f"""
    <div style="display:flex; justify-content:flex-end; margin-bottom:16px;">
        <div style="
            background: linear-gradient(135deg,#4F46E5,#7C3AED);
            color:#FFFFFF;
            padding:10px 14px;
            border-radius:18px 18px 4px 18px;
            max-width:70%;
            font-size:14px;
            line-height:1.45;
            box-shadow: 0 10px 24px rgba(79,70,229,0.28);
        ">
            {clean_msg}
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_assistant_bubble(message: str):
    clean_msg = clean_text(message)
    left, right = st.columns([0.06, 0.94])
    with left:
        st.markdown(
            """
            <div style="
                width:36px;
                height:36px;
                border-radius:50%;
                background: linear-gradient(135deg,#22C55E,#16A34A);
                display:flex;
                align-items:center;
                justify-content:center;
                color:white;
                font-size:11px;
                font-weight:700;
                box-shadow: 0 8px 20px rgba(34,197,94,0.25);
                margin-top:2px;
            ">AI</div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        safe_msg = html.escape(clean_msg).replace("\n", "<br>")
        st.markdown(
            f"""
            <div style="
                background: rgba(15,23,42,0.96);
                border: 1px solid rgba(148, 163, 184, 0.5);
                border-radius: 14px;
                padding: 10px 14px;
                max-width: 78%;
                font-size: 14px;
                line-height: 1.5;
                box-shadow: 0 14px 32px rgba(15,23,42,0.9);
            ">
                {safe_msg}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_kpi_cards(kpis):
    if not kpis:
        return

    cols = st.columns(len(kpis))
    for i, kpi in enumerate(kpis):
        with cols[i]:
            metric = kpi.get("metric", "")
            total = kpi.get("total", "")
            avg = kpi.get("average", "")
            delta = float(kpi.get("delta", 0) or 0)
            direction = "up" if delta >= 0 else "down"
            arrow = "↑" if delta >= 0 else "↓"
            trend_class = "positive" if delta >= 0 else "negative"
            trend_label = kpi.get("trend_label", "from prior baseline")
            st.markdown(
                f"""
                <div class="kpi-card glass-card{' kpi-card--featured' if i == 0 else ''}">
                  <div class="kpi-card__topline">
                    <div class="kpi-card__label">{html.escape(str(metric))}</div>
                    <div class="kpi-card__chip {trend_class}">
                      <span>{arrow}</span>
                      <span>{abs(delta):.1f}%</span>
                    </div>
                  </div>
                  <div class="kpi-card__value">{html.escape(str(total))}</div>
                  <div class="kpi-card__meta">Avg: {html.escape(str(avg))}</div>
                  <div class="kpi-card__trend {trend_class}">
                    {arrow} {abs(delta):.1f}% {html.escape(str(trend_label)).lower()}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_section_header(title, subtitle=""):
    safe_title = html.escape(clean_text(title))
    safe_subtitle = html.escape(clean_text(subtitle))
    st.markdown(
        f"""
        <div class="section-heading">
            <div class="section-heading__title">{safe_title}</div>
            {'<div class="section-heading__subtitle">' + safe_subtitle + '</div>' if safe_subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _normalize_chart_payload(chart):
    if isinstance(chart, dict) and chart.get("figure") is not None:
        return chart
    if isinstance(chart, go.Figure):
        return {
            "figure": chart,
            "title": chart.layout.title.text if chart.layout.title else "Chart",
            "rationale": "",
            "summary": [],
            "warnings": [],
            "data": None,
            "x_col": "",
            "y_cols": [],
            "chart_type": "chart",
        }
    return None


def render_chart_card(chart, st_instance, key_prefix: str | None = None):
    payload = _normalize_chart_payload(chart)
    if not payload:
        return

    fig = payload["figure"]
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(15, 23, 42, 0)",
        plot_bgcolor="rgba(15, 23, 42, 0)",
        font=dict(color="#e6eefc", family="Segoe UI, sans-serif"),
        title=dict(font=dict(color="#f8fbff", size=18)),
        legend=dict(
            bgcolor="rgba(15, 23, 42, 0.75)",
            bordercolor="rgba(148, 163, 184, 0.12)",
            borderwidth=1,
        ),
        margin=dict(l=20, r=20, t=48, b=20),
        xaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.10)",
            zerolinecolor="rgba(148, 163, 184, 0.12)",
        ),
        yaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.10)",
            zerolinecolor="rgba(148, 163, 184, 0.12)",
        ),
    )
    chart_key = key_prefix or re.sub(r"[^a-zA-Z0-9_]+", "_", payload.get("title", "chart"))
    st_instance.plotly_chart(fig, width="stretch", key=f"{chart_key}_plot")

    rationale = clean_text(payload.get("rationale", ""))
    if rationale:
        st_instance.caption(f"Why this chart: {rationale}")

    for warning in payload.get("warnings", []):
        st_instance.caption(clean_text(warning))

    summary = payload.get("summary", []) or []
    if summary:
        st_instance.markdown("**Chart Summary**")
        for item in summary:
            st_instance.write(f"- {clean_text(item)}")

    data = payload.get("data")
    download_key = chart_key
    if isinstance(data, pd.DataFrame) and not data.empty:
        left, right = st_instance.columns(2)
        with left:
            st.download_button(
                "Download Plot Data",
                data=chart_download_bytes(payload),
                file_name=f"{download_key}_plot_data.csv",
                mime="text/csv",
                key=f"{download_key}_csv",
                width="stretch",
            )
        with right:
            try:
                image_bytes = fig.to_image(format="png", width=1200, height=700, scale=2)
                st.download_button(
                    "Download Chart PNG",
                    data=image_bytes,
                    file_name=f"{download_key}.png",
                    mime="image/png",
                    key=f"{download_key}_png",
                    width="stretch",
                )
            except Exception as exc:
                st.caption("PNG export is unavailable in this environment.")

    suggestion_items = build_graph_follow_up_suggestions(payload)
    if suggestion_items:
        st_instance.markdown("**Suggested Graphs**")
        st_instance.caption("These prompts are the most likely to return chart-friendly results.")
        for idx, item in enumerate(suggestion_items):
            clean_q = clean_text(item["question"])
            if st_instance.button(clean_q, key=f"{download_key}_graph_followup_chart_{idx}", width="stretch"):
                queue_query(clean_q)


def render_sidebar_dataset_badge(name, rows, cols):
    st.sidebar.markdown("### Active Dataset")

    safe_name = html.escape(clean_text(name))
    st.sidebar.markdown(
        f"""
    <div class="sidebar-dataset-card">
        <div style="color:#E2E8F0; font-size:14px; font-weight:600;">
            {safe_name}
        </div>
        <div class="sidebar-dataset-meta">{rows:,} rows | {cols} columns</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_sidebar_branding(app_title: str, app_icon: str, subtitle: str = "AI Intelligence Suite"):
    st.sidebar.markdown(
        f"""
    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); padding: 24px 20px; border-radius: 16px; margin-bottom: 24px; backdrop-filter: blur(10px); position: relative; overflow: hidden;">
        <div style="position: absolute; top: -50%; right: -20%; width: 120px; height: 120px; background: radial-gradient(circle, #6366F1 0%, transparent 70%); opacity: 0.45;"></div>
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px; position: relative; z-index: 1;">
            <div style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 4px 10px rgba(79, 70, 229, 0.32);">
                {html.escape(str(app_icon))}
            </div>
            <div style="font-size: 22px; font-weight: 800; color: white; letter-spacing: -0.5px;">
                {html.escape(str(app_title))}
            </div>
        </div>
        <div style="color: #94A3B8; font-size: 12px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; margin-left: 48px; position: relative; z-index: 1;">
            {html.escape(str(subtitle))}
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_sidebar_question_inspiration(questions):
    if not questions:
        return None

    st.sidebar.markdown("### Question Ideas")
    clicked_question = None

    with st.sidebar.container():
        st.markdown(
            """
        <div style="
            background: rgba(255,255,255,0.04);
            padding: 12px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.08);
            margin-top: 10px;
            margin-bottom: 10px;
        ">
        """,
            unsafe_allow_html=True,
        )

        for idx, question in enumerate(questions):
            label = clean_text(question)
            if st.button(label, key=f"sidebar_question_{idx}", width="stretch"):
                clicked_question = label

        st.markdown("</div>", unsafe_allow_html=True)

    return clicked_question


def render_insight_card(text):
    safe_text = html.escape(clean_text(text))
    st.markdown(
        f"""
        <div class="insight-banner">
            <div class="insight-banner__eyebrow">Business Insight</div>
            <div class="insight-banner__body">{safe_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result_status(title, body, kind="info"):
    tone_class = {
        "warning": "status-card--warning",
        "success": "status-card--success",
    }.get(kind, "status-card--info")
    st.markdown(
        f"""
        <div class="status-card {tone_class}">
            <div class="status-card__title">{html.escape(clean_text(title))}</div>
            <div class="status-card__body">{html.escape(clean_text(body))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_structured_response(data: dict):
    section_labels = {
        "EXECUTIVE INSIGHT": "Executive Insight",
        "KEY FINDINGS": "Key Findings",
        "BUSINESS IMPACT": "Business Impact",
        "LIMITATIONS": "Limitations",
        "RECOMMENDATIONS": "Recommendations",
        "RECOMMENDED NEXT STEPS": "Recommendations",
    }

    section_tones = {
        "EXECUTIVE INSIGHT": "rgba(59, 130, 246, 0.18)",
        "KEY FINDINGS": "rgba(16, 185, 129, 0.16)",
        "BUSINESS IMPACT": "rgba(14, 165, 233, 0.16)",
        "LIMITATIONS": "rgba(234, 179, 8, 0.14)",
        "RECOMMENDATIONS": "rgba(99, 102, 241, 0.18)",
        "RECOMMENDED NEXT STEPS": "rgba(99, 102, 241, 0.18)",
    }

    for section, points in data.items():
        if not points:
            continue

        label = section_labels.get(section, section.title())
        tone = section_tones.get(section, "rgba(148, 163, 184, 0.14)")
        # Wrap each section in a structured-section block so CSS can style it
        # Make Limitations collapsible using <details> without hiding content.
        safe_label = html.escape(label)
        safe_tone = html.escape(tone)
        header_html = f"<div class='structured-section__header'><span class='structured-section__icon'>💡</span><div class='structured-section__title'>{safe_label}</div></div>"

        if section == "LIMITATIONS":
            st.markdown(
                f"""
                <div class="structured-section" style="background:{safe_tone};">
                    <details open style="padding:10px; border-radius:10px;">
                        <summary style="font-weight:700; color:#c7d6ee; margin-bottom:8px;">{safe_label}</summary>
                        <div class="structured-section__body">
                """,
                unsafe_allow_html=True,
            )
            for point in points:
                st.markdown(f"- {clean_text(point)}")
            st.markdown("</div></details></div>", unsafe_allow_html=True)
        else:
            # Emphasize Executive Insight visually
            section_class = "structured-section structured-section--emphasize" if section == "EXECUTIVE INSIGHT" else "structured-section"
            st.markdown(
                f"""
                <div class="{section_class}" style="background:{safe_tone};">
                    {header_html}
                    <div class="structured-section__body" style="padding-top:6px;">
                """,
                unsafe_allow_html=True,
            )
            for point in points:
                st.markdown(f"- {clean_text(point)}")
            st.markdown("</div></div>", unsafe_allow_html=True)


def render_table_panel(title: str, dataframe: pd.DataFrame, key: str, max_rows: int | None = None):
    if dataframe is None:
        return

    working_df = dataframe.copy()
    if working_df.empty:
        st.info("No rows available for this view.")
        return

    safe_key = re.sub(r"[^a-zA-Z0-9_]+", "_", key)
    st.markdown('<div class="glass-card table-panel">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Search, filter, and sort this view without leaving the current analysis context.</div>', unsafe_allow_html=True)

    col_search, col_filter, col_sort = st.columns([1.5, 1, 1])
    with col_search:
        search_term = st.text_input("Search", placeholder="Search rows...", key=f"{safe_key}_search")
    with col_filter:
        filter_column = st.selectbox("Filter column", ["All columns"] + list(working_df.columns), key=f"{safe_key}_filter_col")
    with col_sort:
        sort_column = st.selectbox("Sort by", ["Original order"] + list(working_df.columns), key=f"{safe_key}_sort_col")

    if search_term:
        term = search_term.lower()
        mask = working_df.astype(str).apply(lambda col: col.str.lower().str.contains(term, na=False))
        working_df = working_df[mask.any(axis=1)]

    if filter_column != "All columns":
        filter_series = working_df[filter_column].dropna()
        unique_values = filter_series.unique().tolist()

        if pd.api.types.is_numeric_dtype(filter_series):
            sorted_values = sorted(unique_values)
        else:
            sorted_values = sorted(unique_values, key=lambda value: str(value).lower())

        value_options = [None] + sorted_values[:100]
        selected_value = st.selectbox(
            "Filter value",
            value_options,
            format_func=lambda value: "All" if value is None else str(value),
            key=f"{safe_key}_filter_val",
        )

        if selected_value is not None:
            working_df = working_df[working_df[filter_column] == selected_value]

    if sort_column != "Original order":
        ascending = st.toggle("Ascending", value=False, key=f"{safe_key}_ascending")
        try:
            working_df = working_df.sort_values(by=sort_column, ascending=ascending, kind="stable")
        except (KeyError, ValueError) as e:
            st.caption(f"Sort failed: {e}")
            pass

    if max_rows is not None and len(working_df) > max_rows:
        st.caption(f"Showing first {max_rows:,} of {len(working_df):,} rows after filters.")
        working_df = working_df.head(max_rows)
    else:
        st.caption(f"{len(working_df):,} rows shown")

    page_size = st.selectbox(
        "Rows per page",
        options=[25, 50, 100, 200],
        index=1,
        key=f"{safe_key}_page_size",
    )
    total_rows = len(working_df)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    page_number = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
        key=f"{safe_key}_page_number",
    )
    start_idx = (int(page_number) - 1) * int(page_size)
    end_idx = min(start_idx + int(page_size), total_rows)
    page_df = working_df.iloc[start_idx:end_idx]
    st.caption(f"Displaying rows {start_idx + 1:,} to {end_idx:,} of {total_rows:,}.")

    display_df = page_df.fillna("—").copy()
    display_df.columns = [html.escape(str(col)) for col in display_df.columns]

    rows_html = []
    for row_index, (_, row) in enumerate(display_df.iterrows()):
        cells = []
        for value in row.tolist():
            cell_value = html.escape(str(value))
            cells.append(f"<td>{cell_value}</td>")
        row_class = "even" if row_index % 2 else "odd"
        rows_html.append(f"<tr class='{row_class}'>{''.join(cells)}</tr>")

    header_html = "".join(f"<th>{col}</th>" for col in display_df.columns)
    table_html = f"""
    <div class="dark-table-wrap">
        <table class="dark-table">
            <thead>
                <tr>{header_html}</tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
    """

    st.markdown(table_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_quality_badge(confidence: float | None = None, source_columns: list[str] | None = None):
    """
    Render a visual quality/confidence badge for AI responses.
    
    Args:
        confidence: Float between 0.0-1.0 indicating model confidence
        source_columns: List of column names used to derive the answer
    
    Badge levels:
    - High (green): confidence >= 0.8 AND source_columns present
    - Medium (yellow): 0.5 <= confidence < 0.8 OR partial sources
    - Low (red): confidence < 0.5 OR no sources
    """
    confidence = float(confidence or 0.0)
    confidence = max(0.0, min(1.0, confidence))
    source_columns = source_columns or []
    has_sources = bool(source_columns and len(source_columns) > 0)
    
    # Determine a user-friendly badge level.
    if confidence >= 0.8 and has_sources:
        badge_level = "✅ High Confidence Insight"
        badge_color = "#10b981"  # Green
        badge_bg = "rgba(16, 185, 129, 0.1)"
        badge_border = "rgba(16, 185, 129, 0.3)"
        icon = "✅"
    elif confidence >= 0.5 or has_sources:
        badge_level = "ℹ️ Confidence Review Recommended"
        badge_color = "#f59e0b"  # Amber
        badge_bg = "rgba(245, 158, 11, 0.1)"
        badge_border = "rgba(245, 158, 11, 0.3)"
        icon = "ℹ️"
    else:
        badge_level = "⚠️ Low Confidence Insight"
        badge_color = "#ef4444"  # Red
        badge_bg = "rgba(239, 68, 68, 0.1)"
        badge_border = "rgba(239, 68, 68, 0.3)"
        icon = "⚠️"
    
    sources_text = " & ".join(source_columns[:2]) if source_columns else "active dataset"
    sources_display = f"📊 Based on {sources_text} data"
    
    st.markdown(
        f"""
        <div style="
            background: {badge_bg};
            border: 1px solid {badge_border};
            border-radius: 10px;
            padding: 10px 14px;
            margin-bottom: 12px;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 10px;
        ">
            <span style="
                color: {badge_color};
                font-weight: 700;
                font-size: 16px;
            ">{icon}</span>
            <div style="flex: 1;">
                <div style="
                    color: {badge_color};
                    font-weight: 700;
                    font-size: 13px;
                ">
                    {badge_level}
                </div>
                <div style="
                    color: #cbd5e1;
                    font-size: 12px;
                    margin-top: 3px;
                ">
                    {sources_display}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_settings_panel():
    """
    Render AI settings panel in the sidebar for model/temperature tuning.
    Returns a dict with current settings.
    """
    # Hide developer-tuning controls from end-user UI while keeping stable defaults.
    model_choice = st.session_state.get("ai_model", "llama-3.3-70b")
    temperature = float(st.session_state.get("ai_temperature", 0.7))
    max_tokens = int(st.session_state.get("ai_max_tokens", 1024))
    use_cache = bool(st.session_state.get("use_response_cache", True))
    fast_mode = bool(st.session_state.get("ui_fast_mode", True))

    # Performance panel removed from sidebar per request.
    # fast_mode remains read from session state default above.
    
    # Store settings in session state
    st.session_state["ai_model"] = model_choice
    st.session_state["ai_temperature"] = temperature
    st.session_state["ai_max_tokens"] = max_tokens
    st.session_state["use_response_cache"] = use_cache
    st.session_state["ui_fast_mode"] = fast_mode
    
    return {
        "model": model_choice,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "use_cache": use_cache,
        "fast_mode": fast_mode,
    }


def render_latency_badge(latency_ms: float | None = None):
    """
    Render a latency badge showing API response time and estimated token usage.
    
    Args:
        latency_ms: Response time in milliseconds
    """
    # Keep developer metrics out of user-facing UI.
    # Latency and token details should be tracked via logs/monitoring only.
    return


def render_queue_status(queue_stats: dict | None = None):
    """
    Render request queue status badge.
    
    Args:
        queue_stats: Dict with queue status from request_queue module
    """
    # Queue diagnostics are operational details; keep out of end-user UI.
    return


def render_cache_statistics(cache_stats: dict | None = None):
    """
    Render cache hit/miss statistics.
    
    Args:
        cache_stats: Dict with cache metrics from cache_metrics module
    """
    # Cache metrics are developer/ops details; keep out of end-user UI.
    return
