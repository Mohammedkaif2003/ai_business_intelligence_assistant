TAILWIND_CDN = '<script src="https://cdn.tailwindcss.com"></script>'

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=Sora:wght@600;700;800&display=swap');

:root {
    --bg-app: #04111d;
    --bg-panel: rgba(9, 25, 41, 0.84);
    --bg-panel-strong: rgba(8, 22, 36, 0.96);
    --bg-soft: rgba(148, 163, 184, 0.08);
    --border-soft: rgba(125, 211, 252, 0.16);
    --border-strong: rgba(125, 211, 252, 0.28);
    --text-main: #f5fbff;
    --text-muted: #c9dae9;
    --text-soft: #8da5bb;
    --accent-a: #22c55e;
    --accent-b: #38bdf8;
    --accent-c: #f59e0b;
    --accent-d: #f97316;
    --success: #10b981;
    --warning: #f59e0b;
    --insight: #38bdf8;
    --danger: #fb7185;
    --card-radius: 18px;
    --card-shadow: 0 20px 44px rgba(2, 10, 20, 0.32);
}

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background:
        radial-gradient(circle at 0% 0%, rgba(34, 197, 94, 0.08), transparent 24%),
        radial-gradient(circle at 100% 0%, rgba(56, 189, 248, 0.09), transparent 28%),
        linear-gradient(180deg, #03111d 0%, #04131f 48%, #061622 100%) !important;
    color: var(--text-main) !important;
    font-family: 'Manrope', 'Segoe UI', sans-serif !important;
}

html, body {
    margin: 0 !important;
    padding: 0 !important;
    min-height: 100vh !important;
}

html {
    background: #03111d !important;
}

body::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: -9999;
    background:
        radial-gradient(circle at 0% 0%, rgba(34, 197, 94, 0.08), transparent 24%),
        radial-gradient(circle at 100% 0%, rgba(56, 189, 248, 0.09), transparent 28%),
        linear-gradient(180deg, #03111d 0%, #04131f 48%, #061622 100%);
}

body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    min-height: 100vh !important;
}

[data-testid="stAppViewContainer"] {
    background-attachment: fixed !important;
}

[data-testid="stAppViewContainer"] > section,
[data-testid="stAppViewContainer"] > section > div,
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"],
[data-testid="stBottomBlockContainer"] > div,
.stChatFloatingInputContainer,
.stChatInputContainer {
    background-color: #03111d !important;
}

[data-testid="stMain"] {
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="stMainBlockContainer"] {
    width: 100% !important;
    flex: 1 0 auto !important;
    padding-bottom: 8rem !important;
}

/* Remove default Streamlit chrome strips that can look white on some themes. */
header[data-testid="stHeader"],
footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    background: transparent !important;
}

[data-testid="stAppViewContainer"] > .main {
    background: transparent !important;
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
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 34%),
        linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.025));
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 20px;
    padding: 22px;
    box-shadow: var(--card-shadow);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    animation: fadeSlideIn 0.45s ease;
    position: relative;
    overflow: hidden;
}

.glass-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 24px 48px rgba(4, 15, 28, 0.42);
    border-color: rgba(125, 211, 252, 0.24);
}

.glass-card::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(255,255,255,0.03), transparent 42%);
    pointer-events: none;
}

.section-heading,
.section-hero,
.section-title,
.section-subtitle {
    position: relative;
    z-index: 1;
}

.section-heading {
    margin: 8px 0 14px;
}

.section-heading__title,
.section-title {
    color: var(--text-main);
    font-family: 'Sora', 'Segoe UI', sans-serif;
    font-size: 1.5rem;
    font-weight: 800;
    line-height: 1.2;
    letter-spacing: -0.03em;
}

.section-heading__subtitle,
.section-subtitle {
    margin-top: 6px;
    max-width: 780px;
    color: var(--text-muted);
    font-size: 0.95rem;
    line-height: 1.6;
}

.section-hero__eyebrow,
.chat-hero__eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid rgba(125, 211, 252, 0.2);
    background: rgba(255, 255, 255, 0.04);
    color: #b8d6ea;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 800;
}

