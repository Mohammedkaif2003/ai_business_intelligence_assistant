from modules.code_executor import _run_subprocess_sandbox
import pandas as pd

code = """
fig = px.line(x=[1,2,3], y=[1,3,2])
charts = [fig]
result = None
"""

out = _run_subprocess_sandbox(code, pd.DataFrame())
print(out)
