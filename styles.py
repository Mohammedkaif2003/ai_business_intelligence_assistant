TAILWIND_CDN = '<script src="https://cdn.tailwindcss.com"></script>'

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=Sora:wght@600;700;800&display=swap');

:root {
    --bg-app: #071728;
    --bg-panel: rgba(9, 30, 48, 0.84);
    --bg-panel-strong: rgba(9, 30, 48, 0.96);
    --bg-soft: rgba(148, 163, 184, 0.08);
    --border-soft: rgba(148, 163, 184, 0.16);
    --text-main: #f7fbff;
    --text-muted: #c7d8e8;
    --accent-a: #4f46e5;
    --accent-b: #7c3aed;
    --accent-c: #ff8a3d;
    --success: #10b981;
    --card-radius: 14px;
    --card-shadow: 0 14px 32px rgba(2, 6, 23, 0.28);
}

html, body, .stApp {
    background: #03111d !important;
    color: var(--text-main) !important;
    font-family: 'Manrope', 'Segoe UI', sans-serif !important;
}

/* ─── Eliminate ALL white/light background bleed from Streamlit wrappers ─── */
.stApp > header,
.stApp > footer,
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
header[data-testid="stHeader"],
footer,
.stApp > footer,
.stDeployButton,
#MainMenu,
.block-container,
[data-testid="block-container"],
.stApp > div,
.stApp > section,
.stApp > section > div,
.main,
.main > div,
section.main,
section.main > div,
section.main > div.block-container,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > div,
[data-testid="stAppViewContainer"] > section,
[data-testid="stAppViewBlockContainer"],
[data-testid="stBottomBlockContainer"],
[data-testid="stBottom"],
[data-testid="stMainBlockContainer"] {
    background: #03111d !important;
    background-color: #03111d !important;
}

/* Hide the default Streamlit header / deploy bar completely */
[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}

/* Ensure bottom chat-input area also gets the dark bg */
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"] {
    background: linear-gradient(180deg, transparent 0%, #03111d 12%) !important;
}

[data-testid="stSidebar"],
section[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebarNav"] {
    background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
    border-right: 1px solid rgba(99, 102, 241, 0.14) !important;
}

[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
}

[data-testid="stSidebar"] * {
    color: #edf4ff !important;
}

[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div {
    color: #edf4ff !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"],
[data-testid="stSidebar"] [data-baseweb="select"],
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],
[data-testid="stSidebar"] .stTextInput > div > div > input,
[data-testid="stSidebar"] .stNumberInput input {
    background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
}

.glass-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.03));
    border: 1px solid var(--border-soft);
    border-radius: 18px;
    padding: 20px;
    box-shadow: 0 18px 40px rgba(2, 6, 23, 0.22);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    animation: fadeSlideIn 0.45s ease;
}

.glass-card:hover {
    transform: translateY(-2px) scale(1.01);
    box-shadow: 0 22px 50px rgba(79, 70, 229, 0.18);
    border-color: rgba(99, 102, 241, 0.28);
}

[data-testid="stMetric"] {
    background: linear-gradient(180deg, rgba(99, 102, 241, 0.12), rgba(9, 30, 48, 0.42));
    border: 1px solid rgba(99, 102, 241, 0.2);
    border-radius: 18px;
    padding: 18px 18px 14px 18px;
}

[data-testid="stMetricLabel"] {
    color: #d8e2f2 !important;
    font-size: 0.82rem !important;
}

[data-testid="stMetricValue"] {
    color: #f8fbff !important;
    font-size: 1.7rem !important;
}

[data-testid="stMetricDelta"] {
    color: #86efac !important;
}

[data-testid="stSidebar"] small,
[data-testid="stSidebar"] .stCaption {
    color: #c6d3ea !important;
}

.stTabs [data-baseweb="tab-list"] {
    width: 100%;
    display: flex;
    align-items: stretch;
    gap: 10px;
    padding: 8px;
    margin-top: 10px;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border-soft);
    border-radius: 16px;
}

.stTabs [data-baseweb="tab"] {
    flex: 1;
    min-height: 46px;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 700;
    color: var(--text-muted);
    transition: all 0.22s ease;
    position: relative;
    border: 1px solid rgba(148, 163, 184, 0.14);
    background: rgba(255,255,255,0.02);
    overflow: hidden;
}

.stTabs [data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.06);
    color: #ffffff;
    border-color: rgba(99, 102, 241, 0.35);
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--accent-a), var(--accent-b)) !important;
    color: white !important;
    border-color: rgba(129, 140, 248, 0.55) !important;
    box-shadow: 0 10px 22px rgba(79, 70, 229, 0.26);
}

/* ─────────── Styled tab navigation (buttons-in-columns) ─────────── */
/*
 * Scoped via an adjacent-sibling selector off the .apex-tab-nav-marker
 * element emitted just above the tab row. Only the buttons inside the
 * st.columns immediately following the marker get this tab styling —
 * the rest of the app's buttons are untouched.
 */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .apex-tab-nav-marker)
    + [data-testid="stElementContainer"] [data-testid="stHorizontalBlock"] {
    gap: 10px !important;
    padding: 8px !important;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-soft);
    border-radius: 16px;
    box-shadow: 0 8px 20px rgba(2, 6, 23, 0.25);
}