.section-hero__title {
    margin-top: 14px;
    font-size: 2rem;
    font-family: 'Sora', 'Segoe UI', sans-serif;
    font-weight: 800;
    color: var(--text-main);
    line-height: 1.08;
    max-width: 760px;
}

.section-hero__subtitle {
    margin-top: 10px;
    max-width: 760px;
    color: var(--text-muted);
    font-size: 1rem;
    line-height: 1.65;
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

/* Fallback styling for Streamlit tab markup using ARIA roles (covers Streamlit markup changes) */
[role="tablist"] {
    width: 100% !important;
    display: flex !important;
    align-items: stretch !important;
    gap: 10px !important;
    padding: 8px !important;
    margin-top: 10px !important;
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 16px !important;
}

[role="tab"] {
    flex: 1 1 0% !important;
    min-height: 46px !important;
    border-radius: 12px !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    color: var(--text-muted) !important;
    transition: all 0.22s ease !important;
    position: relative !important;
    border: 1px solid rgba(148, 163, 184, 0.14) !important;
    background: rgba(255,255,255,0.02) !important;
    overflow: hidden !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 14px !important;
}

[role="tab"]:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #ffffff !important;
    border-color: rgba(99, 102, 241, 0.35) !important;
}

[role="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, var(--accent-a), var(--accent-b)) !important;
    color: white !important;
    border-color: rgba(129, 140, 248, 0.55) !important;
    box-shadow: 0 10px 22px rgba(79, 70, 229, 0.26) !important;
}

/* Extra fallbacks: ensure nested buttons or inner wrappers become full-width flex items */
[role="tab"] > button,
[role="tab"] > div > button,
button[role="tab"],
.stTabs [data-baseweb="tab"] > button,
.stTabs [data-baseweb="tab"] > div > button {
    width: 100% !important;
    height: 100% !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: transparent !important;
    border: none !important;
    padding: 12px 14px !important;
}

/* Cover cases where Streamlit renders a small pill by centering the tab group */
.stApp [role="tablist"],
.stApp [data-baseweb="tab-list"],
.stApp .stTabs [data-baseweb="tab-list"] {
    max-width: 1200px !important;
    margin-left: auto !important;
    margin-right: auto !important;
}

/* Tighten spacing so tabs appear as a single connected bar on wide screens */
@media (min-width: 800px) {
    [role="tablist"] {
        gap: 18px !important;
        padding: 10px 14px !important;
    }
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
    border: 1px solid rgba(148, 163, 184, 0.12) !important;
    border-radius: 14px !important;
    background: rgba(8, 28, 45, 0.5) !important;
    overflow: hidden;
}

[data-testid="stExpander"] details {
    background: transparent !important;
}

[data-testid="stExpander"] summary {
    background: rgba(12, 28, 44, 0.78) !important;
    color: #e8f4ff !important;
    border-bottom: 1px solid rgba(148, 163, 184, 0.1) !important;
    font-weight: 700 !important;
}

[data-testid="stExpander"] summary * {
    color: #e8f4ff !important;
}

[data-testid="stExpander"] details > div:last-child {
    background: rgba(7, 24, 39, 0.72) !important;
    color: #e8f4ff !important;
}

[data-testid="stExpander"] details > div:last-child * {
    color: #e8f4ff !important;
}

/* Remove any accidental divider bars inside expander content. */
[data-testid="stExpander"] hr {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    border: 0 !important;
}

[data-testid="stChatInput"] {
    border: 1px solid rgba(129, 140, 248, 0.16) !important;
    border-radius: 18px !important;
    background:
        radial-gradient(circle at 8% 0%, rgba(99, 102, 241, 0.07), transparent 38%),
        linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
    box-shadow: 0 8px 18px rgba(2, 6, 23, 0.24), inset 0 0 0 1px rgba(255,255,255,0.02) !important;
    transition: border-color 220ms ease, box-shadow 220ms ease, transform 220ms ease !important;
    animation: chatInputReveal 260ms ease;
}

