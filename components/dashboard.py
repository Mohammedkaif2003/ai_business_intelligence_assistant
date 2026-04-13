from modules.app_tabs import render_dashboard_header as _render_dashboard_header
from modules.app_tabs import render_data_overview_tab as _render_data_overview_tab


def render_dashboard_header(df):
    return _render_dashboard_header(df)


def render_data_overview_page(df):
    return _render_data_overview_tab(df)
