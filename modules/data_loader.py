import pandas as pd


def normalize_columns(df):

    # Clean column names
    df.columns = (
        df.columns
        .str.strip()
        .str.replace("_", " ")
        .str.replace("-", " ")
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

    # Convert Date column if present
    if "Date" in df.columns:
        try:
            df["Date"] = pd.to_datetime(df["Date"])
        except (TypeError, ValueError):
            pass

    # Deduplicate column names that may collide after normalization/mapping.
    # For collisions, append " (1)", " (2)", ... to create unique column names.
    cols = list(df.columns)
    counts: dict[str, int] = {}
    unique_cols: list[str] = []
    collisions = False
    for col in cols:
        base = str(col)
        if base not in counts:
            counts[base] = 0

        if counts[base] == 0 and base not in unique_cols:
            unique_name = base
            counts[base] = 1
        else:
            collisions = True
            idx = counts[base]
            unique_name = f"{base} ({idx})"
            # ensure we don't accidentally collide with an existing unique name
            while unique_name in unique_cols:
                idx += 1
                unique_name = f"{base} ({idx})"
            counts[base] = idx + 1

        unique_cols.append(unique_name)

    if collisions:
        import logging

        logging.getLogger(__name__).debug("column_name_collisions_resolved", extra={"original": cols, "resolved": unique_cols})
        df.columns = unique_cols

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


def load_dataset(raw_input):
    """Load a dataset from bytes, file-like, or path and return a pandas DataFrame.

    Accepts:
    - bytes: contents of a CSV file
    - str: filesystem path to a CSV
    - file-like object
    """
    import io

    # If bytes provided, wrap in BytesIO
    if isinstance(raw_input, (bytes, bytearray)):
        bio = io.BytesIO(raw_input)
        df = pd.read_csv(bio)
    elif hasattr(raw_input, "read"):
        # file-like
        df = pd.read_csv(raw_input)
    elif isinstance(raw_input, str):
        df = pd.read_csv(raw_input)
    else:
        raise ValueError("Unsupported input type for load_dataset")

    # normalize and return
    df = normalize_columns(df)
    return df
