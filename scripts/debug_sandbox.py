import pandas as pd
from modules.code_executor import _run_subprocess_sandbox

code = """
fig = px.line(x=[1,2,3], y=[1,3,2])
charts = [fig]
result = None
"""
print('Running sandbox test...')
out = _run_subprocess_sandbox(code, pd.DataFrame())
print('OUT:', out)