/* Blend the entire chat-input footer area with the dark app canvas. */
[data-testid="stChatInputContainer"],
.stChatFloatingInputContainer,
.stChatInputContainer {
    position: relative !important;
    background:
        linear-gradient(180deg, rgba(3, 17, 29, 0.06), rgba(3, 17, 29, 0.98)) !important;
    border-top: 1px solid rgba(148, 163, 184, 0.08) !important;
    padding-bottom: 1rem !important;
}

[data-testid="stChatInput"] > div,
[data-testid="stChatInputContainer"] {
    background: transparent !important;
    border-radius: 18px !important;
    padding: 6px 8px !important;
}

[data-testid="stChatInputContainer"]::before,
.stChatFloatingInputContainer::before,
.stChatInputContainer::before {
    content: "";
    position: absolute;
    inset: -40px 0 0 0;
    background:
        linear-gradient(180deg, transparent 0%, rgba(3, 17, 29, 0.88) 36%, rgba(3, 17, 29, 1) 100%);
    pointer-events: none;
    z-index: -1;
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

.top-tabs {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 8px 12px;
}

.top-tabs .stButton {
    background: transparent !important;
}

.top-tabs .stButton > button {
    border-radius: 12px !important;
    border: 1px solid rgba(148, 163, 184, 0.14) !important;
    background: rgba(255,255,255,0.02) !important;
    color: var(--text-muted) !important;
    padding: 10px 18px !important;
    font-weight: 700 !important;
    min-width: 140px !important;
}

.top-tabs .stButton > button:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #ffffff !important;
}

.top-tabs .stButton > button:active,
.top-tabs .stButton > button[aria-pressed="true"],
.top-tabs .stButton > button[aria-current="true"] {
    background: linear-gradient(135deg, var(--accent-a), var(--accent-b)) !important;
    color: white !important;
    border-color: rgba(129, 140, 248, 0.55) !important;
    box-shadow: 0 10px 22px rgba(79, 70, 229, 0.16) !important;
}

/* Structured response section styling (AI Analyst improvements) */
.structured-section {
    border: 1px solid rgba(148,163,184,0.10);
    border-radius: 12px;
    padding: 14px 16px;
    margin: 14px 0;
    backdrop-filter: blur(6px);
}

.structured-section--emphasize {
    border-color: rgba(59,130,246,0.32) !important;
    box-shadow: 0 10px 30px rgba(59,130,246,0.06) !important;
}

/* Final-answer emphasis: gently enlarge and highlight main insight without touching layout */
.structured-section--emphasize .structured-section__body {
    font-size: 1.18rem;
    font-weight: 700;
    line-height: 1.15;
    padding: 12px 6px 6px 6px !important;
    margin-top: 6px;
    border-radius: 10px;
    border: 1px solid rgba(59,130,246,0.08);
    box-shadow: 0 8px 28px rgba(59,130,246,0.04) !important;
}

.structured-section--emphasize .structured-section__body > ul,
.structured-section--emphasize .structured-section__body > li,
.structured-section--emphasize .structured-section__body p {
    font-size: 1.05rem;
    margin: 8px 0 8px 18px;
}

/* Slight header optimization: reduce height/padding and soften intensity */
.section-heading__title,
.section-title,
.section-hero__title {
    font-size: 1.25rem;
    font-weight: 700;
}

.section-heading {
    margin: 6px 0 12px;
}

/* Card-like containers: subtle radius, lighter border and inner padding consistency */
.glass-card,
.report-shell .report-list-card,
.report-config-card,
.kpi-card,
.insight-banner,
.chat-shell {
    border-radius: 16px;
    padding: 16px;
}

/* Spacing improvements: consistent vertical rhythm */
.structured-section + .structured-section,
.glass-card + .glass-card,
.insight-banner + .insight-banner,
.status-card + .status-card {
    margin-top: 16px;
}

