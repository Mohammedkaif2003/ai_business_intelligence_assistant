import pandas as pd

from modules.code_executor import _run_subprocess_sandbox


def test_sandbox_serializes_plotly_charts():
    code = """
fig = px.line(x=[1,2,3], y=[1,3,2])
charts = [fig]
result = None
"""
    df = pd.DataFrame()
    out = _run_subprocess_sandbox(code, df)
    assert isinstance(out, dict)
    assert out.get("status") == "ok"
    assert isinstance(out.get("charts"), list)