[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .apex-tab-nav-marker)
    + [data-testid="stElementContainer"] .stButton > button {
    width: 100% !important;
    min-height: 52px !important;
    border-radius: 12px !important;
    /* Brighter border + subtle outer glow so inactive tabs read as
       clickable navigation, not disabled chips. */
    border: 1px solid rgba(148, 163, 184, 0.42) !important;
    background: rgba(255, 255, 255, 0.06) !important;
    color: #e6eefc !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.01em;
    transition: transform 0.2s ease, background 0.2s ease,
                border-color 0.2s ease, color 0.2s ease,
                box-shadow 0.2s ease !important;
    box-shadow: 0 1px 0 rgba(255, 255, 255, 0.04) inset,
                0 4px 10px rgba(2, 6, 23, 0.28) !important;
}

[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .apex-tab-nav-marker)
    + [data-testid="stElementContainer"] .stButton > button:hover {
    background: rgba(99, 102, 241, 0.12) !important;
    border-color: rgba(99, 102, 241, 0.45) !important;
    color: #ffffff !important;
    transform: translateY(-1px);
}

/* Active tab = Streamlit "primary" button. Override the app-wide orange
 * primary style (set later in this stylesheet) with a blue/indigo gradient
 * so tabs look like navigation, not CTAs. */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .apex-tab-nav-marker)
    + [data-testid="stElementContainer"] .stButton > button[kind="primary"],
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .apex-tab-nav-marker)
    + [data-testid="stElementContainer"] .stButton > button[kind="primary"]:hover,
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .apex-tab-nav-marker)
    + [data-testid="stElementContainer"] .stButton > button[kind="primary"]:focus {
    background: linear-gradient(135deg, var(--accent-a), var(--accent-b)) !important;
    border: 1px solid rgba(129, 140, 248, 0.65) !important;
    color: #ffffff !important;
    box-shadow: 0 10px 22px rgba(79, 70, 229, 0.35) !important;
    transform: translateY(-1px);
}

/* Hide the tiny marker span itself */
.apex-tab-nav-marker {
    display: block;
    height: 0;
    width: 0;
    overflow: hidden;
    line-height: 0;
}

button, .stButton > button, .stDownloadButton > button {
    border-radius: 12px !important;
    border: 1px solid rgba(148, 163, 184, 0.18) !important;
    background: rgba(255,255,255,0.06) !important;
    color: #ecf4ff !important;
    font-weight: 600 !important;
    min-height: 40px;
}

.stButton > button:hover, .stDownloadButton > button:hover {
    border-color: rgba(99, 102, 241, 0.45) !important;
    background: rgba(99, 102, 241, 0.14) !important;
    transform: scale(1.02);
}

.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: linear-gradient(135deg, #ef6c24, #ff8a3d) !important;
    border: none !important;
    color: white !important;
}

[data-baseweb="select"] > div,
[data-baseweb="select"] [role="combobox"],
.stSelectbox div[data-baseweb="select"],
.stTextInput > div > div > input,
.stNumberInput input {
    background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
    color: #e2e8f0 !important;
    border-radius: var(--card-radius) !important;
    border: 1px solid rgba(148, 163, 184, 0.22) !important;
    box-shadow: var(--card-shadow) !important;
}

/* Force dropdown popup menu (rendered in portal) to follow dark theme */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div {
    background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
    border: 1px solid rgba(148, 163, 184, 0.22) !important;
    border-radius: var(--card-radius) !important;
    box-shadow: var(--card-shadow) !important;
}

[data-baseweb="menu"],
[data-baseweb="menu"] > div,
[data-baseweb="menu"] ul,
[data-baseweb="menu"] li {
    background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
    color: #e2e8f0 !important;
}

[data-baseweb="menu"] li[aria-selected="true"],
[data-baseweb="menu"] li:hover {
    background: rgba(99, 102, 241, 0.24) !important;
    color: #f8fbff !important;
}

ul[role="listbox"] {
    background: transparent !important;
    color: #e2e8f0 !important;
}

div[role="listbox"],
[role="listbox"] {
    background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
    border: 1px solid rgba(148, 163, 184, 0.22) !important;
    border-radius: var(--card-radius) !important;
    box-shadow: var(--card-shadow) !important;
}

[role="listbox"] * {
    color: #e2e8f0 !important;
}

li[role="option"] {
    background: transparent !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
}

div[role="option"] {
    background: transparent !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
}

li[role="option"] > div,
div[role="option"] > div {
    background: transparent !important;
}

li[role="option"]:hover {
    background: rgba(99, 102, 241, 0.18) !important;
    color: #e2e8f0 !important;
}

div[role="option"]:hover,
li[role="option"]:hover > div,
div[role="option"]:hover > div {
    background: rgba(99, 102, 241, 0.18) !important;
    color: #e2e8f0 !important;
}

