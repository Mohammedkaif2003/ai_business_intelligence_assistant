from __future__ import annotations

from modules.app_tabs import render_ai_analyst_tab
from modules.chat_session_manager import ChatSessionManager


def render_ai_analyst_chat_refactored(
    df,
    schema,
    api_key,
    logger,
    session_manager: ChatSessionManager | None = None,
):
    """Compatibility wrapper that delegates to the current AI analyst tab renderer."""
    _ = session_manager
    return render_ai_analyst_tab(df, schema, api_key, logger)
