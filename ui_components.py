# ── Reusable UI building blocks ── edit this file to change component designs

import streamlit as st
from config import KPI_ACCENT_COLORS, KPI_ICONS
import re

def parse_markdown(text: str) -> str:
    """Parse basic markdown into HTML for UI rendering."""
    if not text: return ""
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    return text.replace('\n', '<br>')

def render_kpi_cards(kpis: list):
    """Render KPI cards in a 4-column grid with premium styling."""
    if not kpis:
        st.info("No numeric columns available for KPI metrics.")
        return
    cols = st.columns(len(kpis))
    
    # Premium gradient maps
    gradients = [
        "linear-gradient(135deg, #4F46E5 0%, #3B82F6 100%)", # Indigo to Blue
        "linear-gradient(135deg, #059669 0%, #10B981 100%)", # Emerald
        "linear-gradient(135deg, #D97706 0%, #F59E0B 100%)", # Amber
        "linear-gradient(135deg, #E11D48 0%, #F43F5E 100%)"  # Rose
    ]
    
    shadow_colors = [
        "rgba(79, 70, 229, 0.2)",
        "rgba(16, 185, 129, 0.2)",
        "rgba(245, 158, 11, 0.2)",
        "rgba(244, 63, 94, 0.2)"
    ]

    for i, kpi in enumerate(kpis):
        idx = i % len(gradients)
        grad = gradients[idx]
        shadow = shadow_colors[idx]
        icon = KPI_ICONS[i % len(KPI_ICONS)]
        
        with cols[i]:
            # Critical: removed all blank newlines from the string
            st.markdown(f"""
            <div style="background: white; border-radius: 20px; padding: 24px; position: relative; overflow: hidden; border: 1px solid #F1F5F9; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05), 0 8px 10px -6px rgba(0,0,0,0.01); transition: transform 0.3s ease, box-shadow 0.3s ease;" onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 10px 25px -5px rgba(0,0,0,0.05), 0 8px 10px -6px rgba(0,0,0,0.01)';">
                <!-- Decorative blurred circle in the background -->
                <div style="position: absolute; top: -20px; right: -20px; width: 100px; height: 100px; background: {grad}; opacity: 0.1; filter: blur(20px); border-radius: 50%;"></div>
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                    <div style="color: #64748B; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">
                        {kpi['metric']}
                    </div>
                    <div style="width: 36px; height: 36px; border-radius: 10px; background: {grad}; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px {shadow};">
                        <span style="font-size: 18px; color: white;">{icon}</span>
                    </div>
                </div>
                <div style="font-size: 32px; font-weight: 800; color: #0F172A; letter-spacing: -0.5px; line-height: 1;">
                   {kpi['total']:,.2f}
                </div>
                <div style="display: flex; align-items: center; gap: 6px; margin-top: 12px;">
                    <span style="display: inline-flex; align-items: center; justify-content: center; padding: 2px 6px; border-radius: 4px; background: #ECFDF5; color: #059669; font-size: 11px; font-weight: 600;">
                        Avg
                    </span>
                    <span style="font-size: 13px; color: #64748B; font-weight: 500;">
                        {kpi['average']:,.2f}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

def render_section_header(title: str, subtitle: str = ""):
    st.markdown(f"""
    <div style="margin: 2.5rem 0 1.5rem;">
      <h2 style="font-size: 26px; font-weight: 800; color: #0F172A; letter-spacing: -0.5px; margin-bottom: 4px; background: linear-gradient(135deg, #0F172A 0%, #334155 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        {title}
      </h2>
      {"<p style='font-size: 15px; color: #64748B; font-weight: 400; max-width: 600px;'>" + subtitle + "</p>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)

def render_chart_card(fig, st_instance):
    fig.update_layout(
        template="plotly_white",
        height=450,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", color="#334155"),
        title=dict(font=dict(size=18, color="#0F172A", family="Inter, sans-serif")),
        modebar=dict(bgcolor='rgba(255, 255, 255, 0.8)', color="#64748B", activecolor="#4F46E5"),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Inter")
    )
    # Applying nice color palette to chart if it's not custom
    fig.update_traces(marker=dict(line=dict(width=0)))
    
    st_instance.markdown(
        '<div class="premium-card" style="margin-bottom: 24px; padding: 16px;">',
        unsafe_allow_html=True
    )
    st_instance.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})
    st_instance.markdown('</div>', unsafe_allow_html=True)

def render_user_bubble(message: str):
    st.markdown(f"""
    <div style="display: flex; justify-content: flex-end; margin-bottom: 24px;">
      <div style="background: linear-gradient(135deg, #4F46E5 0%, #4338CA 100%); color: white; border-radius: 20px 20px 4px 20px; padding: 14px 20px; max-width: 80%; font-size: 15px; font-weight: 400; line-height: 1.6; box-shadow: 0 4px 14px 0 rgba(79, 70, 229, 0.25);">
        {parse_markdown(message)}
      </div>
      <div style="width: 36px; height: 36px; border-radius: 50%; background: #E0E7FF; display: flex; align-items: center; justify-content: center; margin-left: 12px; color: #4338CA; font-weight: 700; font-size: 14px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); flex-shrink: 0;">
        You
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_assistant_bubble(message: str):
    st.markdown(f"""
    <div style="display: flex; align-items: flex-start; margin-bottom: 24px;">
      <div style="width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #10B981 0%, #059669 100%); display: flex; align-items: center; justify-content: center; margin-right: 12px; color: white; font-weight: 700; font-size: 12px; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3); flex-shrink: 0;">
        AI
      </div>
      <div style="background: white; border: 1px solid #E2E8F0; border-radius: 4px 20px 20px 20px; padding: 16px 20px; max-width: 85%; font-size: 15px; color: #1E293B; line-height: 1.65; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);">
        {parse_markdown(message)}
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar_dataset_badge(dataset_name: str, rows: int, cols: int):
    st.sidebar.markdown(f"""
    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 16px; margin-bottom: 24px; backdrop-filter: blur(10px);">
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
         <div style="width: 8px; height: 8px; border-radius: 50%; background: #10B981; box-shadow: 0 0 8px #10B981;"></div>
         <div style="color: #94A3B8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em;">
            Active Dataset
         </div>
      </div>
      <div style="color: white; font-weight: 600; font-size: 15px; margin-bottom: 8px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
        {dataset_name}
      </div>
      <div style="display: flex; gap: 8px;">
          <div style="background: rgba(59, 130, 246, 0.15); color: #60A5FA; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 500;">
            {rows:,} rows
          </div>
          <div style="background: rgba(139, 92, 246, 0.15); color: #A78BFA; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 500;">
            {cols} columns
          </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_insight_card(insight: str):
    st.markdown(f"""
    <div style="background: linear-gradient(to right, #EEF2FF, #F5F3FF); border-left: 4px solid #4F46E5; border-radius: 0 12px 12px 0; padding: 20px; margin: 16px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); position: relative; overflow: hidden;">
      <!-- Shine effect -->
      <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.8), transparent); transform: skewX(-20deg) translateX(-150%); transition: transform 0.5s;" onmouseover="this.style.transform='skewX(-20deg) translateX(150%)';" onmouseout="setTimeout(() => this.style.transform='skewX(-20deg) translateX(-150%)', 500);"></div>
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
          <span style="font-size: 16px;">💡</span>
          <div style="color: #4F46E5; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;">
            Key AI Insight
          </div>
      </div>
      <div style="color: #1E293B; font-size: 15px; line-height: 1.6; font-weight: 500; position: relative; z-index: 1;">
        {parse_markdown(insight)}
      </div>
    </div>
    """, unsafe_allow_html=True)