li[aria-selected="true"][role="option"] {
    background: rgba(99, 102, 241, 0.28) !important;
    color: #f8fbff !important;
}

div[aria-selected="true"][role="option"],
li[aria-selected="true"][role="option"] > div,
div[aria-selected="true"][role="option"] > div {
    background: rgba(99, 102, 241, 0.28) !important;
    color: #f8fbff !important;
}

.stTextInput > label,
.stSelectbox > label,
.stNumberInput > label {
    color: #dbeafe !important;
}

[data-testid="stExpander"] {
    border: 1px solid rgba(148, 163, 184, 0.16) !important;
    border-radius: 14px !important;
    background: rgba(8, 28, 45, 0.72) !important;
    overflow: hidden;
}

[data-testid="stExpander"] details {
    background: transparent !important;
}

[data-testid="stExpander"] summary {
    background: linear-gradient(180deg, rgba(49, 46, 129, 0.9), rgba(30, 41, 59, 0.88)) !important;
    color: #e8f4ff !important;
    border-bottom: 1px solid rgba(148, 163, 184, 0.14) !important;
    font-weight: 700 !important;
}

[data-testid="stExpander"] summary * {
    color: #e8f4ff !important;
}

[data-testid="stExpander"] details > div:last-child {
    background: rgba(7, 24, 39, 0.9) !important;
    color: #e8f4ff !important;
}

[data-testid="stExpander"] details > div:last-child * {
    color: #e8f4ff !important;
}

[data-testid="stChatInput"] {
    border: 1px solid rgba(129, 140, 248, 0.24) !important;
    border-radius: 18px !important;
    background:
        radial-gradient(circle at 8% 0%, rgba(99, 102, 241, 0.12), transparent 38%),
        linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
    box-shadow: 0 12px 28px rgba(2, 6, 23, 0.35), inset 0 0 0 1px rgba(255,255,255,0.03) !important;
    transition: border-color 220ms ease, box-shadow 220ms ease, transform 220ms ease !important;
    animation: chatInputReveal 260ms ease;
}

[data-testid="stChatInput"] > div,
[data-testid="stChatInputContainer"] {
    background: transparent !important;
    border-radius: 18px !important;
    padding: 6px 8px !important;
}

[data-testid="stChatInput"] form,
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="textarea"] > div,
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInput"] [data-baseweb="base-input"] > div {
    background: linear-gradient(180deg, #0b1326 0%, #060b18 100%) !important;
    border: 1px solid rgba(99, 102, 241, 0.22) !important;
    border-radius: 14px !important;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02) !important;
}

