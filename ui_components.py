# ── Reusable UI building blocks ── edit this file to change component designs

import streamlit as st
from config import KPI_ACCENT_COLORS, KPI_ICONS

def render_kpi_cards(kpis: list):
    """Render KPI cards in a 4-column grid with coloured left borders."""
    if not kpis:
        st.info("No numeric columns available for KPI metrics.")
        return
    cols = st.columns(len(kpis))
    accent_map = ["#3B82F6", "#10B981", "#F59E0B", "#F43F5E"]
    for i, kpi in enumerate(kpis):
        accent = accent_map[i % len(accent_map)]
        icon = KPI_ICONS[i % len(KPI_ICONS)]
        with cols[i]:
            st.markdown(f"""
            <div style="background:white; border-radius:12px; padding:20px;
                        border:1px solid #E2E8F0; border-left:4px solid {accent};
                        box-shadow:0 1px 3px rgba(0,0,0,0.05);">
              <div style="color:#64748B; font-size:11px; font-weight:600;
                          text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">
                {icon} {kpi['metric']}
              </div>
              <div style="font-size:28px; font-weight:700; color:#1E293B;">
                {kpi['total']:,.2f}
              </div>
              <div style="font-size:12px; color:#10B981; margin-top:6px; font-weight:500;">
                Avg {kpi['average']:,.2f}
              </div>
            </div>
            """, unsafe_allow_html=True)

def render_section_header(title: str, subtitle: str = ""):
    """Render a styled section header."""
    st.markdown(f"""
    <div style="margin: 1.5rem 0 0.75rem;">
      <div style="font-size:18px; font-weight:700; color:#1E293B;">{title}</div>
      {"<div style='font-size:13px; color:#64748B; margin-top:2px;'>" + subtitle + "</div>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)

def render_chart_card(fig, st_instance):
    """Wrap a Plotly chart in a white card."""
    fig.update_layout(
        template="plotly_white",
        height=420,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st_instance.markdown(
        '<div style="background:white; border-radius:12px; padding:16px; '
        'border:1px solid #E2E8F0; box-shadow:0 1px 3px rgba(0,0,0,0.05); margin-bottom:16px;">',
        unsafe_allow_html=True
    )
    st_instance.plotly_chart(fig, use_container_width=True)
    st_instance.markdown('</div>', unsafe_allow_html=True)

def render_user_bubble(message: str):
    st.markdown(f"""
    <div style="display:flex; justify-content:flex-end; margin-bottom:12px;">
      <div style="background:#2563EB; color:white; border-radius:18px 18px 4px 18px;
                  padding:12px 16px; max-width:75%; font-size:14px; line-height:1.5;">
        {message}
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_assistant_bubble(message: str):
    st.markdown(f"""
    <div style="display:flex; align-items:flex-start; gap:10px; margin-bottom:12px;">
      <div style="width:32px; height:32px; border-radius:50%; background:#EFF6FF;
                  display:flex; align-items:center; justify-content:center;
                  color:#2563EB; font-size:11px; font-weight:700; flex-shrink:0;">AI</div>
      <div style="background:white; border:1px solid #E2E8F0; border-radius:4px 18px 18px 18px;
                  padding:12px 16px; max-width:75%; font-size:14px; color:#334155; line-height:1.5;">
        {message}
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar_dataset_badge(dataset_name: str, rows: int, cols: int):
    st.sidebar.markdown(f"""
    <div style="background:#0F172A; border-radius:10px; padding:14px; margin-bottom:16px;">
      <div style="color:#94A3B8; font-size:10px; text-transform:uppercase;
                  letter-spacing:0.08em; margin-bottom:6px;">Active Dataset</div>
      <div style="color:white; font-weight:600; font-size:14px;">{dataset_name}</div>
      <div style="color:#34D399; font-size:12px; margin-top:4px;">{rows:,} rows · {cols} columns</div>
    </div>
    """, unsafe_allow_html=True)

def render_insight_card(insight: str):
    st.markdown(f"""
    <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px;
                padding:14px 16px; margin-top:12px;">
      <div style="color:#1D4ED8; font-size:12px; font-weight:600;
                  text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px;">
        🧠 Business Insight
      </div>
      <div style="color:#1E3A5F; font-size:14px; line-height:1.6;">{insight}</div>
    </div>
    """, unsafe_allow_html=True)