/* Top section cleanup: make small captions and confidence indicators compact */
.stCaption {
    display: inline-block !important;
    margin-top: 6px !important;
    margin-bottom: 6px !important;
    color: var(--text-soft) !important;
}

/* Reduce intensity of Limitations detail block while keeping it open and visible */
.structured-section details {
    background: rgba(255,255,255,0.02) !important;
    border-radius: 10px;
    padding: 8px !important;
}

.structured-section details summary {
    background: transparent !important;
    color: #dbeafe !important;
    font-weight: 700 !important;
    margin-bottom: 6px !important;
}

/* Micro-interactions: gentle lift on hover for sections */
.structured-section {
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}
.structured-section:hover {
    transform: translateY(-3px);
    box-shadow: 0 18px 36px rgba(2,10,20,0.06);
    border-color: rgba(148,163,184,0.14);
}

/* Keep Limitations visually less dominant */
.structured-section[style*="rgba(234, 179, 8"] {
    opacity: 0.95;
}

/* Home page feature cards styling */
.home-page .home-card {
    background: linear-gradient(145deg, rgba(15,23,42,0.75), rgba(2,6,23,0.65)) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    transition: all 0.25s ease !important;
    border-radius: var(--card-radius) !important;
}

.home-page .home-card:hover {
    transform: translateY(-6px) !important;
    box-shadow: 0 20px 40px rgba(0,0,0,0.35) !important;
}

.structured-section__header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
}

.structured-section__icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg,var(--accent-a),var(--accent-b));
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 700;
    box-shadow: 0 8px 18px rgba(79,70,229,0.18);
}

.structured-section__title {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #e6f0ff;
    font-weight: 800;
}

.structured-section__body ul, .structured-section__body li {
    margin: 6px 0 6px 18px;
}

/* Make follow-up suggestion buttons appear as pills */
.top-tabs ~ .glass-card .stButton > button,
.structured-section + .stButton > button,
.follow-up .stButton > button,
.stMarkdownContainer .stButton > button {
    border-radius: 999px !important;
    padding: 8px 16px !important;
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(148,163,184,0.10) !important;
}

/* Tidy top area: align answer-ready, preview, and confidence into neat block */
.stCaption {
    display: block !important;
    margin-top: 8px !important;
    margin-bottom: 8px !important;
    color: var(--text-soft) !important;
}

/* Slightly soften heavy gradients for long cards to reduce visual noise */
.glass-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
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
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 32%),
        rgba(255,255,255,0.035);
    border: 1px solid var(--border-soft);
    border-radius: 22px;
    padding: 22px;
    height: 100%;
    box-shadow: 0 18px 36px rgba(2, 10, 20, 0.22);
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
    padding: 28px;
    border-radius: 24px;
    border: 1px solid rgba(125, 211, 252, 0.18);
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.24), transparent 30%),
        radial-gradient(circle at bottom left, rgba(34, 197, 94, 0.16), transparent 28%),
        linear-gradient(180deg, rgba(9, 30, 48, 0.95), rgba(7, 23, 40, 0.9));
    box-shadow: 0 24px 48px rgba(2, 10, 20, 0.26);
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
    background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.025));
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 18px;
    padding: 18px;
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
    min-height: 166px;
    position: relative;
    overflow: hidden;
    border-radius: 22px;
    background:
        radial-gradient(circle at 100% 0%, rgba(56, 189, 248, 0.09), transparent 34%),
        linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.025));
}

.kpi-card::before {
    content: "";
    position: absolute;
    inset: auto -15% -26% auto;
    width: 150px;
    height: 150px;
    background: radial-gradient(circle, rgba(34, 197, 94, 0.18), transparent 70%);
}

.kpi-card--featured {
    border-color: rgba(34, 197, 94, 0.24);
    background:
        radial-gradient(circle at top right, rgba(34, 197, 94, 0.16), transparent 32%),
        linear-gradient(180deg, rgba(20, 41, 34, 0.72), rgba(9, 29, 41, 0.8));
}

