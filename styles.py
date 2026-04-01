TAILWIND_CDN = '<script src="https://cdn.tailwindcss.com"></script>'

CUSTOM_CSS = """
<style>

:root {
    --bg-app: #09111f;
    --bg-panel: rgba(15, 23, 42, 0.82);
    --bg-panel-strong: rgba(15, 23, 42, 0.96);
    --bg-soft: rgba(148, 163, 184, 0.08);
    --border-soft: rgba(148, 163, 184, 0.16);
    --text-main: #f5f9ff;
    --text-muted: #c6d3ea;
    --accent-a: #4f46e5;
    --accent-b: #7c3aed;
    --accent-c: #f97316;
    --success: #10b981;
}

html, body, .stApp {
    background: #020617 !important;
    color: var(--text-main);
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(79, 70, 229, 0.18) 0%, transparent 32%),
        linear-gradient(180deg, #11162a 0%, #09111f 52%, #050b17 100%);
}

.block-container {
    max-width: 1280px;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #101625 0%, #0c1320 100%);
    border-right: 1px solid rgba(148, 163, 184, 0.08);
}

h1, h2, h3, h4, h5, h6 {
    color: #f8fbff !important;
    letter-spacing: -0.02em;
}

p, span, label, div {
    color: inherit;
}

small, .stCaption {
    color: var(--text-muted) !important;
}

[data-testid="stMarkdownContainer"],
[data-testid="stText"],
.stMarkdown,
.stCaptionContainer,
li {
    color: var(--text-main) !important;
}

.glass-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.028));
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
    background: linear-gradient(180deg, rgba(99, 102, 241, 0.08), rgba(15, 23, 42, 0.35));
    border: 1px solid rgba(99, 102, 241, 0.12);
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

[data-testid="stSidebar"] * {
    color: #edf4ff !important;
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
    border-color: rgba(99, 102, 241, 0.28);
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--accent-a), var(--accent-b)) !important;
    color: white !important;
    border-color: rgba(129, 140, 248, 0.55) !important;
    box-shadow: 0 10px 22px rgba(79, 70, 229, 0.22);
}

.stTabs [data-baseweb="tab"]::after {
    content: "";
    position: absolute;
    left: 24%;
    right: 24%;
    bottom: 4px;
    height: 2px;
    border-radius: 999px;
    background: rgba(255,255,255,0.9);
    transform: scaleX(0);
    transition: transform 0.22s ease;
}

.stTabs [aria-selected="true"]::after {
    transform: scaleX(1);
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
    background: linear-gradient(135deg, #ef4444, #f97316) !important;
    border: none !important;
    color: white !important;
}

[data-testid="stSidebar"] .stRadio > div,
[data-baseweb="select"] > div,
[data-baseweb="select"] [role="combobox"],
.stSelectbox div[data-baseweb="select"],
.stTextInput > div > div > input,
.stNumberInput input {
    background: #182132 !important;
    color: #f8fbff !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}

.stTextInput > label,
.stSelectbox > label,
.stNumberInput > label {
    color: #dbeafe !important;
}

.stTextInput input::placeholder {
    color: #8fa5c7 !important;
    opacity: 1;
}

[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
    background: #182132 !important;
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.1);
}

[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
    background: #182132 !important;
}

[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
    background: #182132 !important;
}

[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] * {
    color: #f8fbff !important;
}

[data-testid="stSidebar"] .stSelectbox input,
[data-testid="stSidebar"] .stSelectbox span,
[data-testid="stSidebar"] .stSelectbox svg {
    color: #f8fbff !important;
    fill: #f8fbff !important;
}

[data-testid="stSidebar"] .stSelectbox button,
[data-testid="stSidebar"] .stSelectbox input {
    background: #182132 !important;
}

[data-testid="stSidebar"] .stSelectbox {
    background: transparent !important;
}

[data-baseweb="popover"] {
    background: #0f172a !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(148, 163, 184, 0.14);
    box-shadow: 0 16px 40px rgba(2, 6, 23, 0.55) !important;
}

[data-testid="stSidebar"] [data-baseweb="popover"],
[role="listbox"],
[data-baseweb="menu"],
[data-baseweb="menu"] ul,
[data-baseweb="menu"] li,
[data-testid="stSidebar"] [role="listbox"],
[data-testid="stSidebar"] ul,
[data-testid="stSidebar"] li {
    background: #0f172a !important;
    color: #f8fbff !important;
}

div[data-baseweb="popover"] {
    background: #0f172a !important;
}

div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] [role="option"],
div[data-baseweb="popover"] [role="listbox"],
div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] > div > div {
    background: #0f172a !important;
    color: #f8fbff !important;
}

[data-baseweb="option"] {
    background: #0f172a !important;
    color: #f8fbff !important;
}

[data-baseweb="option"]:hover {
    background: rgba(99,102,241,0.18) !important;
}

[data-baseweb="select"] [aria-expanded="true"],
[data-baseweb="select"] [role="combobox"] {
    background: #182132 !important;
    color: #f8fbff !important;
}

[data-baseweb="select"] svg,
.stSelectbox svg {
    fill: #f8fbff !important;
    color: #f8fbff !important;
}

[role="option"] {
    background: #0f172a !important;
    color: #f8fbff !important;
}

[role="option"]:hover,
[role="option"][aria-selected="true"] {
    background: rgba(99,102,241,0.18) !important;
    color: #ffffff !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] {
    box-shadow: none !important;
}

[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px dashed rgba(255,255,255,0.15) !important;
    border-radius: 14px !important;
    padding: 18px !important;
}

[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploader"] section,
[data-testid="stFileUploader"] > div {
    background: transparent !important;
    border: none !important;
}

[data-testid="stFileUploader"] div[role="button"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 10px !important;
}

[data-testid="stFileUploader"] span {
    color: #94A3B8 !important;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid var(--border-soft);
    background: var(--bg-panel-strong) !important;
}

[data-testid="stDataFrame"] div[data-testid="stDataFrameResizable"],
[data-testid="stDataFrame"] [role="grid"],
[data-testid="stDataFrame"] canvas {
    background: var(--bg-panel-strong) !important;
}

[data-testid="stDataFrame"] [role="columnheader"],
[data-testid="stDataFrame"] [role="gridcell"],
[data-testid="stDataFrame"] [role="rowheader"] {
    background: transparent !important;
    color: #dbeafe !important;
    border-color: rgba(148, 163, 184, 0.12) !important;
}

[data-testid="stDataFrame"] [role="columnheader"] {
    background: rgba(79, 70, 229, 0.12) !important;
    color: #f8fbff !important;
    font-weight: 700 !important;
    position: sticky !important;
    top: 0;
    z-index: 3;
}

[data-testid="stDataFrame"] [role="gridcell"] {
    font-size: 0.95rem !important;
    color: #eef5ff !important;
    background: rgba(15, 23, 42, 0.88) !important;
}

[data-testid="stDataFrame"] [role="row"]:nth-child(even) [role="gridcell"] {
    background: rgba(20, 31, 52, 0.96) !important;
}

[data-testid="stDataFrame"] [role="row"]:hover [role="gridcell"] {
    background: rgba(59, 130, 246, 0.12) !important;
}

[data-testid="stDataFrame"] [data-testid="StyledCell"],
[data-testid="stDataFrame"] [data-testid="stDataFrameCell"] {
    background: rgba(15, 23, 42, 0.92) !important;
    color: #eef5ff !important;
}

[data-testid="stDataFrame"] [data-testid="StyledCell"]:nth-child(even),
[data-testid="stDataFrame"] [data-testid="stDataFrameCell"]:nth-child(even) {
    background: rgba(20, 31, 52, 0.96) !important;
}

[data-testid="stExpander"] {
    border: 1px solid var(--border-soft);
    border-radius: 14px;
    background: rgba(255,255,255,0.03);
}

[data-testid="stExpander"] details {
    background: #161f2f !important;
    border-radius: 14px !important;
}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary *,
[data-testid="stExpander"] details > div:first-child,
[data-testid="stExpander"] details > div:first-child * {
    background: #202a3b !important;
    color: #f8fbff !important;
}

[data-testid="stExpander"] * {
    color: #eef5ff !important;
}

[data-testid="stExpander"] details summary {
    background: #202a3b !important;
    color: #f8fbff !important;
    padding-top: 0.4rem;
    padding-bottom: 0.4rem;
}

[data-testid="stExpander"] details > div:last-child,
[data-testid="stExpander"] details > div:last-child *,
[data-testid="stExpander"] [role="button"] {
    background: #161f2f !important;
    color: #eef5ff !important;
}

[data-testid="stAlert"] {
    border-radius: 14px;
}

.stCodeBlock,
.stCode,
[data-testid="stCodeBlock"],
[data-testid="stCode"] {
    background: #131b2b !important;
    border: 1px solid rgba(148, 163, 184, 0.14) !important;
    border-radius: 14px !important;
}

pre,
code,
.stCodeBlock pre,
.stCodeBlock code,
[data-testid="stCodeBlock"] pre,
[data-testid="stCodeBlock"] code {
    background: #131b2b !important;
    color: #eaf2ff !important;
}

.stCodeBlock span,
[data-testid="stCodeBlock"] span,
pre span,
code span {
    background: transparent !important;
    color: inherit !important;
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

.report-config-card h4,
.report-list-card h4 {
    margin-top: 0;
    margin-bottom: 12px;
}

.report-config-meta {
    color: #dbe8fb;
    font-size: 13px;
    line-height: 1.6;
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
    border: 1px solid rgba(99, 102, 241, 0.16);
    background:
        radial-gradient(circle at top right, rgba(129, 140, 248, 0.16), transparent 28%),
        linear-gradient(180deg, rgba(15, 23, 42, 0.95), rgba(10, 17, 31, 0.84));
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
.report-stat-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8fb4db;
}

.forecast-stat-value,
.report-stat-value {
    margin-top: 8px;
    font-size: 24px;
    font-weight: 800;
    color: #f8fbff;
}

.forecast-stat-subtle,
.report-stat-subtle {
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
    background: radial-gradient(circle, rgba(56, 189, 248, 0.24), transparent 70%);
}

.kpi-card__topline {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
}

.kpi-card__label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #9fb2d1;
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

.kpi-card__meta {
    font-size: 12px;
    color: #a8bad8;
    margin-top: 8px;
}

.kpi-card__trend {
    display: inline-flex;
    margin-top: 10px;
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
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

.hero-chart-card {
    padding: 20px;
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.12);
    background:
        radial-gradient(circle at top right, rgba(79, 70, 229, 0.12), transparent 30%),
        linear-gradient(180deg, rgba(15, 23, 42, 0.9), rgba(12, 19, 32, 0.88));
}

.dark-table-wrap {
    overflow: auto;
    max-height: 360px;
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.12);
    background: #0f172a;
}

.dark-table {
    width: 100%;
    border-collapse: collapse;
    min-width: 720px;
}

.dark-table thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: #172033;
    color: #f8fbff;
    text-align: left;
    font-size: 12px;
    font-weight: 700;
    padding: 10px 12px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.14);
}

.dark-table tbody td {
    padding: 10px 12px;
    font-size: 12px;
    color: #e6eefc;
    border-bottom: 1px solid rgba(148, 163, 184, 0.08);
    white-space: nowrap;
}

.dark-table tbody tr.odd td {
    background: #0f172a;
}

.dark-table tbody tr.even td {
    background: #142034;
}

.dark-table tbody tr:hover td {
    background: rgba(59, 130, 246, 0.16);
}

.quick-insights-panel {
    padding: 22px;
    border-radius: 18px;
    border: 1px solid rgba(56, 189, 248, 0.14);
    background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.15), transparent 34%),
        linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.72));
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

.quick-insight-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8fb4db;
    margin-bottom: 8px;
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
        radial-gradient(circle at top left, rgba(99, 102, 241, 0.14), transparent 30%),
        linear-gradient(180deg, rgba(9, 17, 31, 0.96), rgba(15, 23, 42, 0.86));
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

.chat-hero__subtitle {
    font-size: 13px;
    color: #9fb2d1;
    margin-top: 4px;
}

.chat-status {
    padding: 10px 14px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    color: #c7f9ff;
    background: rgba(34, 211, 238, 0.09);
    border: 1px solid rgba(34, 211, 238, 0.18);
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
    background: #60a5fa;
    animation: pulseDots 1.2s infinite ease-in-out;
}

.typing-dots span:nth-child(2) {
    animation-delay: 0.15s;
}

.typing-dots span:nth-child(3) {
    animation-delay: 0.3s;
}

.sidebar-dataset-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
    padding: 12px;
    border-radius: 12px;
    border: 1px solid rgba(99,102,241,0.18);
    margin-bottom: 10px;
    box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.04), 0 12px 26px rgba(2, 6, 23, 0.22);
}

.sidebar-dataset-meta {
    margin-top: 6px;
    font-size: 12px;
    color: #9fb2d1;
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

    .report-shell {
        grid-template-columns: 1fr;
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 13px;
    }

    .quick-insights-grid {
        grid-template-columns: 1fr;
    }

    .chat-hero {
        flex-direction: column;
        align-items: flex-start;
    }

    .forecast-stat-grid,
    .report-stat-grid {
        grid-template-columns: 1fr;
    }
}

/* User-requested Awesome Animations */
@keyframes floatLoop {
    0% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
    100% { transform: translateY(0); }
}

@keyframes pulseGlow {
    0% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.4); }
    70% { box-shadow: 0 0 0 12px rgba(79, 70, 229, 0); }
    100% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0); }
}

@keyframes slideInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-float {
    animation: floatLoop 6s ease-in-out infinite;
}

.animate-pulse-glow {
    animation: pulseGlow 2s infinite;
}

.animate-slide {
    animation: slideInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
</style>
"""


def inject_styles(st):
    st.markdown(TAILWIND_CDN, unsafe_allow_html=True)
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
