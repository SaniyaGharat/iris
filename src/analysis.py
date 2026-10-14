"""Business analysis on the cleaned sales data (Delivered orders only)."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(ROOT / "data" / "processed" / "sales_data_cleaned.csv", parse_dates=["order_date"])
all_rev = df.revenue.sum()
d = df[df.order_status == "Delivered"].copy()          # revenue = Delivered only
d["month"] = d.order_date.dt.to_period("M")

plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 14})
fmt_m = FuncFormatter(lambda x, _: f"₹{x/1e6:.1f}M")
BLUE, GREY, ORANGE = "#2563eb", "#cbd5e1", "#ea580c"
insights = {}

# ---- Q1: top 5 categories --------------------------------------------------
cat = d.groupby("category").revenue.sum().sort_values(ascending=False)
top5 = cat.head(5); share = top5 / d.revenue.sum() * 100
fig, ax = plt.subplots(figsize=(9, 5.2))
bars = ax.barh(top5.index[::-1], top5.values[::-1], color=[GREY]*4 + [BLUE])
for b, s in zip(bars, share.values[::-1]):
    ax.text(b.get_width(), b.get_y() + b.get_height()/2, f"  ₹{b.get_width()/1e6:.2f}M ({s:.1f}%)", va="center")
ax.xaxis.set_major_formatter(fmt_m); ax.set_xlim(0, top5.max()*1.22)
ax.set_title("Top 5 Categories by Revenue (Delivered Orders)"); ax.set_xlabel("Revenue (₹ millions)"); ax.set_ylabel("Category")
fig.tight_layout(); fig.savefig(FIG / "q1_top_categories.png", dpi=200); plt.close(fig)
insights["q1"] = (f"{cat.index[0]} leads with ₹{cat.iloc[0]/1e6:.2f}M ({share.iloc[0]:.1f}% of revenue), and the top two "
                  f"categories ({cat.index[0]} and {cat.index[1]}) together earn {share.iloc[:2].sum():.1f}%.")

# ---- Q2: monthly revenue ---------------------------------------------------
m = d.groupby("month").revenue.sum(); mom = m.pct_change() * 100
labels = [p.strftime("%b") for p in m.index]
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.bar(labels, m.values, color=[GREY if p.month < 10 else BLUE for p in m.index])
ax.plot(labels, m.values, color=ORANGE, marker="o", lw=2)
ax.yaxis.set_major_formatter(fmt_m)
ax.set_title("Monthly Revenue, 2025 (Delivered Orders)"); ax.set_xlabel("Month (2025)"); ax.set_ylabel("Revenue (₹ millions)")
fig.tight_layout(); fig.savefig(FIG / "q2_monthly_revenue.png", dpi=200); plt.close(fig)
pre, post = m[m.index.month < 10].mean(), m[m.index.month >= 10].mean()
peak = m.idxmax()
insights["q2"] = (f"Revenue averaged ₹{pre/1e6:.2f}M a month from January to September, then stepped up "
                  f"{(post/pre-1)*100:.0f}% to ₹{post/1e6:.2f}M a month in Q4, peaking in {peak.strftime('%B')} at ₹{m.max()/1e6:.2f}M.")

# ---- Q3 (bonus): top 3 cities ---------------------------------------------
city = d[d.city != "Unknown"].groupby("city").revenue.sum().sort_values(ascending=False)
t3 = city.head(3); cshare = t3 / d.revenue.sum() * 100
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(t3.index, t3.values, color=BLUE, width=.55)
for b, s in zip(bars, cshare.values):
    ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"₹{b.get_height()/1e6:.2f}M\n({s:.1f}%)", ha="center", va="bottom")
ax.yaxis.set_major_formatter(fmt_m); ax.set_ylim(0, t3.max()*1.2)
ax.set_title("Top 3 Cities by Revenue (Delivered Orders)"); ax.set_xlabel("City"); ax.set_ylabel("Revenue (₹ millions)")
fig.tight_layout(); fig.savefig(FIG / "q3_top_cities.png", dpi=200); plt.close(fig)
insights["q3"] = (f"{t3.index[0]}, {t3.index[1]} and {t3.index[2]} generate {cshare.sum():.1f}% of revenue, "
                  f"with {t3.index[0]} alone contributing {cshare.iloc[0]:.1f}%.")

# ---- supporting numbers ----------------------------------------------------
lost = all_rev - d.revenue.sum()
insights["leakage"] = (f"Only {d.revenue.sum()/all_rev*100:.1f}% of order value (₹{d.revenue.sum()/1e6:.2f}M of ₹{all_rev/1e6:.2f}M) "
                       f"was delivered; ₹{lost/1e6:.2f}M was cancelled or returned.")
kpi = {"delivered_revenue": round(d.revenue.sum(), 2), "delivered_orders": len(d),
       "avg_order_value": round(d.revenue.mean(), 2), "all_orders_revenue": round(all_rev, 2)}
print(kpi); print(cat.round(0).to_dict()); print(m.round(0).to_dict()); print(mom.round(1).to_dict()); print(city.round(0).to_dict())
with open(ROOT / "reports" / "insights.md", "w", encoding="utf-8") as f:
    f.write("# Key insights (Delivered orders only)\n\n")
    for k, t in [("q1", "Top 5 categories"), ("q2", "Monthly revenue"), ("q3", "Top 3 cities"), ("leakage", "Revenue leakage")]:
        f.write(f"- **{t}:** {insights[k]}\n")
for k, v in insights.items(): print(k, "->", v)