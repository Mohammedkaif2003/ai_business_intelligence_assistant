import os
import re

import streamlit as st
from groq import Groq

from modules.app_secrets import get_secret
from modules.code_executor import validate_generated_code

api_key = get_secret("GROQ_API_KEY")


@st.cache_data(show_spinner=False)
def generate_analysis_code(api_key, query, df, dataset_context):
    client = Groq(api_key=api_key)

    columns = ", ".join(df.columns)
    numeric_cols = list(df.select_dtypes(include="number").columns)
    categorical_cols = list(df.select_dtypes(exclude="number").columns)

    prompt = f"""
You are an expert Python data analyst.

IMPORTANT:
- Do NOT use external libraries like scipy
- Use only pandas, numpy, plotly.express (imported as px), plotly.graph_objects (imported as go)
- For outliers, use IQR method (NOT zscore)

You are analyzing a pandas dataframe named df.

DATASET CONTEXT
---------------
{dataset_context}

AVAILABLE COLUMNS
-----------------
{columns}

COLUMN TYPES
------------
Numeric: {numeric_cols}
Categorical: {categorical_cols}

USER QUESTION
-------------
{query}

RULES
-----
1. Write ONLY valid Python code.
2. Use dataframe name: df.
3. Store final output in `result`.
4. Create charts using plotly.express (px) and store in `charts = []`.
5. ALWAYS define `charts = []` at the top.
6. Do NOT use matplotlib or seaborn.
7. Wrap everything inside ```python``` block.
8. NO explanations, ONLY code.

CHART TYPE SELECTION
--------------------
Choose the best chart type for the user's question:
- Trend / time series → px.line(..., markers=True)
- Comparison by category → px.bar(...)
- Distribution / spread → px.histogram(...) or px.box(...)
- Boxplot / quartiles / IQR → px.box(x=category, y=metric)
- Scatter / relationship → px.scatter(x=metric1, y=metric2)
- Correlation heatmap → px.imshow(df[numeric_cols].corr(), text_auto=".2f")
- Outlier detection → scatter with color= to highlight outliers
- Forecast → px.line for actual data + fig.add_scatter for dashed forecast line

Always prioritize business-relevant metrics:
- Prefer Revenue, Profit, Cost for analysis
- Use grouping for meaningful insights (e.g., by Region, Product, Department)
- Avoid returning raw data unless explicitly requested

QUERY HANDLING
--------------
- "North region" -> df[df['Region'] == 'North']
- "top N" -> df.sort_values(by=<numeric_column>, ascending=False).head(N)

MULTI-STEP LOGIC
----------------
1. Filter
2. Group/Aggregate
3. Sort
4. Limit

OUTLIER METHOD
--------------
Q1 = df[col].quantile(0.25)
Q3 = df[col].quantile(0.75)
IQR = Q3 - Q1
outliers = df[(df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)]

EXAMPLE
-------
```python
charts = []
result = df.groupby("Category")["Revenue"].sum().reset_index()
fig = px.bar(result, x="Category", y="Revenue", title="Revenue by Category")
charts = [fig]
```
Do NOT return df.head() or raw dataframe unless explicitly asked.
Always perform aggregation, filtering, or calculation.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        raw_output = response.choices[0].message.content
        match = re.search(r"```python\s*(.*?)\s*```", raw_output, re.DOTALL)
        if match:
            code = match.group(1)
        else:
            code = raw_output.replace("```python", "").replace("```", "").strip()

        cleaned = []
        for line in code.split("\n"):
            if line.strip().startswith(("import ", "from ")):
                continue
            cleaned.append(line)

        code = "\n".join(cleaned)

        if "charts =" not in code:
            code = "charts = []\n" + code

        if "result =" not in code:
            code += "\nresult = df.select_dtypes(include='number').sum()"

        validation_result = validate_generated_code(code)
        if isinstance(validation_result, str):
            safe_message = validation_result.replace("'", "\\'")
            return f"charts = []\nresult = '{safe_message}'"

        return code

    except Exception as e:
        return f"charts = []\nresult = 'AI code generation failed: {str(e)}'"
