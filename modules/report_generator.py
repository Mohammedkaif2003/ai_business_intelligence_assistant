try:
    import kaleido
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "kaleido"])

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, Image,
    PageBreak, HRFlowable, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate
from datetime import datetime
import pandas as pd
import os
import plotly.express as px
from io import BytesIO
import re


# ═══════════════════════════════════════════════════
#  BRAND COLORS
# ═══════════════════════════════════════════════════

BRAND_DARK = colors.HexColor("#1E293B")       # Dark navy
BRAND_PRIMARY = colors.HexColor("#2563EB")     # Blue accent
BRAND_LIGHT = colors.HexColor("#3B82F6")       # Lighter blue
BRAND_GOLD = colors.HexColor("#F59E0B")        # Gold accent
BRAND_GREEN = colors.HexColor("#10B981")       # Green for positive
BRAND_RED = colors.HexColor("#EF4444")         # Red for alerts
BRAND_GRAY = colors.HexColor("#64748B")        # Muted gray
BRAND_BG = colors.HexColor("#F8FAFC")          # Light background
TABLE_HEADER_BG = colors.HexColor("#1E3A5F")   # Deep blue for table headers
TABLE_ROW_ALT = colors.HexColor("#F1F5F9")     # Alternating row color


# ═══════════════════════════════════════════════════
#  CUSTOM STYLES
# ═══════════════════════════════════════════════════

def get_custom_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=26,
        textColor=BRAND_DARK,
        spaceAfter=4,
        alignment=TA_LEFT,
        leading=32,
    ))

    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        fontName="Helvetica",
        fontSize=12,
        textColor=BRAND_GRAY,
        spaceAfter=20,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=BRAND_PRIMARY,
        spaceBefore=16,
        spaceAfter=8,
        leading=20,
        borderPadding=(0, 0, 4, 0),
    ))

    styles.add(ParagraphStyle(
        name="SubSection",
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=BRAND_DARK,
        spaceBefore=10,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="BodyText2",
        fontName="Helvetica",
        fontSize=10,
        textColor=BRAND_DARK,
        spaceAfter=6,
        leading=14,
    ))

    styles.add(ParagraphStyle(
        name="InsightBox",
        fontName="Helvetica-Oblique",
        fontSize=10,
        textColor=BRAND_DARK,
        spaceAfter=6,
        leading=14,
        borderColor=BRAND_PRIMARY,
        borderWidth=1,
        borderPadding=10,
        backColor=colors.HexColor("#EFF6FF"),
    ))

    styles.add(ParagraphStyle(
        name="RecItem",
        fontName="Helvetica",
        fontSize=10,
        textColor=BRAND_DARK,
        spaceAfter=4,
        leading=14,
        leftIndent=16,
        bulletIndent=6,
    ))

    styles.add(ParagraphStyle(
        name="FooterStyle",
        fontName="Helvetica",
        fontSize=8,
        textColor=BRAND_GRAY,
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name="QueryNum",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.white,
        spaceBefore=0,
        spaceAfter=0,
    ))

    styles.add(ParagraphStyle(
        name="QueryText",
        fontName="Helvetica-Oblique",
        fontSize=12,
        leading=16,
        textColor=BRAND_DARK,
        spaceBefore=12,
        spaceAfter=16,
        leftIndent=8,
        borderColor=BRAND_GOLD,
        borderWidth=2,
        borderPadding=10,
        backColor=colors.HexColor("#FFFBEB"),
    ))

    styles.add(ParagraphStyle(
        name="TOCItem",
        fontName="Helvetica",
        fontSize=11,
        textColor=BRAND_DARK,
        spaceBefore=6,
        spaceAfter=6,
        leftIndent=20,
        leading=16,
    ))

    styles.add(ParagraphStyle(
        name="CoverDate",
        fontName="Helvetica",
        fontSize=11,
        textColor=colors.white,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name="AIResponse",
        fontName="Helvetica",
        fontSize=10,
        textColor=BRAND_DARK,
        spaceAfter=8,
        leading=15,
        borderColor=BRAND_GREEN,
        borderWidth=2,
        borderPadding=12,
        backColor=colors.HexColor("#F0FDF4"),
    ))

    styles.add(ParagraphStyle(
        name="AIResponseLabel",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=BRAND_GREEN,
        spaceBefore=8,
        spaceAfter=4,
    ))

    return styles


