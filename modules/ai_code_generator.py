import os
import re

import streamlit as st
from groq import Groq

from modules.app_secrets import get_secret
from modules.code_executor import validate_generated_code

api_key = get_secret("GROQ_API_KEY")


def _is_rate_limit_error(error: Exception) -> bool:
    text = str(error).lower()
    return "429" in text or "too many requests" in text or "rate limit" in text


@st.cache_data(show_spinner=False)
def generate_analysis_code(api_key, query, df, dataset_context):
    client = Groq(api_key=api_key)

    columns = ", ".join(df.columns)
    numeric_cols = list(df.select_dtypes(include="number").columns)
    categorical_cols = list(df.select_dtypes(exclude="number").columns)

    prompt = f"""Return only valid Python code.

Use pandas and plotly.express only. Do not import extra libraries.
Use df as the dataframe. Put final output in result and charts in charts = [].
Prefer business metrics when available. Use aggregation, grouping, sorting, filtering, or top-N logic. Do not return raw df unless asked.

Dataset context:
{dataset_context}

Columns: {columns}
Numeric: {numeric_cols}
Categorical: {categorical_cols}
Question: {query}

Rules:
- Output only Python code in one ```python``` block.
- Always define charts = [].
- Use IQR for outliers.
- No explanations or markdown.
- Keep the result focused and business-ready.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=700,
        )

        raw_output = response.choices[0].message.content or ""
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
        if _is_rate_limit_error(e):
            return "charts = []\nresult = 'AI code generation paused: Groq rate limit reached. Please wait 30-60 seconds and retry.'"
        return f"charts = []\nresult = 'AI code generation failed: {str(e)}'"
