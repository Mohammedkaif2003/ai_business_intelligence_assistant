from groq import Groq
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", None)


def suggest_business_questions(query, df, schema):

    client = Groq(api_key=GROQ_API_KEY)

    # Build richer context
    sample_values = ""
    for col in schema.get("categorical_columns", [])[:3]:
        try:
            unique_vals = df[col].dropna().unique()[:5]
            sample_values += f"  {col}: {', '.join(str(v) for v in unique_vals)}\n"
        except:
            pass

    dataset_info = f"""
Dataset Overview
Rows: {schema['rows']}
Columns: {schema['columns']}

Column Names:
{schema['column_names']}

Numeric Columns:
{schema['numeric_columns']}

Categorical Columns:
{schema['categorical_columns']}

Sample Category Values:
{sample_values}
"""

    prompt = f"""You are a senior business intelligence analyst advising an executive.

The user just asked this question about their dataset:
"{query}"

Dataset Information:
{dataset_info}

Generate exactly 5 follow-up questions that a business executive would naturally ask next.

RULES:
- Each question must reference SPECIFIC column names from the dataset
- Include one question about trends over time (if date data exists)
- Include one question about rankings or top/bottom performers
- Include one question about comparisons between categories
- Include one predictive/forward-looking question
- Include one question about anomalies or outlier detection
- Make questions progressively deeper (start simple, end complex)
- Use the actual column names and category values where possible
- Format as numbered list (1. 2. 3. 4. 5.)
- Each question should be self-contained and specific enough to get a direct answer
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a senior business analyst. Generate specific, actionable follow-up questions using actual column names from the dataset."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=400
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI suggestion failed: {str(e)}"