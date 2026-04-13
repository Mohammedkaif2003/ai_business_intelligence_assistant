from modules.app_tabs import render_ai_analyst_tab


def render_chat_page(df, schema, api_key, logger):
    return render_ai_analyst_tab(df, schema, api_key, logger)
