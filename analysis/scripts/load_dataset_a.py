"""Load Dataset A (ntr_pastatai construction-year export) into a pandas DataFrame.

Handles: pipe delimiter, Lithuanian decimal-comma numeric formatting.
"""
import pandas as pd
import numpy as np

NUMERIC_COMMA_COLS = [
    "atr_uzstatytas_plotas", "bendras_plotas", "naudingas_plotas", "gyv_plotas",
    "verslo_plotas", "pagalb_nenaud_plotas", "pagalb_naud_plotas", "rusiu_plotas",
    "garazu_plotas",
]

INT_COLS = [
    "aukstu_skaicius", "stat_pradzios_metai", "stat_pabaigos_metai",
    "modern_pradzios_metai", "modern_pabaigos_metai",
]


def _comma_to_float(s):
    if pd.isna(s) or s == "":
        return np.nan
    return float(str(s).replace(",", "."))


def load(path="statiniai_Kauno_m_sav.csv"):
    df = pd.read_csv(path, sep="|", encoding="utf-8", dtype=str, keep_default_na=False)
    df.replace("", np.nan, inplace=True)
    for c in NUMERIC_COMMA_COLS:
        df[c] = df[c].apply(_comma_to_float)
    for c in INT_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["dirbt_id"] = df["dirbt_id"].astype(str)
    return df


if __name__ == "__main__":
    df = load()
    print("rows", len(df))
    print("dtypes:")
    print(df[NUMERIC_COMMA_COLS + INT_COLS].dtypes)
    print()
    print("atr_uzstatytas_plotas describe:")
    print(df["atr_uzstatytas_plotas"].describe())
    print()
    print("stat_pabaigos_metai populated pct:", df["stat_pabaigos_metai"].notna().mean())
    print("stat_pabaigos_metai range:", df["stat_pabaigos_metai"].min(), df["stat_pabaigos_metai"].max())
    print()
    print("aukstu_skaicius populated pct:", df["aukstu_skaicius"].notna().mean())
    print("aukstu_skaicius value counts (top 15):")
    print(df["aukstu_skaicius"].value_counts().head(15))
    print()
    print("distinct seniunijos count:", df["seniunijos_pavad"].nunique())
    with open("analysis/output/seniunijos_a.txt", "w", encoding="utf-8") as f:
        for v in sorted(df["seniunijos_pavad"].dropna().unique()):
            f.write(v + "\n")
    print("wrote analysis/output/seniunijos_a.txt")