[data-testid="stChatInput"] textarea {
    color: #e2e8f0 !important;
    background: linear-gradient(180deg, #0b1326 0%, #060b18 100%) !important;
    border: none !important;
    box-shadow: none !important;
    padding: 8px 8px !important;
    caret-color: #c7d2fe !important;
    -webkit-text-fill-color: #e2e8f0 !important;
}

[data-testid="stChatInput"] textarea:focus,
[data-testid="stChatInput"] textarea:active {
    background: linear-gradient(180deg, #0b1326 0%, #060b18 100%) !important;
    color: #e2e8f0 !important;
    outline: none !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #9cb4cb !important;
    opacity: 1;
}

/* Compact theme box used around answer summaries and follow-ups */
.ai-theme-box {
    margin: 8px 0 !important;
    padding: 6px 0 !important;
}

/* Make expanders more compact and avoid large visual gaps */
[data-testid="stExpander"] summary {
    padding: 8px 14px !important;
    min-height: 40px !important;
    display: flex !important;
    align-items: center !important;
}

[data-testid="stExpander"] details > div:last-child {
    padding: 10px 14px !important;
}

/* Reduce extra vertical spacing inside glass cards to tighten layout */
.glass-card {
    padding: 14px !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: rgba(99, 102, 241, 0.78) !important;
    box-shadow:
        0 16px 34px rgba(2, 6, 23, 0.5),
        0 0 0 3px rgba(99, 102, 241, 0.22),
        0 0 24px rgba(99, 102, 241, 0.26) !important;
    transform: translateY(-1px);
}

[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: 1px solid rgba(199, 210, 254, 0.35) !important;
    color: #eafffe !important;
    width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
    min-width: 36px !important;
    border-radius: 999px !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 8px 16px rgba(79, 70, 229, 0.35) !important;
    transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease !important;
}

[data-testid="stChatInput"] button:hover {
    background: linear-gradient(135deg, #6366f1, #7c3aed) !important;
    transform: translateY(-1px) scale(1.03);
    box-shadow: 0 10px 20px rgba(99, 102, 241, 0.45) !important;
    filter: saturate(1.06);
}

[data-testid="stChatInput"] button:active {
    transform: translateY(0) scale(0.98);
}

[data-testid="stChatInput"] button:focus-visible {
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(199, 210, 254, 0.8), 0 8px 16px rgba(99, 102, 241, 0.45) !important;
}

[data-testid="stFileUploader"] {
    border: 1px dashed rgba(99, 102, 241, 0.38) !important;
    border-radius: var(--card-radius) !important;
    background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
    padding: 12px !important;
    box-shadow: var(--card-shadow) !important;
}

[data-testid="stFileUploader"] section,
[data-testid="stFileUploaderDropzone"] {
    background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
    border: none !important;
    border-radius: var(--card-radius) !important;
}

[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span {
    color: #c8dff3 !important;
}

[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] div[role="button"] {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: 1px solid rgba(199, 210, 254, 0.35) !important;
    color: #ecfffe !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
}

[data-testid="stFileUploader"] button:hover,
[data-testid="stFileUploader"] div[role="button"]:hover {
    background: linear-gradient(135deg, #6366f1, #7c3aed) !important;
    border-color: rgba(199, 210, 254, 0.55) !important;
}


.stSuccess,
.stSuccess > div,
[data-testid="stAlert"] {
    background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
    border: 1px solid rgba(20, 184, 166, 0.38) !important;
    border-radius: var(--card-radius) !important;
    box-shadow: var(--card-shadow) !important;
    color: #e2e8f0 !important;
}

.stSuccess *,
[data-testid="stAlert"] * {
    color: #e2e8f0 !important;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--border-soft);
    background: var(--bg-panel-strong) !important;
}

[data-testid="stDataFrame"] [role="columnheader"] {
    background: rgba(99, 102, 241, 0.14) !important;
    color: #f8fbff !important;
    font-weight: 700 !important;
}

[data-testid="stDataFrame"] [role="gridcell"] {
    color: #eef5ff !important;
    background: rgba(9, 30, 48, 0.9) !important;
}

[data-testid="stDataFrame"] [role="row"]:nth-child(even) [role="gridcell"] {
    background: rgba(13, 38, 58, 0.95) !important;
}

.report-shell {
    display: grid;
    grid-template-columns: minmax(0, 1.9fr) minmax(320px, 1fr);
    gap: 20px;
    align-items: start;
}

.report-list-card,
.report-config-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border-soft);
    border-radius: 18px;
    padding: 20px;
    height: 100%;
}

.report-query-item {
    background: rgba(255,255,255,0.035);
    border-left: 4px solid #6366f1;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 12px;
    border: 1px solid rgba(255,255,255,0.08);
}

.report-actions {
    margin-top: 22px;
    padding-top: 16px;
    border-top: 1px solid rgba(148, 163, 184, 0.12);
}

.forecast-hero,
.report-hero {
    padding: 22px;
    border-radius: 20px;
    border: 1px solid rgba(99, 102, 241, 0.2);
    background:
        radial-gradient(circle at top right, rgba(99, 102, 241, 0.2), transparent 30%),
        linear-gradient(180deg, rgba(9, 30, 48, 0.95), rgba(7, 23, 40, 0.86));
}

.forecast-controls {
    margin-top: 18px;
    padding: 16px;
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, 0.12);
    background: rgba(255,255,255,0.03);
}

.forecast-stat-grid,
.report-stat-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    margin-top: 16px;
}

.forecast-stat-card,
.report-stat-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 16px;
    padding: 16px;
}

.forecast-stat-label,
.report-stat-label,
.kpi-card__label,
.quick-insight-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #9ec2da;
}

.forecast-stat-value,
.report-stat-value {
    margin-top: 8px;
    font-size: 24px;
    font-weight: 800;
    color: #f8fbff;
}

.forecast-stat-subtle,
.report-stat-subtle,
.kpi-card__meta,
.sidebar-dataset-meta,
.chat-hero__subtitle {
    margin-top: 6px;
    font-size: 12px;
    color: #a8bad8;
}

.report-feature-list {
    display: grid;
    gap: 10px;
    margin-top: 10px;
}

.report-feature-item {
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(148, 163, 184, 0.1);
}

.kpi-card {
    min-height: 148px;
    position: relative;
    overflow: hidden;
}

.kpi-card::before {
    content: "";
    position: absolute;
    inset: auto -20% -35% auto;
    width: 120px;
    height: 120px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.24), transparent 70%);
}

.kpi-card__topline {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
}

.kpi-card__chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 5px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid transparent;
}

.kpi-card__chip.positive,
.kpi-card__trend.positive {
    color: #86efac;
    background: rgba(16, 185, 129, 0.12);
    border-color: rgba(16, 185, 129, 0.2);
}

.kpi-card__chip.negative,
.kpi-card__trend.negative {
    color: #fda4af;
    background: rgba(244, 63, 94, 0.12);
    border-color: rgba(244, 63, 94, 0.2);
}

.kpi-card__value {
    font-size: 30px;
    font-weight: 800;
    margin-top: 12px;
    line-height: 1.05;
    color: #f8fbff;
}

.kpi-card__trend {
    display: inline-flex;
    margin-top: 10px;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
}

.hero-chart-card {
    padding: 20px;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.12);
    background:
        radial-gradient(circle at top right, rgba(20, 184, 166, 0.2), transparent 32%),
        linear-gradient(180deg, rgba(9, 30, 48, 0.92), rgba(7, 23, 40, 0.88));
}