.kpi-card--featured::before {
    background: radial-gradient(circle, rgba(56, 189, 248, 0.22), transparent 68%);
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
    font-size: 34px;
    font-weight: 800;
    margin-top: 16px;
    line-height: 1.05;
    color: #f8fbff;
    letter-spacing: -0.04em;
}

/* Slightly increase prominence of KPI / main numeric values (final answers) */
.kpi-card__value,
[data-testid="stMetricValue"] {
    font-size: 38px !important;
    font-weight: 800 !important;
    text-shadow: 0 6px 18px rgba(2,6,23,0.45);
}

/* Make the main metric display more distinct with a subtle border/glow */
.kpi-card__value::after,
[data-testid="stMetricValue"]::after {
    content: "";
    display: block;
    height: 6px;
    margin-top: 8px;
    border-radius: 6px;
    background: linear-gradient(90deg, rgba(34,197,94,0.18), rgba(56,189,248,0.16));
    opacity: 0.9;
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
    padding: 24px;
    border-radius: 22px;
    border: 1px solid rgba(148, 163, 184, 0.12);
    background:
        radial-gradient(circle at top right, rgba(20, 184, 166, 0.2), transparent 32%),
        radial-gradient(circle at bottom left, rgba(56, 189, 248, 0.12), transparent 28%),
        linear-gradient(180deg, rgba(9, 30, 48, 0.92), rgba(7, 23, 40, 0.88));
}

.quick-insights-panel {
    padding: 28px;
    border-radius: 24px;
    border: 1px solid rgba(20, 184, 166, 0.18);
    background:
        radial-gradient(circle at top right, rgba(20, 184, 166, 0.24), transparent 34%),
        radial-gradient(circle at 0% 100%, rgba(56, 189, 248, 0.1), transparent 28%),
        linear-gradient(180deg, rgba(9, 30, 48, 0.92), rgba(9, 30, 48, 0.74));
    box-shadow: 0 24px 48px rgba(2, 10, 20, 0.24);
}

.quick-insights-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    margin-top: 16px;
}

.quick-insight-item {
    background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.025));
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 18px;
    padding: 18px;
}

.quick-insight-value {
    margin-top: 8px;
    font-size: 17px;
    font-weight: 700;
    color: #f8fbff;
    line-height: 1.45;
}

.chat-shell {
    border: 1px solid rgba(148, 163, 184, 0.1);
    border-radius: 24px;
    padding: 24px;
    background:
        radial-gradient(circle at top left, rgba(20, 184, 166, 0.12), transparent 34%),
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.1), transparent 28%),
        linear-gradient(180deg, rgba(7, 23, 40, 0.96), rgba(9, 30, 48, 0.88));
    box-shadow: 0 24px 48px rgba(2, 10, 20, 0.24);
}

.ai-theme-box {
    margin-top: 10px;
    margin-bottom: 10px;
    padding: 10px;
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.12);
    background:
        radial-gradient(circle at 0% 0%, rgba(148, 163, 184, 0.06), transparent 34%),
        linear-gradient(180deg, rgba(9, 24, 45, 0.82), rgba(7, 18, 33, 0.88));
    box-shadow: 0 6px 12px rgba(2, 6, 23, 0.2);
}

/* Soft separator for structured response sections. */
.soft-divider {
    height: 1px;
    margin: 14px 0 10px;
    background: linear-gradient(90deg, rgba(148, 163, 184, 0.03), rgba(148, 163, 184, 0.28), rgba(148, 163, 184, 0.03));
    border-radius: 999px;
}

/* Main navigation as a joined segmented control spanning the full row. */
.top-tabs {
    width: 100%;
    margin: 24px 0 18px;
    padding: 0;
}

.top-tabs [data-testid="stHorizontalBlock"] {
    gap: 0 !important;
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.12), transparent 36%),
        linear-gradient(180deg, rgba(9, 24, 41, 0.98), rgba(6, 18, 30, 0.98));
    border: 1px solid rgba(125, 211, 252, 0.16);
    border-radius: 24px;
    padding: 8px;
    overflow: hidden;
    box-shadow: 0 18px 36px rgba(2, 10, 20, 0.22);
}

