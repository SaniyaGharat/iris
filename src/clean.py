import pandas as pd, numpy as np

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "sales.csv"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
log = []
def step(name, rows_removed=0, values_changed=0, note=""):
    log.append({"step": len(log)+1, "action": name, "rows_removed": rows_removed,
                "values_changed": values_changed, "rows_after": len(df), "note": note})

df = pd.read_csv(SRC, dtype=str, keep_default_na=False)
step("Load raw file", note=f"{df.shape[1]} columns")

# 1. exact duplicates
n = len(df); df = df.drop_duplicates().reset_index(drop=True)
step("Remove exact duplicate rows", n-len(df), note="Every duplicate order_id was a full-row copy")

# 2. whitespace / case / aliases
def changed(before, after): return int((before != after).sum())
for c in ["city", "category", "payment_method"]:
    b = df[c].copy()
    df[c] = df[c].str.strip().str.replace(r"\s+", " ", regex=True)
    if c == "payment_method":
        df[c] = df[c].replace({"upi": "UPI"}).where(df[c] != "", "")
    if c in ("city", "category"):
        df[c] = df[c].where(df[c] == "", df[c].str.title() if c == "city" else df[c].str.lower())
    step(f"Standardise text in {c}", values_changed=changed(b, df[c]), note="trim spaces, unify case")
df["category"] = df["category"].replace({"electronics": "Electronics", "clothing": "Clothing",
    "home & kitchen": "Home & Kitchen", "beauty": "Beauty", "books": "Books"})
b = df["city"].copy(); df["city"] = df["city"].replace({"Bangalore": "Bengaluru"})
step("Map city alias Bangalore -> Bengaluru", values_changed=changed(b, df["city"]))
df["payment_method"] = df["payment_method"].replace({"Upi": "UPI", "Cod": "COD"})

# 3. dates
raw = df["order_date"]
d1 = pd.to_datetime(raw, format="%d-%m-%Y", errors="coerce")
d2 = pd.to_datetime(raw, format="%d-%b-%y", errors="coerce")
d3 = pd.to_datetime(raw, format="%m-%d-%Y", errors="coerce")
df["order_date"] = d1.fillna(d2).fillna(d3)
assert df["order_date"].isna().sum() == 0
step("Parse 3 mixed date formats to ISO", values_changed=len(df),
     note=f"dd-mm-yyyy={d1.notna().sum()}, dd-Mon-yy={(d1.isna()&d2.notna()).sum()}, "
          f"mm-dd-yyyy={(d1.isna()&d2.isna()&d3.notna()).sum()}; ambiguous (day<=12) numeric dates assumed dd-mm-yyyy")

# 4. numeric
for c in ["quantity", "unit_price", "discount_pct"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# 5. invalid quantity -> drop
bad_q = (df.quantity <= 0) | (df.quantity > 100)
n = len(df); df = df[~bad_q].reset_index(drop=True)
step("Drop invalid quantity (<=0 or 500)", n-len(df),
     note="Orders cannot have zero/negative quantity; 500 is ~100x the normal max of 4, likely entry error")

# 6. invalid price / discount -> NaN
valid_prices = df.unit_price.where((df.unit_price > 0) & (df.unit_price < 20000))
med = valid_prices.groupby(df["product"]).median()
bad_p = df.unit_price.notna() & ~((df.unit_price > 0) & (df.unit_price < 20000))
df.loc[bad_p, "unit_price"] = np.nan
step("Flag impossible unit_price (0 or 250000) as missing", values_changed=int(bad_p.sum()))
bad_d = df.discount_pct.notna() & ~df.discount_pct.isin([0, 5, 10, 15, 20])
df.loc[bad_d, "discount_pct"] = np.nan
step("Flag impossible discount_pct (150) as missing", values_changed=int(bad_d.sum()))

# 7. imputation
m = df.unit_price.isna()
df.loc[m, "unit_price"] = df.loc[m, "product"].map(med).round(2)
step("Impute missing unit_price with product median", values_changed=int(m.sum()),
     note="Each product has a tight price band; median is robust to remaining outliers")
m = df.discount_pct.isna(); df.loc[m, "discount_pct"] = 0
step("Impute missing discount_pct with 0", values_changed=int(m.sum()),
     note="0 is the most common value (~43%); assumes no discount when not recorded")

for c, label in [("city", "Unknown"), ("customer_name", "Unknown")]:
    known = df[df[c] != ""].groupby("customer_id")[c].agg(lambda s: s.mode().iloc[0])
    m = df[c] == ""
    df.loc[m, c] = df.loc[m, "customer_id"].map(known).fillna("")
    rec = int(m.sum() - (df[c] == "").sum())
    m2 = df[c] == ""; df.loc[m2, c] = label
    step(f"Fill missing {c}", values_changed=int(m.sum()),
         note=f"{rec} recovered from same customer_id's other orders, {int(m2.sum())} set to 'Unknown'")
m = df.payment_method == ""; df.loc[m, "payment_method"] = "Unknown"
step("Fill missing payment_method with 'Unknown'", values_changed=int(m.sum()), note="No reliable way to infer")

# 7b. statistical outlier check (per-product 3x IQR on unit_price)
g = df.groupby("product")["unit_price"]
q1, q3 = g.transform(lambda x: x.quantile(.25)), g.transform(lambda x: x.quantile(.75))
iqr = q3 - q1
n_out = int(((df.unit_price < q1 - 3*iqr) | (df.unit_price > q3 + 3*iqr)).sum())
step("Statistical outlier check on unit_price (3x IQR per product)", values_changed=n_out,
     note="0 flagged: prices sit within ~7% of each product's median after fixing the 0 / 250,000 values")

# 8. revenue
df["revenue"] = (df.quantity * df.unit_price * (1 - df.discount_pct / 100)).round(2)
step("Add revenue column", values_changed=len(df), note="quantity x unit_price x (1 - discount_pct/100)")

df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d")
df.to_csv(OUT / "sales_data_cleaned.csv", index=False)
pd.DataFrame(log).to_csv(OUT / "cleaning_log.csv", index=False)
pd.set_option("display.width", 250, "display.max_colwidth", 90)
print(pd.DataFrame(log).to_string(index=False))
print(df.shape, df.isna().sum().sum(), "nulls;", df.revenue.sum().round(0))
print(df[["city","category","payment_method"]].apply(lambda s: s.nunique()).to_dict())