.quick-insights-panel {
    padding: 22px;
    border-radius: 18px;
    border: 1px solid rgba(20, 184, 166, 0.2);
    background:
        radial-gradient(circle at top right, rgba(20, 184, 166, 0.24), transparent 34%),
        linear-gradient(180deg, rgba(9, 30, 48, 0.92), rgba(9, 30, 48, 0.74));
}

.quick-insights-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    margin-top: 16px;
}

.quick-insight-item {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 14px;
    padding: 14px;
}

.quick-insight-value {
    font-size: 15px;
    font-weight: 700;
    color: #f8fbff;
}

.chat-shell {
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 22px;
    padding: 20px;
    background:
        radial-gradient(circle at top left, rgba(20, 184, 166, 0.2), transparent 34%),
        linear-gradient(180deg, rgba(7, 23, 40, 0.96), rgba(9, 30, 48, 0.88));
}

.chat-hero-card {
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 20px;
    padding: 22px 24px;
    margin-bottom: 14px;
    background:
        radial-gradient(circle at 6% 0%, rgba(99, 102, 241, 0.18), transparent 36%),
        radial-gradient(circle at 94% 100%, rgba(20, 184, 166, 0.16), transparent 40%),
        linear-gradient(180deg, rgba(7, 23, 40, 0.96), rgba(9, 30, 48, 0.88));
    box-shadow: 0 18px 40px rgba(2, 6, 23, 0.32);
    animation: fadeSlideIn 0.45s ease;
}

.chat-hero-block {
    display: flex;
    justify-content: space-between;
    gap: 18px;
    align-items: center;
    flex-wrap: wrap;
}

.ai-theme-box {
    margin-top: 10px;
    margin-bottom: 10px;
    padding: 10px;
    border-radius: 14px;
    border: 1px solid rgba(99, 102, 241, 0.3);
    background:
        radial-gradient(circle at 0% 0%, rgba(99, 102, 241, 0.14), transparent 34%),
        linear-gradient(180deg, rgba(9, 24, 45, 0.9), rgba(7, 18, 33, 0.92));
    box-shadow: 0 10px 22px rgba(2, 6, 23, 0.35);
}

.ai-theme-box .stButton > button {
    background: rgba(20, 35, 58, 0.82) !important;
    border: 1px solid rgba(99, 102, 241, 0.28) !important;
}

.ai-theme-box .stButton > button:hover {
    background: rgba(30, 47, 76, 0.9) !important;
    border-color: rgba(129, 140, 248, 0.52) !important;
}

.chat-hero {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: center;
    margin-bottom: 16px;
}

.chat-hero__title {
    font-size: 26px;
    font-weight: 800;
    color: #f8fbff;
}

.chat-status {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    color: #e0e7ff;
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.18), rgba(20, 184, 166, 0.16));
    border: 1px solid rgba(129, 140, 248, 0.3);
    box-shadow: 0 6px 18px rgba(79, 70, 229, 0.18);
    white-space: nowrap;
}

.chat-status__pulse {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
    animation: livePulse 1.8s infinite ease-out;
    flex-shrink: 0;
}

.chat-status__label {
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #eef2ff;
}

.typing-dots {
    display: inline-flex;
    gap: 5px;
    align-items: center;
    line-height: 0;
}

.typing-dots span {
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: linear-gradient(135deg, #818cf8, #6366f1);
    animation: pulseDots 1.2s infinite ease-in-out;
    display: inline-block;
}

.typing-dots span:nth-child(2) {
    animation-delay: 0.15s;
}

.typing-dots span:nth-child(3) {
    animation-delay: 0.3s;
}

@keyframes livePulse {
    0% {
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6);
        transform: scale(0.92);
    }
    70% {
        box-shadow: 0 0 0 10px rgba(16, 185, 129, 0);
        transform: scale(1);
    }
    100% {
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
        transform: scale(0.92);
    }
}

.landing-hero {
    margin-bottom: 18px;
    padding: 24px;
    border-radius: 24px;
    border: 1px solid rgba(99, 102, 241, 0.24);
    background:
        radial-gradient(circle at 12% 10%, rgba(99, 102, 241, 0.24), transparent 36%),
        radial-gradient(circle at 88% 16%, rgba(255, 138, 61, 0.2), transparent 30%),
        linear-gradient(165deg, rgba(8, 36, 56, 0.96) 0%, rgba(7, 23, 40, 0.98) 68%);
    box-shadow: 0 24px 48px rgba(2, 10, 20, 0.35);
    animation: fadeSlideIn 0.5s ease;
}

.landing-hero__kicker {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 700;
    color: #c7d2fe;
}

.landing-hero__title {
    margin-top: 8px;
    font-size: 34px;
    font-family: 'Sora', 'Segoe UI', sans-serif;
    font-weight: 800;
    line-height: 1.15;
    color: #f7fbff;
    max-width: 820px;
}

.landing-hero__subtitle {
    margin-top: 10px;
    font-size: 14px;
    color: #c7d8e8;
    max-width: 760px;
}