.top-tabs [data-testid="stColumn"] {
    width: 100%;
}

.top-tabs [data-testid="stColumn"]:not(:last-child) {
    border-right: 1px solid rgba(125, 211, 252, 0.1);
}

.top-tabs [data-testid="stColumn"] .stButton {
    height: 100%;
}

.top-tabs [data-testid="stColumn"] .stButton > button {
    width: 100%;
    min-height: 72px;
    border-radius: 18px !important;
    border: 1px solid transparent !important;
    background:
        radial-gradient(circle at top right, rgba(255,255,255,0.06), transparent 34%),
        linear-gradient(180deg, rgba(13, 31, 49, 0.96), rgba(8, 21, 34, 0.98)) !important;
    color: rgba(226, 232, 240, 0.82) !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    box-shadow: none !important;
    transform: none !important;
}

.top-tabs [data-testid="stColumn"] .stButton > button:hover {
    border-color: rgba(125, 211, 252, 0.18) !important;
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.12), transparent 34%),
        linear-gradient(180deg, rgba(16, 37, 58, 0.98), rgba(9, 24, 38, 0.98)) !important;
    color: #f8fbff !important;
}

.top-tabs [data-testid="stColumn"]:nth-child(1) .stButton > button[kind="primary"] {
    border-color: rgba(56, 189, 248, 0.34) !important;
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.18), transparent 34%),
        linear-gradient(180deg, rgba(15, 43, 66, 0.98), rgba(8, 25, 40, 0.98)) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(56, 189, 248, 0.14) !important;
    color: #ffffff !important;
}

.top-tabs [data-testid="stColumn"]:nth-child(2) .stButton > button[kind="primary"] {
    border-color: rgba(167, 139, 250, 0.34) !important;
    background:
        radial-gradient(circle at top right, rgba(167, 139, 250, 0.2), transparent 34%),
        linear-gradient(180deg, rgba(33, 28, 60, 0.98), rgba(15, 19, 36, 0.98)) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(167, 139, 250, 0.14) !important;
    color: #ffffff !important;
}

.top-tabs [data-testid="stColumn"]:nth-child(3) .stButton > button[kind="primary"] {
    border-color: rgba(245, 158, 11, 0.34) !important;
    background:
        radial-gradient(circle at top right, rgba(245, 158, 11, 0.18), transparent 34%),
        linear-gradient(180deg, rgba(57, 39, 18, 0.98), rgba(26, 20, 15, 0.98)) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(245, 158, 11, 0.14) !important;
    color: #ffffff !important;
}

.top-tabs [data-testid="stColumn"]:nth-child(4) .stButton > button[kind="primary"] {
    border-color: rgba(52, 211, 153, 0.34) !important;
    background:
        radial-gradient(circle at top right, rgba(52, 211, 153, 0.18), transparent 34%),
        linear-gradient(180deg, rgba(16, 49, 44, 0.98), rgba(11, 24, 28, 0.98)) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(52, 211, 153, 0.14) !important;
    color: #ffffff !important;
}

@media (max-width: 900px) {
    .landing-hero {
        grid-template-columns: 1fr;
    }

    .top-tabs [data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px !important;
    }

    .top-tabs [data-testid="stColumn"]:not(:last-child) {
        border-right: 0;
    }

    .top-tabs [data-testid="stColumn"] .stButton > button {
        min-height: 56px;
        padding: 14px 14px !important;
    }

    .section-hero__title,
    .landing-hero__title {
        font-size: 2rem;
    }
}

.ai-theme-box .stButton > button {
    background: rgba(20, 35, 58, 0.62) !important;
    border: 1px solid rgba(148, 163, 184, 0.2) !important;
}

.ai-theme-box .stButton > button:hover {
    background: rgba(30, 47, 76, 0.78) !important;
    border-color: rgba(148, 163, 184, 0.34) !important;
}

/* Make Try Asking suggestions feel like clear action chips, not input boxes. */
.try-box {
    cursor: pointer;
    transition: all 0.2s ease;
}

