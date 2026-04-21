# Changelog

All notable changes to Apex Analytics are documented in this file.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] — 2026-04-22

### Added — Compute-First Architecture
- **Deterministic analysis engine** (`modules/smart_analysis.py`): new module that handles 9 query patterns (ranking, comparison, trend, distribution, correlation, outlier, forecast, aggregate, general) using pure pandas — no LLM code generation. Matches user words to DataFrame columns via exact name, substring, and stem matching.
- **Narration-only LLM mode** (`modules/ai_conversation.py`): new `narrate_result()` function that gives Groq pre-computed numbers and asks it only to explain them in 3-5 sentences. If Groq fails (429 rate limit, timeout), the computed summary is returned as-is — no more "I couldn't generate an AI response" fallback.
- **Boxplot chart builder** (`modules/auto_visualizer.py`): `_build_boxplot()` — grouped or ungrouped box-and-whisker distributions with mean+SD overlay.
- **Correlation heatmap builder** (`modules/auto_visualizer.py`): `_build_heatmap()` — correlation matrix with RdBu_r diverging scale, annotation text, and strongest-pair detection.
- **Outlier detection chart** (`modules/auto_visualizer.py`): `_build_outlier_chart()` — IQR-based scatter plot with red outlier highlights and dashed bound lines.
- **Forecast chart** (`modules/auto_visualizer.py`): linear extrapolation with actual (solid) + forecast (dashed) overlay in `build_chart_from_query()`.
- **9 new intent tokens** (`modules/auto_visualizer.py`): `_BOXPLOT_TOKENS`, `_SCATTER_TOKENS`, `_HEATMAP_TOKENS`, `_OUTLIER_TOKENS`, `_FORECAST_TOKENS` plus "line chart" / "line graph" in trend tokens.
- **Chart type selection guidance** (`modules/ai_code_generator.py`): explicit CHART TYPE SELECTION section in the LLM prompt so the model picks the right `px.*` call when AI code generation is used as a fallback.
- **Clickable follow-up questions**: suggested follow-up questions rendered as `st.button` instead of plain text. Clicking one injects it into the chat flow.
- **Chart persistence**: generated charts stored in `st.session_state` and re-rendered on every rerun. Charts no longer vanish when buttons are clicked.
- **Login gate** (`auth.py`): SHA-256 hashed credentials stored in a local, git-ignored `users.json`. Ships with two demo users.
- **Session-persistent tab navigation**: radio-based nav keyed into `st.session_state["active_tab"]`. Clicking buttons no longer kicks the user back to Data Overview.
- **CHANGELOG.md** (this file).

### Changed — Analysis Pipeline
- **AI Analyst execution order** (`modules/app_tabs.py`): now ① `run_smart_analysis` → ② `detect_simple_query` → ③ `generate_analysis_code`. Smart analysis handles ~90% of queries deterministically.
- **Query intent classification** (`modules/query_utils.py`): added 12 new chart intent tokens (boxplot, scatter, heatmap, outlier, anomaly, correlation, line chart, bar chart, histogram, forecast, predict, extrapolat).
- **`auto_visualize()` expanded** (`modules/auto_visualizer.py`): now generates boxplot, heatmap, and outlier charts in the automatic collection. Dedup limit raised from 5 to 8.
- **`build_chart_from_query()` rewritten** (`modules/auto_visualizer.py`): dispatches 9 intent categories instead of 4.
- **Chart palette** (`modules/auto_visualizer.py`): bar charts use multi-color discrete palette instead of continuous scale.
- **Chart card rendering** (`ui_components.py`): deep-copies figures so dark-theme mutations don't follow charts into session state or PDF.

### Fixed — Crash & Rendering
- **Finance data TypeError crash** (`modules/app_logic.py`): `_compute_period_delta` now skips `date_col` when it equals the metric column (e.g. "year" is both numeric and a date token). Previously `df[["year", "year"]]` created a duplicate-column DataFrame and `pd.to_numeric` raised `TypeError`.
- **Heatmap unreadable in PDF** (`modules/report_generator.py`, `modules/auto_visualizer.py`): changed from dark custom navy→red scale to `RdBu_r` diverging scale. PDF export no longer strips `coloraxis` from heatmap figures.
- **`_plotly_to_bytes` coloraxis blanket** (`modules/report_generator.py`): `coloraxis=dict(showscale=False)` was killing heatmap colors in PDF. Now conditionally preserves coloraxis for heatmap traces.
- **`_reset_trace_colors_for_light_bg` heatmap handling** (`modules/report_generator.py`): now applies `RdBu_r` colorscale and dark annotation text for heatmap traces instead of trying to set a marker color.
- Buttons in AI Analyst and Reports tabs resetting the active tab to Data Overview on rerun.
- AI Analyst charts looking monotone when underlying data had equal values.
- "Live analysis ready" layout broken because `chat-shell` div swallowed the Clear Chat button.