.landing-hero__stats {
    margin-top: 18px;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
}

.landing-hero__stat {
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    background: rgba(255, 255, 255, 0.05);
    padding: 12px;
}

.landing-hero__stat-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #9ec2da;
}

.landing-hero__stat-value {
    margin-top: 6px;
    font-size: 20px;
    font-weight: 800;
    color: #f7fbff;
}

.sidebar-dataset-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
    padding: 12px;
    border-radius: 12px;
    border: 1px solid rgba(99,102,241,0.22);
    margin-bottom: 10px;
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.08), 0 12px 26px rgba(2, 6, 23, 0.22);
}

.table-panel .stTextInput,
.table-panel .stSelectbox,
.table-panel [data-testid="stToggle"] {
    margin-top: 0.2rem;
}

.table-panel [data-testid="stHorizontalBlock"] {
    align-items: end;
    gap: 0.75rem;
}

.table-panel .stTextInput label,
.table-panel .stSelectbox label,
.table-panel [data-testid="stToggle"] label {
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8fb4db !important;
}

.dark-table-wrap {
    width: 100%;
    max-width: 100%;
    max-height: 320px;
    overflow: auto;
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.14);
    background: #0d2336;
}

.dark-table {
    width: max-content;
    min-width: 100%;
    border-collapse: collapse;
}

.dark-table thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: #12324a;
    color: #f8fbff;
    text-align: left;
    font-size: 12px;
    font-weight: 700;
    padding: 8px 10px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
    white-space: nowrap;
}

.dark-table tbody td {
    padding: 8px 10px;
    font-size: 12px;
    color: #e6eefc;
    border-bottom: 1px solid rgba(148, 163, 184, 0.09);
    white-space: nowrap;
}

.dark-table tbody tr.odd td {
    background: #0d2336;
}

.dark-table tbody tr.even td {
    background: #0f2a40;
}

.dark-table tbody tr:hover td {
    background: rgba(99, 102, 241, 0.18);
}

@keyframes pulseDots {
    0%, 80%, 100% { transform: scale(0.7); opacity: 0.45; }
    40% { transform: scale(1); opacity: 1; }
}

@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 980px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .report-shell,
    .quick-insights-grid,
    .forecast-stat-grid,
    .report-stat-grid,
    .landing-hero__stats {
        grid-template-columns: 1fr;
    }

    .chat-hero {
        flex-direction: column;
        align-items: flex-start;
    }

    .landing-hero__title {
        font-size: 28px;
    }
}

/* ---------------- Final Streamlit Dark Override ---------------- */
[data-baseweb="select"],
[data-baseweb="select"] > div,
[data-baseweb="select"] [role="combobox"] {
    background: #020617 !important;
    border: 1px solid #1e293b !important;
    color: #e2e8f0 !important;
    box-shadow: 0 10px 24px rgba(2, 6, 23, 0.26) !important;
}

[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] * {
    background: #0f172a !important;
    border-color: #1e293b !important;
    color: #e2e8f0 !important;
}

[role="listbox"],
[role="listbox"] * {
    background: #0f172a !important;
    color: #e2e8f0 !important;
    border-color: #1e293b !important;
}

[role="listbox"] [role="option"],
li[role="option"],
div[role="option"] {
    background: #0f172a !important;
    color: #e2e8f0 !important;
}

[role="listbox"] [role="option"]:hover,
li[role="option"]:hover,
div[role="option"]:hover {
    background: #1e293b !important;
    color: #e2e8f0 !important;
}

[role="listbox"] [role="option"][aria-selected="true"],
li[role="option"][aria-selected="true"],
div[role="option"][aria-selected="true"] {
    background: #1e293b !important;
    color: #f8fafc !important;
}

[data-testid="stFileUploader"],
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploader"] section,
[data-testid="stFileUploader"] article {
    background: #020617 !important;
    border-color: #1e293b !important;
    color: #e2e8f0 !important;
}

[data-testid="stFileUploader"] {
    border: 1px dashed #1e293b !important;
    border-radius: 14px !important;
    box-shadow: 0 10px 24px rgba(2, 6, 23, 0.26) !important;
}

[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] div[role="button"] {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: 1px solid rgba(199, 210, 254, 0.35) !important;
    color: #ecfffe !important;
}

[data-testid="stFileUploader"] button *,
[data-testid="stFileUploader"] div[role="button"] * {
    background: transparent !important;
    color: #ecfffe !important;
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"],
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] *,
[data-testid="stFileUploader"] .uploadedFile,
[data-testid="stFileUploader"] .uploadedFile * {
    background: #0f172a !important;
    color: #e2e8f0 !important;
    border-color: #1e293b !important;
}

.stAlert,
.stAlert > div,
.stAlert * {
    background: #0f172a !important;
    border-color: #1e293b !important;
    color: #e2e8f0 !important;
    box-shadow: 0 10px 24px rgba(2, 6, 23, 0.22) !important;
}

.stAlert [data-testid="stMarkdownContainer"],
.stAlert svg {
    color: #34d399 !important;
    fill: #34d399 !important;
}