.try-box:hover {
    background: rgba(255, 255, 255, 0.05);
}

.try-asking-section .stButton > button {
    border-radius: 999px !important;
    min-height: 34px !important;
    padding: 0 12px !important;
    font-size: 12px !important;
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(148, 163, 184, 0.22) !important;
}

.try-asking-section .stButton > button:hover {
    background: rgba(255, 255, 255, 0.09) !important;
    border-color: rgba(148, 163, 184, 0.36) !important;
}

/* Make follow-up / suggestion buttons consistent as pills with subtle hover */
.follow-up .stButton > button,
.suggestion-chip .stButton > button,
.stMarkdownContainer .stButton > button {
    border-radius: 999px !important;
    padding: 8px 14px !important;
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(148,163,184,0.10) !important;
    transition: transform 0.14s ease, box-shadow 0.14s ease, background 0.14s ease;
}

.follow-up .stButton > button:hover,
.suggestion-chip .stButton > button:hover,
.stMarkdownContainer .stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 20px rgba(2,6,23,0.12);
    background: rgba(255,255,255,0.06) !important;
}

/* Compact the quality/confidence badge to a single-line compact layout on small widths */
@media (max-width: 780px) {
    .stSidebar .stMarkdown, .stCaption {
        display: block !important;
    }
    .stCaption {
        font-size: 12px !important;
    }
}

.chat-hero {
    display: flex;
    justify-content: space-between;
    gap: 22px;
    align-items: center;
    margin-bottom: 18px;
}

.chat-hero__title {
    margin-top: 10px;
    font-size: 30px;
    font-weight: 800;
    color: #f8fbff;
    font-family: 'Sora', 'Segoe UI', sans-serif;
    letter-spacing: -0.03em;
}

.chat-status {
    padding: 12px 16px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    color: #ebfff7;
    background: linear-gradient(135deg, rgba(34, 197, 94, 0.16), rgba(56, 189, 248, 0.12));
    border: 1px solid rgba(125, 211, 252, 0.24);
}

.typing-dots {
    display: inline-flex;
    gap: 6px;
    align-items: center;
}

.typing-dots span {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #6366f1;
    animation: pulseDots 1.2s infinite ease-in-out;
}

.typing-dots span:nth-child(2) {
    animation-delay: 0.15s;
}

.typing-dots span:nth-child(3) {
    animation-delay: 0.3s;
}

.landing-hero {
    margin-bottom: 18px;
    padding: 30px;
    border-radius: 28px;
    border: 1px solid rgba(125, 211, 252, 0.22);
    background:
        radial-gradient(circle at 12% 10%, rgba(56, 189, 248, 0.22), transparent 36%),
        radial-gradient(circle at 88% 16%, rgba(249, 115, 22, 0.18), transparent 30%),
        radial-gradient(circle at 50% 100%, rgba(34, 197, 94, 0.12), transparent 30%),
        linear-gradient(165deg, rgba(8, 36, 56, 0.96) 0%, rgba(7, 23, 40, 0.98) 68%);
    box-shadow: 0 28px 58px rgba(2, 10, 20, 0.38);
    animation: fadeSlideIn 0.5s ease;
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.9fr);
    gap: 22px;
    align-items: end;
}

.landing-hero__content {
    min-width: 0;
}

.landing-hero__kicker {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 700;
    color: #c7d2fe;
}

.landing-hero__title {
    margin-top: 10px;
    font-size: 38px;
    font-family: 'Sora', 'Segoe UI', sans-serif;
    font-weight: 800;
    line-height: 1.08;
    color: #f7fbff;
    max-width: 820px;
    letter-spacing: -0.05em;
}

.landing-hero__subtitle {
    margin-top: 14px;
    font-size: 15px;
    color: #c7d8e8;
    max-width: 760px;
    line-height: 1.7;
}

.landing-hero__badges {
    margin-top: 18px;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.landing-hero__badge {
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(125, 211, 252, 0.18);
    color: #e8f4ff;
    font-size: 12px;
    font-weight: 700;
}

.landing-hero__stats {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
}

.landing-hero__stat {
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.03));
    padding: 16px 18px;
    backdrop-filter: blur(10px);
}

