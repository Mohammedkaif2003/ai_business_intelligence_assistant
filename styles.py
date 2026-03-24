# ── All custom CSS ── edit this file to change visual styling

TAILWIND_CDN = '<script src="https://cdn.tailwindcss.com"></script>'

CUSTOM_CSS = """
<style>
/* Tab active state */
.stTabs [aria-selected="true"] {
    background-color: #2563EB !important;
    color: white !important;
    border-radius: 8px;
}
.stTabs [data-baseweb="tab"] {
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 600;
    background: #F1F5F9;
    margin-right: 6px;
}
.stTabs [data-baseweb="tab"]:hover {
    background: #E2E8F0;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: white;
    border-radius: 12px;
    padding: 1rem;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #1E293B !important;
}
[data-testid="stSidebar"] * {
    color: #CBD5E1 !important;
}

/* DataFrame */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
}

/* Chat input */
[data-testid="stChatInput"] textarea {
    border-radius: 12px !important;
}

/* Main background */
.main .block-container {
    background: #F8FAFC;
    padding-top: 2rem;
}
</style>
"""

def inject_styles(st):
    st.markdown(TAILWIND_CDN, unsafe_allow_html=True)
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
