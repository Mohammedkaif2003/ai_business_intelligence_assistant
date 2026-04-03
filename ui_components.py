import html
import re
from html import unescape

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

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
                <div class="kpi-card glass-card">
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
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


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
    st_instance.plotly_chart(fig, use_container_width=True, key=f"{chart_key}_plot")

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
                use_container_width=True,
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
                    use_container_width=True,
                )
            except Exception:
                st.caption("PNG export is unavailable in this environment.")

    suggestion_items = build_graph_follow_up_suggestions(payload)
    if suggestion_items:
        st_instance.markdown("**Suggested Graphs**")
        st_instance.caption("These prompts are the most likely to return chart-friendly results.")
        for idx, item in enumerate(suggestion_items):
            clean_q = clean_text(item["question"])
            if st_instance.button(clean_q, key=f"{download_key}_graph_followup_chart_{idx}", use_container_width=True):
                st.session_state.auto_query = clean_q
                st.rerun()


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
            if st.button(label, key=f"sidebar_question_{idx}", use_container_width=True):
                clicked_question = label

        st.markdown("</div>", unsafe_allow_html=True)

    return clicked_question


def render_insight_card(text):
    st.info(clean_text(text))


def render_result_status(title, body, kind="info"):
    message = f"**{clean_text(title)}**\n\n{clean_text(body)}"
    if kind == "warning":
        st.warning(message)
    elif kind == "success":
        st.success(message)
    else:
        st.info(message)


def render_structured_response(data: dict):
    section_labels = {
        "EXECUTIVE INSIGHT": "Executive Insight",
        "KEY FINDINGS": "Key Findings",
        "BUSINESS IMPACT": "Business Impact",
        "LIMITATIONS": "Limitations",
        "RECOMMENDATIONS": "Recommendations",
    }

    for section, points in data.items():
        if not points:
            continue

        label = section_labels.get(section, section.title())
        st.markdown(f"### {label}")

        for point in points:
            st.write(f"- {clean_text(point)}")

        st.markdown("---")


def render_table_panel(title: str, dataframe: pd.DataFrame, key: str, max_rows: int | None = None):
    if dataframe is None:
        return

    working_df = dataframe.copy()
    if working_df.empty:
        st.info("No rows available for this view.")
        return

    safe_key = re.sub(r"[^a-zA-Z0-9_]+", "_", key)
    st.markdown('<div class="glass-card table-panel">', unsafe_allow_html=True)
    st.markdown(f"### {html.escape(title)}")

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
        except Exception:
            pass

    if max_rows is not None and len(working_df) > max_rows:
        st.caption(f"Showing first {max_rows:,} of {len(working_df):,} rows after filters.")
        working_df = working_df.head(max_rows)
    else:
        st.caption(f"{len(working_df):,} rows shown")

    display_df = working_df.fillna("—").copy()
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
