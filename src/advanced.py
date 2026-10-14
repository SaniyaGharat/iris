"""Advanced analytics: order outcomes, statistical tests, discount effectiveness, RFM segmentation."""
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "reports" / "figures"; FIG.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(ROOT / "data" / "processed" / "sales_data_cleaned.csv", parse_dates=["order_date"])
df["failed"] = (df.order_status != "Delivered").astype(int)       # cancelled or returned
BLUE, GREY, ORANGE, RED = "#2563eb", "#cbd5e1", "#ea580c", "#dc2626"
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 13})
out = []                                                           # lines for the findings report
def say(s=""): out.append(s); print(s)

def chi_test(col, data=df):
    ct = pd.crosstab(data[col], data.failed)
    chi2, p, _, _ = stats.chi2_contingency(ct)
    v = np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1)))
    return p, v

# ---------------------------------------------------------------- 1. outcomes
overall = df.failed.mean()
say("## 1. Cancellations and returns")
say(f"- Overall: {overall*100:.1f}% of orders were cancelled or returned "
    f"({(df.order_status=='Cancelled').mean()*100:.1f}% cancelled, {(df.order_status=='Returned').mean()*100:.1f}% returned).")
known = df[(df.city != "Unknown") & (df.payment_method != "Unknown")]   # tests exclude placeholder labels
fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), sharey=True)
for ax, col, title in zip(axes, ["category", "city", "payment_method"], ["Category", "City", "Payment method"]):
    data = known if col != "category" else df
    rate = data.groupby(col).failed.mean().sort_values(ascending=False)
    p, v = chi_test(col, data)
    ax.bar(rate.index, rate.values, color=[ORANGE if x == rate.max() else GREY for x in rate.values])
    ax.axhline(overall, color="black", ls="--", lw=1); ax.set_title(f"{title} (chi-square p = {p:.2f})")
    ax.tick_params(axis="x", rotation=45); ax.set_xlabel(title)
    for lab in ax.get_xticklabels(): lab.set_ha("right")
    say(f"- {title}: failure rates range {rate.min()*100:.1f}%-{rate.max()*100:.1f}%; chi-square p = {p:.3f}, Cramér's V = {v:.3f} "
        f"({'significant' if p < .05 else 'not significant'}).")
