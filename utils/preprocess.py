import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler


def preprocess(df):

    print("Preprocessing started...")

    # -------------------------------
    # 1. CLEAN COLUMN NAMES
    # -------------------------------
    df.columns = df.columns.str.strip()  # removes spaces

    # -------------------------------
    # 2. FIND LABEL COLUMN (AUTO FIX)
    # -------------------------------
    label_col = None

    for col in df.columns:
        if col.lower() == "label":
            label_col = col
            break

    if label_col is None:
        raise Exception(f"Label column not found. Columns are: {list(df.columns)}")

    print(f"Using label column: {label_col}")

    # -------------------------------
    # 3. CLEAN DATA
    # -------------------------------
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()

    # -------------------------------
    # 4. ENCODE LABEL
    # -------------------------------
    df[label_col] = df[label_col].apply(
        lambda x: 0 if str(x).strip().upper() == "BENIGN" else 1
    )

    # -------------------------------
    # 5. SPLIT FEATURES & LABEL
    # -------------------------------
    X = df.drop(columns=[label_col])
    y = df[label_col]

    # -------------------------------
    # 6. NUMERIC CONVERSION
    # -------------------------------
    X = X.apply(pd.to_numeric, errors='coerce')
    X = X.fillna(0)

    # -------------------------------
    # 7. RESET INDEX (CRITICAL FIX)
    # -------------------------------
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)

    # -------------------------------
    # 8. SCALE
    # -------------------------------
    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    print("Preprocessing completed:", X.shape)

    return X, y