# ═══════════════════════════════════════════════════
#  PAGE HEADER & FOOTER
# ═══════════════════════════════════════════════════

def add_page_decoration(canvas, doc):
    """Add header bar and page number to every page."""
    canvas.saveState()

    # Top accent bar
    canvas.setFillColor(BRAND_PRIMARY)
    canvas.rect(0, A4[1] - 8, A4[0], 8, fill=True, stroke=False)

    # Bottom bar
    canvas.setFillColor(BRAND_DARK)
    canvas.rect(0, 0, A4[0], 30, fill=True, stroke=False)

    # Footer text
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(
        A4[0] / 2, 10,
        f"AI Business Intelligence Report  •  Page {doc.page}  •  Confidential"
    )

    canvas.restoreState()


def add_first_page_decoration(canvas, doc):
    """Cover page — no header, just the accent bar."""
    canvas.saveState()

    # Top accent bar (thicker for cover)
    canvas.setFillColor(BRAND_PRIMARY)
    canvas.rect(0, A4[1] - 12, A4[0], 12, fill=True, stroke=False)

    # Bottom bar
    canvas.setFillColor(BRAND_DARK)
    canvas.rect(0, 0, A4[0], 30, fill=True, stroke=False)

    # Footer
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(A4[0] / 2, 10, "AI Business Intelligence Report  •  Confidential")

    canvas.restoreState()


# ═══════════════════════════════════════════════════
#  SECTION DIVIDER
# ═══════════════════════════════════════════════════

def section_divider():
    return HRFlowable(
        width="100%",
        thickness=1.5,
        color=BRAND_PRIMARY,
        spaceBefore=10,
        spaceAfter=10
    )


def thin_divider():
    return HRFlowable(
        width="100%",
        thickness=0.5,
        color=colors.HexColor("#E2E8F0"),
        spaceBefore=6,
        spaceAfter=6
    )


# ═══════════════════════════════════════════════════
#  CHART GENERATION
# ═══════════════════════════════════════════════════

def clean_chart_title(title: str, max_len=60) -> str:
    """Remove special chars and truncate for chart titles."""
    title = str(title).replace("&", "and").replace("<", "").replace(">", "")
    title = title.replace("\n", " ").replace("\r", " ")
    return title[:max_len] + ("..." if len(title) > max_len else "")


def get_chart_columns(df):
    """Detect the correct x (category) and y (numeric) columns from a result DataFrame."""
    # Exclude stray index columns
    clean_cols = [c for c in df.columns if str(c).lower() not in ("index", "level_0")]
    df = df[clean_cols]

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime", "datetime64"]).columns.tolist()

    # Remove datetime from categorical
    categorical_cols = [c for c in categorical_cols if c not in datetime_cols]

    if datetime_cols and numeric_cols:
        return datetime_cols[0], numeric_cols[0], "line"
    elif categorical_cols and numeric_cols:
        return categorical_cols[0], numeric_cols[0], "bar"
    elif len(numeric_cols) >= 2:
        return numeric_cols[0], numeric_cols[1], "scatter"
    elif len(numeric_cols) == 1:
        return None, numeric_cols[0], "hist"
    else:
        return None, None, None