input,
textarea,
.stTextInput input,
.stTextArea textarea {
    background: #020617 !important;
    border: 1px solid #1e293b !important;
    color: #e2e8f0 !important;
}

@keyframes chatInputReveal {
    from {
        opacity: 0.86;
        transform: translateY(2px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

input::placeholder,
textarea::placeholder {
    color: #94a3b8 !important;
}

/* Final clean sidebar uploader and status styling */
[data-testid="stFileUploader"] [data-testid*="FileUploaderFile"],
[data-testid="stFileUploader"] [class*="uploadedFile"],
[data-testid="stFileUploader"] [class*="fileUploader"] [class*="file"] {
    display: none !important;
}

[data-testid="stFileUploader"] *[style*="background"],
[data-testid="stFileUploader"] *[style*="background-color"] {
    background: transparent !important;
    background-color: transparent !important;
}

[data-testid="stFileUploader"],
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploader"] section,
[data-testid="stFileUploader"] article {
    background: linear-gradient(180deg, #0f172a, #020617) !important;
    border-color: #1e293b !important;
    color: #e2e8f0 !important;
}

[data-testid="stFileUploader"] {
    border: 1px dashed #1e293b !important;
    border-radius: 14px !important;
    box-shadow: 0 10px 24px rgba(2, 6, 23, 0.26) !important;
    padding: 12px !important;
    margin-bottom: 12px !important;
}

[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] div[role="button"] {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    color: #ecfffe !important;
    border: 1px solid rgba(199, 210, 254, 0.35) !important;
}

[data-testid="stFileUploader"] button *,
[data-testid="stFileUploader"] div[role="button"] * {
    background: transparent !important;
    background-color: transparent !important;
    color: #ecfffe !important;
}

.stSuccess,
.stSuccess > div,
.stAlert,
.stAlert > div {
    background: linear-gradient(180deg, #0f172a, #020617) !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px !important;
    box-shadow: 0 10px 24px rgba(2, 6, 23, 0.2) !important;
}

.stSuccess [data-testid="stMarkdownContainer"],
.stAlert [data-testid="stMarkdownContainer"] {
    color: #e2e8f0 !important;
}

.stSuccess svg,
.stAlert svg {
    color: #34d399 !important;
    fill: #34d399 !important;
}

/* Plain inline dataset success text (no card/background container) */
.sidebar-success-inline {
    margin-top: 6px;
    margin-bottom: 10px;
    padding: 0;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #86efac;
    font-size: 13px;
    font-weight: 700;
    line-height: 1.35;
}

/* Final uploader enforcement: hide native uploaded-file row in all variants */
[data-testid="stFileUploader"] [data-testid*="FileUploaderFile"],
[data-testid="stFileUploader"] [class*="uploadedFile"],
[data-testid="stFileUploader"] [class*="fileUploader"] [class*="file"],
[data-testid*="FileUploaderFile"],
[class*="uploadedFile"],
[class*="fileUploader"] [class*="file"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    border: 0 !important;
    overflow: hidden !important;
}

/* Keep uploader area dark and consistent */
[data-testid="stFileUploader"],
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploader"] section,
[data-testid="stFileUploader"] article,
[data-testid="stFileUploader"] div[role="presentation"] {
    background: linear-gradient(180deg, #0f172a, #020617) !important;
    border-color: #1e293b !important;
    color: #e2e8f0 !important;
}

/* 🔥 FORCE REMOVE DEFAULT STREAMLIT FILE CHIP (FINAL FIX) */
[data-testid*="FileUploaderFile"],
[class*="uploadedFile"],
[class*="fileUploader"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
}

/* Remove inner grey backgrounds */
[data-testid="stFileUploader"] * {
    background: transparent !important;
    background-color: transparent !important;
}

/* Clean dark uploader */
[data-testid="stFileUploader"] {
    background: linear-gradient(180deg, #0f172a, #020617) !important;
    border: 1px dashed #4338ca !important;
    border-radius: 14px !important;
    padding: 12px !important;
}

/* Empty state hero for first-time users */
.empty-state-hero {
    max-width: 760px;
    margin: 14vh 0 0 0;
    padding: 26px 24px;
    border-radius: 20px;
    border: 1px solid rgba(99, 102, 241, 0.26);
    background:
        radial-gradient(circle at 8% 6%, rgba(99, 102, 241, 0.2), transparent 36%),
        linear-gradient(180deg, rgba(11, 24, 44, 0.92), rgba(7, 17, 31, 0.94));
    box-shadow: 0 22px 46px rgba(2, 6, 23, 0.42);
    text-align: left;
    animation: heroFadeIn 380ms ease;
    transition: transform 220ms ease, box-shadow 220ms ease;
}

.empty-state-hero:hover {
    transform: translateY(-1px) scale(1.01);
    box-shadow: 0 26px 52px rgba(2, 6, 23, 0.5);
}

.empty-state-hero__title {
    font-size: 38px;
    font-weight: 800;
    color: #f8fbff;
    letter-spacing: -0.02em;
}

.empty-state-hero__subtitle {
    margin-top: 10px;
    color: #d7e3f1;
    font-size: 15px;
}

.empty-state-hero__support {
    margin-top: 12px;
    color: #9ab0ca;
    font-size: 13px;
}

/* Upload callout text */
.sidebar-upload-hint {
    margin-top: 6px;
    color: #c7d2fe;
    font-size: 12px;
    font-weight: 700;
}

.sidebar-upload-subhint {
    margin-top: 2px;
    margin-bottom: 8px;
    color: #94a3b8;
    font-size: 11px;
}

/* Make upload area feel like primary action */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    border: 1px dashed rgba(129, 140, 248, 1) !important;
    border-radius: 16px !important;
    padding: 22px !important;
    box-shadow:
        0 0 0 1px rgba(129, 140, 248, 0.4),
        0 18px 34px rgba(2, 6, 23, 0.48),
        0 0 28px rgba(99, 102, 241, 0.3) !important;
    animation: uploaderGlowPulse 2.1s ease-in-out infinite;
    transition: transform 180ms ease, box-shadow 180ms ease;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"]:hover {
    transform: translateY(-1px) scale(1.015);
    box-shadow:
        0 0 0 1px rgba(129, 140, 248, 0.62),
        0 18px 36px rgba(2, 6, 23, 0.55),
        0 0 38px rgba(129, 140, 248, 0.46) !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button,
[data-testid="stSidebar"] [data-testid="stFileUploader"] div[role="button"] {
    background: linear-gradient(135deg, #6366f1, #7c3aed) !important;
    border: 1px solid rgba(224, 231, 255, 0.65) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    min-height: 42px !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover,
[data-testid="stSidebar"] [data-testid="stFileUploader"] div[role="button"]:hover {
    background: linear-gradient(135deg, #7c83ff, #8b5cf6) !important;
    border-color: rgba(224, 231, 255, 0.9) !important;
    filter: saturate(1.08);
}

@keyframes uploaderGlowPulse {
    0%, 100% {
        box-shadow:
            0 0 0 1px rgba(129, 140, 248, 0.25),
            0 16px 32px rgba(2, 6, 23, 0.45),
            0 0 24px rgba(99, 102, 241, 0.2);
    }
    50% {
        box-shadow:
            0 0 0 1px rgba(129, 140, 248, 0.42),
            0 18px 36px rgba(2, 6, 23, 0.55),
            0 0 30px rgba(129, 140, 248, 0.34);
    }
}

@keyframes heroFadeIn {
    from {
        opacity: 0;
        transform: translateY(6px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* ─────────────────── Login page ─────────────────── */
.login-hero {
    margin-bottom: 26px;
    padding: 34px 28px 28px 28px;
    border-radius: 22px;
    border: 1px solid rgba(99, 102, 241, 0.28);
    background:
        radial-gradient(circle at 12% 10%, rgba(99, 102, 241, 0.28), transparent 36%),
        radial-gradient(circle at 88% 14%, rgba(255, 138, 61, 0.22), transparent 32%),
        linear-gradient(165deg, rgba(8, 36, 56, 0.96) 0%, rgba(7, 23, 40, 0.98) 68%);
    box-shadow: 0 24px 48px rgba(2, 10, 20, 0.35);
    text-align: center;
    animation: fadeSlideIn 0.5s ease;
}
.login-hero__badge {
    display: inline-flex;
    width: 58px;
    height: 58px;
    align-items: center;
    justify-content: center;
    border-radius: 16px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: white;
    font-size: 28px;
    box-shadow: 0 10px 22px rgba(79, 70, 229, 0.36);
    margin-bottom: 14px;
}
.login-hero__title {
    font-family: 'Sora', 'Segoe UI', sans-serif;
    font-size: 30px;
    font-weight: 800;
    color: #f8fbff;
    letter-spacing: -0.02em;
}
.login-hero__subtitle {
    margin-top: 6px;
    font-size: 13px;
    color: #c7d8e8;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-weight: 600;
}
.login-hero__divider {
    margin: 18px auto 16px auto;
    width: 60px;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(129, 140, 248, 0.7), transparent);
    border-radius: 2px;
}
.login-hero__tag {
    font-size: 14px;
    color: #e2e8f0;
    font-weight: 500;
}

/* Sidebar user card + logout */
.sidebar-user-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 14px;
    margin-bottom: 10px;
    border-radius: 14px;
    border: 1px solid rgba(99, 102, 241, 0.22);
    background: linear-gradient(180deg, rgba(99, 102, 241, 0.12), rgba(9, 30, 48, 0.52));
}
.sidebar-user-card__avatar {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: white;
    font-weight: 800;
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 6px 14px rgba(79, 70, 229, 0.32);
}
.sidebar-user-card__name {
    font-size: 14px;
    font-weight: 700;
    color: #f8fbff;
}
.sidebar-user-card__role {
    font-size: 11px;
    color: #a8bad8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 2px;
}
</style>
"""


def inject_styles(st):
    st.markdown(TAILWIND_CDN, unsafe_allow_html=True)
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