.landing-hero__stat-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #9ec2da;
}

.landing-hero__stat-value {
    margin-top: 6px;
    font-size: 24px;
    font-weight: 800;
    color: #f7fbff;
    letter-spacing: -0.03em;
}

.sidebar-dataset-card {
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.16), transparent 34%),
        linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
    padding: 14px;
    border-radius: 16px;
    border: 1px solid rgba(125, 211, 252, 0.22);
    margin-bottom: 10px;
    box-shadow: 0 0 0 1px rgba(125, 211, 252, 0.08), 0 16px 32px rgba(2, 6, 23, 0.22);
}

.table-panel .stTextInput,
.table-panel .stSelectbox,
.table-panel [data-testid="stToggle"] {
    margin-top: 0.2rem;
}

.table-panel .section-title {
    margin-bottom: 0;
}

.insight-block {
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.12), transparent 34%),
        linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.025));
}

.insight-banner {
    margin: 12px 0 16px;
    padding: 18px 20px;
    border-radius: 18px;
    border: 1px solid rgba(56, 189, 248, 0.2);
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.16), transparent 30%),
        linear-gradient(180deg, rgba(8, 28, 45, 0.88), rgba(7, 23, 40, 0.82));
    box-shadow: 0 18px 34px rgba(2, 10, 20, 0.22);
}

.insight-banner__eyebrow {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #9fd2f1;
    font-weight: 800;
}

.insight-banner__body {
    margin-top: 8px;
    color: var(--text-main);
    font-size: 0.97rem;
    line-height: 1.7;
    font-weight: 600;
}

.status-card {
    margin: 12px 0 14px;
    padding: 14px 16px;
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    background: rgba(255, 255, 255, 0.04);
}

.status-card__title {
    color: var(--text-main);
    font-weight: 800;
    font-size: 0.95rem;
}

.status-card__body {
    margin-top: 6px;
    color: var(--text-muted);
    font-size: 0.92rem;
    line-height: 1.6;
}

.status-card--success {
    border-color: rgba(16, 185, 129, 0.24);
    background: rgba(16, 185, 129, 0.08);
}

.status-card--warning {
    border-color: rgba(245, 158, 11, 0.24);
    background: rgba(245, 158, 11, 0.08);
}

.status-card--info {
    border-color: rgba(56, 189, 248, 0.22);
    background: rgba(56, 189, 248, 0.08);
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
    min-height: 38px !important;
    min-width: 38px !important;
    width: auto !important;
    padding: 0 14px !important;
    border-radius: 999px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 6px !important;
    line-height: 1 !important;
    box-shadow: 0 10px 18px rgba(79, 70, 229, 0.24) !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover,
[data-testid="stSidebar"] [data-testid="stFileUploader"] div[role="button"]:hover {
    background: linear-gradient(135deg, #7c83ff, #8b5cf6) !important;
    border-color: rgba(224, 231, 255, 0.9) !important;
    filter: saturate(1.08);
    transform: translateY(-1px);
    box-shadow: 0 14px 24px rgba(79, 70, 229, 0.3) !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button:active,
[data-testid="stSidebar"] [data-testid="stFileUploader"] div[role="button"]:active {
    transform: translateY(0) scale(0.98);
    box-shadow: 0 8px 16px rgba(79, 70, 229, 0.2) !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button:focus-visible,
[data-testid="stSidebar"] [data-testid="stFileUploader"] div[role="button"]:focus-visible {
    outline: 2px solid rgba(224, 231, 255, 0.95) !important;
    outline-offset: 2px !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button svg,
[data-testid="stSidebar"] [data-testid="stFileUploader"] div[role="button"] svg {
    width: 15px !important;
    height: 15px !important;
    flex-shrink: 0;
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
</style>
"""


def inject_styles(st):
    st.markdown(TAILWIND_CDN, unsafe_allow_html=True)
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