axes[0].set_ylabel("Cancelled or returned (% of orders)"); axes[0].yaxis.set_major_formatter(PercentFormatter(1, 0))
axes[0].set_ylim(0, .5)
fig.suptitle(f"Order Failure Rate by Segment (dashed line = overall {overall*100:.1f}%)", fontweight="bold", y=1.02)
fig.tight_layout(); fig.savefig(FIG / "q4_failure_rates.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# COD vs prepaid
k = df[df.payment_method != "Unknown"].copy(); k["mode"] = np.where(k.payment_method == "COD", "COD", "Prepaid")
tab = pd.crosstab(k["mode"], k.order_status); p_cod = stats.chi2_contingency(tab)[1]
dl = tab["Delivered"] / tab.sum(axis=1)
say(f"- COD vs prepaid: {dl['COD']*100:.1f}% of COD orders and {dl['Prepaid']*100:.1f}% of prepaid orders were delivered "
    f"(chi-square p = {p_cod:.2f}).")
say(f"  **Conclusion:** cash-on-delivery is not riskier than prepaid payment here, so restricting COD would not reduce failures. "
    f"About one in three orders fails in every segment, which suggests a company-wide process issue rather than a problem in one category, city or payment type.")

gross = (df.quantity * df.unit_price)
rev_lost = df.loc[df.failed == 1, "revenue"].sum()
say(f"- Revenue at risk: ₹{rev_lost/1e6:.2f}M of ₹{df.revenue.sum()/1e6:.2f}M order value ({rev_lost/df.revenue.sum()*100:.1f}%). "
    f"Cutting the failure rate by 5 percentage points would recover roughly ₹{df.revenue.sum()*.05/1e6:.2f}M.")

# ---------------------------------------------------------------- 2. discounts
say("\n## 2. Discount effectiveness")
g = df.groupby("discount_pct").agg(orders=("order_id", "size"), avg_qty=("quantity", "mean"),
                                   avg_order_value=("revenue", "mean"), failure=("failed", "mean"))
h, p_q = stats.kruskal(*[x.quantity.values for _, x in df.groupby("discount_pct")])
disc_given = (gross - df.revenue)[df.order_status == "Delivered"].sum()
dl_rev = df.loc[df.order_status == "Delivered", "revenue"].sum()
nd = df[df.discount_pct == 0].failed; dd = df[df.discount_pct > 0].failed
p_fail = stats.chi2_contingency(pd.crosstab(df.discount_pct > 0, df.failed))[1]
say(f"- Average quantity per order is flat across discount levels ({g.avg_qty.min():.2f}-{g.avg_qty.max():.2f} units; Kruskal-Wallis p = {p_q:.2f}).")
say(f"- Discounted orders failed {dd.mean()*100:.1f}% of the time vs {nd.mean()*100:.1f}% for full-price orders (p = {p_fail:.3f}; borderline, and one of several tests, so treat with caution).")
say(f"- Discounts on delivered orders gave away ₹{disc_given/1e6:.2f}M ({disc_given/(dl_rev+disc_given)*100:.1f}% of pre-discount sales).")
say("  **Conclusion:** in this data, deeper discounts are not associated with more units per order, so they reduce revenue without raising volume (observational evidence, not proof of cause). "
    "A test that withholds discounts for a sample of customers would confirm this before any policy change.")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
a1.bar(g.index.astype(int).astype(str) + "%", g.avg_qty, color=BLUE, width=.55); a1.set_ylim(0, 3)
a1.set_title("Units per Order by Discount Level"); a1.set_xlabel("Discount"); a1.set_ylabel("Average quantity per order")
a2.bar(g.index.astype(int).astype(str) + "%", g.avg_order_value, color=ORANGE, width=.55)
a2.set_title("Order Value by Discount Level"); a2.set_xlabel("Discount"); a2.set_ylabel("Average order value (₹)")
a2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
fig.tight_layout(); fig.savefig(FIG / "q5_discount_effect.png", dpi=200); plt.close(fig)

# ---------------------------------------------------------------- 3. RFM
say("\n## 3. Customer segmentation (RFM, delivered orders)")
d = df[df.order_status == "Delivered"]
snap = d.order_date.max() + pd.Timedelta(days=1)
r = d.groupby("customer_id").agg(recency=("order_date", lambda s: (snap - s.max()).days),
                                 frequency=("order_id", "nunique"), monetary=("revenue", "sum"))
r["R"] = pd.qcut(r.recency.rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)   # recent = high
r["F"] = pd.qcut(r.frequency.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
r["M"] = pd.qcut(r.monetary.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
def seg(x):
    if x.R >= 4 and x.F >= 4 and x.M >= 4: return "Champions"
    if x.F >= 4 and x.R >= 3: return "Loyal"
    if x.R <= 2 and (x.F >= 3 or x.M >= 4): return "At Risk (high value)"
    if x.R >= 4 and x.F <= 2: return "New / Promising"
    if x.R <= 2: return "Lapsed"
    return "Needs Attention"
r["segment"] = r.apply(seg, axis=1)
s = r.groupby("segment").agg(customers=("monetary", "size"), revenue=("monetary", "sum"),
                             avg_recency_days=("recency", "mean"), avg_orders=("frequency", "mean")).round(1)
s["customer_share"] = s.customers / s.customers.sum(); s["revenue_share"] = s.revenue / s.revenue.sum()
s = s.sort_values("revenue", ascending=False)
r.reset_index().to_csv(ROOT / "data" / "processed" / "rfm_segments.csv", index=False)
top10 = r.monetary.sort_values(ascending=False).head(int(len(r) * .1)).sum() / r.monetary.sum()
say(f"- {len(r):,} customers placed at least one delivered order; {(r.frequency > 1).mean()*100:.1f}% ordered more than once; "
    f"the top 10% of customers account for {top10*100:.1f}% of revenue.")
for name, row in s.iterrows():
    say(f"- {name}: {int(row.customers)} customers ({row.customer_share*100:.1f}%), {row.revenue_share*100:.1f}% of revenue, "
        f"last order {row.avg_recency_days:.0f} days ago on average.")
fig, ax = plt.subplots(figsize=(10, 5)); idx = np.arange(len(s)); w = .38
ax.bar(idx - w/2, s.customer_share, w, color=GREY, label="Share of customers")
ax.bar(idx + w/2, s.revenue_share, w, color=BLUE, label="Share of revenue")
ax.set_xticks(idx); ax.set_xticklabels(s.index, rotation=20, ha="right"); ax.yaxis.set_major_formatter(PercentFormatter(1, 0))
ax.set_title("Customer Segments: Share of Customers vs Share of Revenue"); ax.set_xlabel("RFM segment"); ax.set_ylabel("Share of total")
ax.legend(frameon=False); fig.tight_layout(); fig.savefig(FIG / "q6_rfm_segments.png", dpi=200); plt.close(fig)

(ROOT / "reports" / "advanced_findings.md").write_text("# Advanced analytics findings\n\n" + "\n".join(out), encoding="utf-8")