def create_chart_image(df, title="", width=900, height=450):
    """Create a clean PNG chart image from a result DataFrame for PDF embedding."""
    # Step 1 — normalise to DataFrame
    if isinstance(df, pd.Series):
        df = df.reset_index()
        if df.shape[1] == 2:
            df.columns = ["Category", "Value"]
    elif isinstance(df, pd.DataFrame):
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index()
        else:
            # Only reset index if the index is meaningful (non-default)
            if not isinstance(df.index, pd.RangeIndex) or df.index.name is not None:
                df = df.reset_index()
            # Drop the integer index column if it crept in
            if "index" in df.columns:
                df = df.drop(columns=["index"])
    df = df.copy()

    # Step 2 — drop any column literally named "index" or "level_0"
    drop_cols = [c for c in df.columns if str(c).lower() in ("index", "level_0")]
    df = df.drop(columns=drop_cols, errors="ignore")

    # Step 3 — detect chart type from the CLEANED df
    x_col, y_col, chart_type = get_chart_columns(df)
    if x_col is None and y_col is None:
        return None

    # Step 4 — build chart
    if chart_type == "bar":
        if len(df) > 20:
            df = df.nlargest(20, y_col)
        df = df.sort_values(y_col, ascending=False)

        # Use horizontal bar if category labels are long (avg > 10 chars)
        avg_label_len = df[x_col].astype(str).str.len().mean()
        if avg_label_len > 10 or len(df) > 10:
            # Horizontal bar — easier to read long labels
            fig = px.bar(
                df, x=y_col, y=x_col,
                orientation="h",
                title=title or f"{y_col} by {x_col}",
                template="plotly_white",
                color_discrete_sequence=["#2563EB"]
            )
            fig.update_layout(
                yaxis=dict(categoryorder="total ascending"),
                xaxis_title=y_col,
                yaxis_title=x_col,
                margin=dict(l=160, r=30, t=60, b=40),
                height=max(400, len(df) * 28),   # auto height based on row count
                width=width,
                font=dict(size=11)
            )
        else:
            # Vertical bar for short labels / few items
            fig = px.bar(
                df, x=x_col, y=y_col,
                title=title or f"{y_col} by {x_col}",
                template="plotly_white",
                color_discrete_sequence=["#2563EB"]
            )
            fig.update_layout(
                xaxis_tickangle=-35,
                xaxis_title=x_col,
                yaxis_title=y_col,
                margin=dict(l=60, r=30, t=60, b=120),
                height=height,
                width=width,
                font=dict(size=11)
            )

    elif chart_type == "line":
        fig = px.line(
            df, x=x_col, y=y_col,
            title=title or f"{y_col} over {x_col}",
            template="plotly_white",
            color_discrete_sequence=["#2563EB"]
        )
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col,
            margin=dict(l=60, r=30, t=60, b=60),
            height=height,
            width=width
        )

    elif chart_type == "hist":
        fig = px.histogram(
            df, x=y_col,
            title=title or f"Distribution of {y_col}",
            template="plotly_white",
            color_discrete_sequence=["#2563EB"]
        )
        fig.update_layout(
            xaxis_title=y_col,
            yaxis_title="Count",
            margin=dict(l=60, r=30, t=60, b=60),
            height=height,
            width=width
        )

    elif chart_type == "scatter":
        fig = px.scatter(
            df, x=x_col, y=y_col,
            title=title or f"{y_col} vs {x_col}",
            template="plotly_white",
            color_discrete_sequence=["#2563EB"]
        )
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title=y_col,
            margin=dict(l=60, r=30, t=60, b=60),
            height=height,
            width=width
        )

    else:
        return None

    # Export to PNG bytes using kaleido
    img_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
    return img_bytes


# ═══════════════════════════════════════════════════
#  RECOMMENDATIONS GENERATOR
# ═══════════════════════════════════════════════════

def generate_recommendations(dataframe):
    recommendations = []

    if dataframe is None:
        return recommendations

    if isinstance(dataframe, pd.Series):
        try:
            dataframe = dataframe.reset_index()
        except ValueError:
            pass

    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        return recommendations

    numeric_cols = dataframe.select_dtypes(include="number").columns.tolist()
    cat_cols = dataframe.select_dtypes(include=["object", "category"]).columns.tolist()

    if numeric_cols and cat_cols:
        metric = numeric_cols[0]
        category = cat_cols[0]

        try:
            grouped = dataframe.groupby(category)[metric].sum().sort_values(ascending=False)

            if len(grouped) >= 2:
                top = grouped.index[0]
                bottom = grouped.index[-1]
                recommendations.append(
                    f"Investigate why <b>{bottom}</b> underperforms compared to <b>{top}</b> and develop targeted improvement strategies."
                )
                top_share = (grouped.iloc[0] / grouped.sum()) * 100
                if top_share > 40:
                    recommendations.append(
                        f"Revenue concentration risk: <b>{top}</b> accounts for {top_share:.0f}% of total. Consider diversification."
                    )
        except:
            pass

    if numeric_cols:
        metric = numeric_cols[0]
        try:
            std = dataframe[metric].std()
            mean = dataframe[metric].mean()
            if mean != 0:
                cv = (std / mean) * 100
                if cv > 50:
                    recommendations.append(
                        f"High variability in <b>{metric}</b> (CV={cv:.0f}%). Investigate root causes and prioritize stabilization."
                    )
        except:
            pass

    if not recommendations:
        recommendations.append("Continue monitoring key metrics and schedule quarterly performance reviews.")
        recommendations.append("Establish KPI targets for the next period based on current performance baselines.")

    return recommendations


