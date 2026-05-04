import pandas as pd


def normalize_columns(df):

    # Clean column names (regex=False avoids FutureWarning in pandas 2.x)
    df.columns = (
        df.columns
        .str.strip()
        .str.replace("_", " ", regex=False)
        .str.replace("-", " ", regex=False)
        .str.title()
    )

    # Standard column mapping
    mapping = {
        "Sales": "Revenue",
        "Sales Amount": "Revenue",
        "Revenue Amount": "Revenue",
        "Total Sales": "Revenue",

        "Product Name": "Product",
        "Item": "Product",
        "Item Name": "Product",

        "Location": "Region",
        "Area": "Region",

        "Order Date": "Date",
        "Transaction Date": "Date"
    }

    df.rename(columns=mapping, inplace=True)

    # Prevent duplicate columns after normalization (e.g. Sales and Sales Amount both mapping to Revenue)
    # If duplicates exist, pandas allows it but it breaks downstream analysis.
    if df.columns.duplicated().any():
        new_cols = []
        counts = {}
        for col in df.columns:
            if col in counts:
                counts[col] += 1
                new_cols.append(f"{col} {counts[col]}")
            else:
                counts[col] = 1
                new_cols.append(col)
        df.columns = new_cols

    # Convert Date column if present
    if "Date" in df.columns:
        try:
            df["Date"] = pd.to_datetime(df["Date"])
        except (TypeError, ValueError):
            pass

    return df


def detect_columns(df):

    column_map = {}

    for col in df.columns:

        name = col.lower()

        if "product" in name or "item" in name:
            column_map["Product"] = col

        elif "region" in name or "location" in name or "area" in name:
            column_map["Region"] = col

        elif "revenue" in name or "sales" in name:
            column_map["Revenue"] = col

        elif "date" in name:
            column_map["Date"] = col

    return column_map
