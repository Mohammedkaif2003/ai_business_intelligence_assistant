import streamlit as st
from groq import Groq
import os
api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", None)
@st.cache_data(show_spinner=False)
def generate_analysis_code(api_key, query, df, dataset_context):

    client = Groq(api_key=api_key)

    columns = ", ".join(df.columns)

    prompt = f"""
You are an expert Python data analyst.

You are analyzing a pandas dataframe named df.

DATASET CONTEXT
---------------
{dataset_context}

AVAILABLE COLUMNS
-----------------
{columns}

USER QUESTION
-------------
{query}

RULES
-----
1. Write ONLY valid Python code using pandas, numpy, and plotly.express (px).
2. Use dataframe name: df. Do NOT import pandas or numpy again.
3. Store the final tabular/numeric output in a variable named `result`.
4. If a visual graph (chart) is suitable or requested, use `px` to generate Plotly figures.
5. Create a Python list named `charts` and append your Plotly figures to it (e.g., `charts = [px.bar(...)]`).
6. Apply `template="plotly_white"` to all your charts for premium design. Keep charts professional and clean.
7. Do NOT use plt, matplotlib, or seaborn. ONLY use plotly.express (px).
8. Do NOT print anything. Do NOT write conversational text outside of comments in the code block.
9. Wrap ALL your Python code inside a single ```python ... ``` block.
10. you can talk calm and cool when user says hi or hello or any other greeting.

EXAMPLE FORMAT
--------------
```python
result = df.groupby("Category")['Revenue'].sum().reset_index()
fig = px.bar(result, x='Category', y='Revenue', title='Revenue by Category', template='plotly_white')
fig.update_traces(marker_color='#4F46E5')
charts = [fig]
```
"""

    try:

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        import re
        code = response.choices[0].message.content

        # Extract code strictly from markdown block if present
        match = re.search(r"```python\s*(.*?)\s*```", code, re.DOTALL)
        if match:
            code = match.group(1)
        else:
            # Fallback string cleaning
            code = code.replace("```python", "").replace("```", "").strip()

        # Remove explanations and imports if AI adds them
        lines = code.split("\n")
        code_lines = []
        for line in lines:
            stripped_line = line.strip()
            
            if stripped_line.startswith("import ") or stripped_line.startswith("from "):
                continue
                
            code_lines.append(line)

        code = "\n".join(code_lines)

        # Safety fallback
        if "result =" not in code and "charts =" not in code:
            code = f"result = df.head()"

        return code

    except Exception as e:

        # Always return valid code to avoid execution crash
        return f"result = 'AI code generation failed: {str(e)}'"