# ═══════════════════════════════════════════════════
#  BUILD ONE QUERY SECTION
# ═══════════════════════════════════════════════════

def analysis_banner(num, styles):
    banner = Table([[Paragraph(f"ANALYSIS #{num}", styles["QueryNum"])]],
                   colWidths=[6.5 * inch])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), BRAND_PRIMARY),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING", (0,0), (-1,-1), 12),
    ]))
    return banner


def _build_query_section(elements, query, summary_text, dataframe, styles, query_num=None, ai_response=None, charts=None, code=None, summary_list=None):
    """Build PDF elements for a single query analysis."""

    # Query number badge
    if query_num:
        elements.append(analysis_banner(query_num, styles))
        elements.append(Spacer(1, 10))

    # User query in a styled box
    safe_query = str(query).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    elements.append(Paragraph(f'"{safe_query}"', styles["QueryText"]))
    elements.append(Spacer(1, 8))

    # ── AI Conversational Response ──
    if ai_response and str(ai_response).strip():
        elements.append(Paragraph("🤖 AI ANALYST", styles["AIResponseLabel"]))
        clean_response = str(ai_response).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        clean_response = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', clean_response)
        clean_response = clean_response.replace("##", "")
        clean_response = clean_response.replace("\n\n", "<br/><br/>")
        clean_response = clean_response.replace("\n", "<br/>")
        elements.append(Paragraph(clean_response, styles["AIResponse"]))
        elements.append(Spacer(1, 10))

    # ── AI Insight ──
    elements.append(Paragraph("AI BUSINESS INSIGHT", styles["SectionHeader"]))
    elements.append(thin_divider())

    # Clean summary text for XML
    clean_summary = str(summary_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    clean_summary = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', clean_summary)
    if "&lt;Axes:" in clean_summary or "&lt;AxesSubplot" in clean_summary or "Axes:" in str(summary_text):
        clean_summary = "Analysis completed. See the AI Response section above for a detailed explanation."
    elements.append(Paragraph(clean_summary, styles["InsightBox"]))
    elements.append(Spacer(1, 12))

    # ── Visual Analysis ──
    if charts and isinstance(charts, list) and len(charts) > 0:
        elements.append(Paragraph("VISUAL ANALYSIS", styles["SectionHeader"]))
        elements.append(thin_divider())
        
        for fig in charts:
            try:
                # Use kaleido to export exactly what the AI generated with the same color scheme
                img_bytes = fig.to_image(format="png", width=900, height=450, scale=2)
                img_buffer = BytesIO(img_bytes)
                rl_image = Image(img_buffer, width=6.5 * inch, height=3.25 * inch)
                elements.append(rl_image)
                elements.append(Spacer(1, 12))
            except Exception as e:
                elements.append(Paragraph(f"AI Chart could not be rendered in PDF: {str(e)[:100]}", styles["BodyText2"]))
    elif isinstance(dataframe, (pd.DataFrame, pd.Series)):
        try:
            df_chart = dataframe.copy() if isinstance(dataframe, pd.DataFrame) else dataframe.copy()
            cleaned_title = clean_chart_title(query)
            img_bytes = create_chart_image(df_chart, title=cleaned_title)
            
            if img_bytes:
                elements.append(Paragraph("VISUAL ANALYSIS (AUTO-GENERATED FALLBACK)", styles["SectionHeader"]))
                elements.append(thin_divider())
                
                img_buffer = BytesIO(img_bytes)
                rl_image = Image(img_buffer, width=6.5 * inch, height=3.25 * inch)
                elements.append(rl_image)
                elements.append(Spacer(1, 8))

        except ValueError as e:
            elements.append(Paragraph(f"Chart could not be rendered: {str(e)}", styles["BodyText2"]))
        except KeyError as e:
            elements.append(Paragraph(f"Column not found for chart: {str(e)}", styles["BodyText2"]))
        except Exception as e:
            elements.append(Paragraph(f"Chart generation skipped: {str(e)[:100]}", styles["BodyText2"]))

    # ── Data Table ──
    if dataframe is not None:
        elements.append(Paragraph("DATA ANALYSIS", styles["SectionHeader"]))
        elements.append(thin_divider())

        df_table = dataframe
        if isinstance(df_table, pd.Series):
            try:
                df_table = df_table.reset_index()
            except ValueError:
                df_table = df_table.reset_index(drop=True).to_frame()

        if isinstance(df_table, pd.DataFrame):
            try:
                if isinstance(df_table.index, pd.MultiIndex):
                    df_table = df_table.reset_index()
                else:
                    df_table = df_table.reset_index(drop=True)
                
                # Cap at 20 rows
                df_table = df_table.head(20)
            except ValueError:
                df_table = df_table.head(20)

            header = [str(c)[:20] for c in df_table.columns.tolist()]
            table_data = [header]
            
            for _, row in df_table.iterrows():
                row_data = []
                for v in row.values:
                    if isinstance(v, (int, float)) and pd.notna(v):
                        if isinstance(v, float):
                            row_data.append(f"{v:,.2f}")
                        else:
                            row_data.append(f"{v:,}")
                    else:
                        row_data.append(str(v)[:25])
                table_data.append(row_data)
        else:
            table_data = [["Result"], [str(df_table)[:100]]]

        # Calculate column widths
        n_cols = len(table_data[0])
        available_width = 6.5 * inch
        col_width = available_width / n_cols

        table = Table(table_data, colWidths=[col_width] * n_cols)

        # Professional table styling
        style_commands = [
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),

            # Body Settings
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            # Grid
            ("GRID", (0, 0), (-1, 0), 0.5, colors.white),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, BRAND_PRIMARY),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("LINEBEFORE", (0, 1), (0, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("LINEAFTER", (-1, 1), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]

        if isinstance(df_table, pd.DataFrame):
            for j, col in enumerate(df_table.columns):
                if pd.api.types.is_numeric_dtype(df_table[col]):
                    style_commands.append(("ALIGN", (j, 0), (j, -1), "RIGHT"))
                else:
                    style_commands.append(("ALIGN", (j, 0), (j, -1), "LEFT"))
        else:
            style_commands.append(("ALIGN", (0, 0), (-1, -1), "CENTER"))

        # Alternating row colors
        for i in range(1, len(table_data)):
            bg = TABLE_ROW_ALT if i % 2 == 0 else colors.white
            style_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        elements.append(Spacer(1, 16))

    # ── Recommendations ──
    elements.append(Paragraph("RECOMMENDATIONS", styles["SectionHeader"]))
    elements.append(thin_divider())

    recs = generate_recommendations(dataframe)
    for i, rec in enumerate(recs, 1):
        bullet = f'<font color="{BRAND_PRIMARY.hexval()}">\u25B6</font>  {rec}'
        elements.append(Paragraph(bullet, styles["RecItem"]))

    elements.append(Spacer(1, 10))


    # ── KEY DATA FINDINGS (EXECUTIVE SUMMARY) ──
    if summary_list and isinstance(summary_list, list) and len(summary_list) > 0:
        elements.append(Paragraph("KEY DATA FINDINGS", styles["SectionHeader"]))
        elements.append(thin_divider())
        for sum_item in summary_list:
            clean_item = str(sum_item).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            clean_item = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', clean_item)
            bullet = f'<font color="{BRAND_PRIMARY.hexval()}">\u25B6</font>  {clean_item}'
            elements.append(Paragraph(bullet, styles["RecItem"]))
        elements.append(Spacer(1, 10))


def build_executive_summary_page(elements, analysis_history, styles):
    elements.append(PageBreak())
    elements.append(Paragraph("EXECUTIVE SUMMARY", styles["SectionHeader"]))
    elements.append(section_divider())
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(
        f"This report covers <b>{len(analysis_history)}</b> AI-powered analyses "
        f"conducted in this session. Key findings are summarised below.",
        styles["BodyText2"]
    ))
    elements.append(Spacer(1, 16))

    for i, entry in enumerate(analysis_history, 1):
        q = str(entry.get("query", "N/A"))[:100]
        insight = str(entry.get("insight", "")).replace("**", "")[:200]
        if insight and "Axes:" not in insight:
            summary_text = insight[:200] + ("..." if len(insight) > 200 else "")
        else:
            summary_text = "Analysis completed successfully."

        elements.append(Paragraph(
            f'<font color="{BRAND_PRIMARY.hexval()}"><b>#{i}</b></font>  {q}',
            styles["SubSection"]
        ))
        elements.append(Paragraph(summary_text, styles["BodyText2"]))
        elements.append(thin_divider())


# ═══════════════════════════════════════════════════
#  MAIN PDF GENERATOR
# ═══════════════════════════════════════════════════

def generate_pdf(query=None, summary_text=None, dataframe=None, charts=None, analysis_history=None):

    file_path = "AI_Executive_Report.pdf"

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        topMargin=1 * inch,
        bottomMargin=0.8 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    elements = []
    styles = get_custom_styles()
    timestamp = datetime.now().strftime("%B %d, %Y  •  %H:%M")

    # ══════════════════════════════════════════════
    #  COVER PAGE
    # ══════════════════════════════════════════════

    elements.append(Spacer(1, 1.5 * inch))

    # Title block with side accent
    title_table = Table(
        [[
            "",
            Paragraph("AI Business Intelligence<br/>Executive Report", styles["ReportTitle"])
        ]],
        colWidths=[6, 5.5 * inch]
    )
    title_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BRAND_PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(title_table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Generated on {timestamp}", styles["ReportSubtitle"]))
    elements.append(Spacer(1, 8))

    # Meta info box
    if analysis_history and len(analysis_history) > 0:
        n_queries = len(analysis_history)
    else:
        n_queries = 1 if query else 0

    meta_data = [
        ["Report Type", "Executive Analytics Report"],
        ["Analyses Included", str(n_queries)],
        ["Generated By", "AI Business Intelligence Assistant"],
        ["Classification", "Confidential"],
    ]

    meta_table = Table(meta_data, colWidths=[1.8 * inch, 4 * inch])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_GRAY),
        ("TEXTCOLOR", (1, 0), (1, -1), BRAND_DARK),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E2E8F0")),
        ("LINEBELOW", (0, -1), (-1, -1), 1, BRAND_PRIMARY),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(meta_table)

    # ── Table of Contents ──
    # ── Table of Contents ──
    if analysis_history and len(analysis_history) > 0:
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("CONTENTS", styles["SectionHeader"]))
        elements.append(section_divider())

        for i, entry in enumerate(analysis_history, 1):
            q_text = str(entry.get("query", "N/A"))[:80]
            elements.append(Paragraph(
                f'<font color="{BRAND_PRIMARY.hexval()}"><b>Analysis #{i}</b></font>  —  {q_text}',
                styles["TOCItem"]
            ))

    # ══════════════════════════════════════════════
    #  ANALYSIS SECTIONS
    # ══════════════════════════════════════════════

    if analysis_history and len(analysis_history) > 0:

        for i, entry in enumerate(analysis_history, 1):
            elements.append(PageBreak())

            _build_query_section(
                elements=elements,
                query=entry.get("query", "N/A"),
                summary_text=entry.get("insight", "N/A"),
                dataframe=entry.get("result"),
                styles=styles,
                query_num=i,
                ai_response=entry.get("ai_response", ""),
                charts=entry.get("charts", []),
                code=entry.get("code", ""),
                summary_list=entry.get("summary", [])
            )

        # Build Executive Summary Page
        if len(analysis_history) > 1:
            build_executive_summary_page(elements, analysis_history, styles)

    elif query is not None:

        elements.append(PageBreak())

        _build_query_section(
            elements=elements,
            query=query,
            summary_text=summary_text,
            dataframe=dataframe,
            styles=styles,
            charts=charts,
            code="",
            summary_list=[]
        )

    else:
        elements.append(PageBreak())
        elements.append(Paragraph("No analysis data available.", styles["BodyText2"]))

    # ══════════════════════════════════════════════
    #  DISCLAIMER PAGE
    # ══════════════════════════════════════════════

    elements.append(PageBreak())
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph("DISCLAIMER", styles["SectionHeader"]))
    elements.append(section_divider())
    elements.append(Paragraph(
        "This report was generated by an AI-powered Business Intelligence system. "
        "The insights, recommendations, and forecasts contained herein are based on "
        "automated analysis of the provided dataset and should be validated by domain "
        "experts before making strategic business decisions. Past performance does not "
        "guarantee future results.",
        styles["BodyText2"]
    ))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        f"Report generated on {timestamp} using AI Business Intelligence Assistant.",
        styles["BodyText2"]
    ))

    # ══════════════════════════════════════════════
    #  BUILD PDF
    # ══════════════════════════════════════════════

    doc.build(
        elements,
        onFirstPage=add_first_page_decoration,
        onLaterPages=add_page_decoration
    )

    return file_path