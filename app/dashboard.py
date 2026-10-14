"""Interactive sales dashboard.  Run from the project root:  streamlit run app/dashboard.py"""
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
st.set_page_config(page_title="Sales Analytics Dashboard", page_icon="📊", layout="wide")

BLUE, GREY, ORANGE = "#2563eb", "#cbd5e1", "#ea580c"
STATUS_COLORS = {"Delivered": BLUE, "Cancelled": ORANGE, "Returned": "#94a3b8"}


@st.cache_data
def load():
    df = pd.read_csv(ROOT / "data" / "processed" / "sales_data_cleaned.csv", parse_dates=["order_date"])
    log = pd.read_csv(ROOT / "data" / "processed" / "cleaning_log.csv")
    return df, log


def inr(x):
    return f"₹{x/1e6:.2f}M" if abs(x) >= 1e6 else f"₹{x:,.0f}"


def rfm(d):
    """RFM scores and named segments for the (already filtered) delivered orders."""
    snap = d.order_date.max() + pd.Timedelta(days=1)
    r = d.groupby("customer_id").agg(recency=("order_date", lambda s: (snap - s.max()).days),
                                     frequency=("order_id", "nunique"), monetary=("revenue", "sum"))
    if len(r) < 25:
        return None
    r["R"] = pd.qcut(r.recency.rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
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
    return r


df, log = load()

# ------------------------------------------------------------------ sidebar filters
st.sidebar.header("Filters")
cats = st.sidebar.multiselect("Category", sorted(df.category.unique()), default=sorted(df.category.unique()))
cities = st.sidebar.multiselect("City", sorted(df.city.unique()), default=sorted(df.city.unique()))
statuses = st.sidebar.multiselect("Order status", ["Delivered", "Cancelled", "Returned"], default=["Delivered"],
                                  help="Revenue is counted for the statuses selected. Default is Delivered only.")
dmin, dmax = df.order_date.min().date(), df.order_date.max().date()
dates = st.sidebar.date_input("Order date range", (dmin, dmax), min_value=dmin, max_value=dmax)
start, end = (dates if isinstance(dates, tuple) and len(dates) == 2 else (dmin, dmax))

mask = (df.category.isin(cats) & df.city.isin(cities) & df.order_status.isin(statuses)
        & df.order_date.between(pd.Timestamp(start), pd.Timestamp(end)))
f = df[mask]
# same filters, but all statuses: needed for failure-rate views
f_all = df[df.category.isin(cats) & df.city.isin(cities)
           & df.order_date.between(pd.Timestamp(start), pd.Timestamp(end))]

st.title("📊 E-commerce Sales Dashboard")
st.caption("Cleaned data (4,944 orders, 2025). Revenue = quantity × unit price × (1 − discount %). "
           "Default view counts Delivered orders only.")

if f.empty:
    st.warning("No orders match the current filters. Widen the selection in the sidebar.")
    st.stop()

# ------------------------------------------------------------------ KPI row
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total revenue", inr(f.revenue.sum()))
c2.metric("Orders", f"{len(f):,}")
c3.metric("Average order value", f"₹{f.revenue.mean():,.0f}")
c4.metric("Cancelled or returned", f"{(f_all.order_status != 'Delivered').mean()*100:.1f}%",
          help="Share of orders in the selected category, city and dates that were cancelled or returned.")

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Order outcomes", "Customers (RFM)", "Data quality"])

# ------------------------------------------------------------------ Overview
with tab1:
    left, right = st.columns(2)
    m = f.groupby(f.order_date.dt.to_period("M")).revenue.sum().reset_index()
    m["month"] = m.order_date.dt.strftime("%b")
    m["mom"] = m.revenue.pct_change() * 100
    fig = px.bar(m, x="month", y="revenue", title="Monthly revenue", labels={"month": "Month (2025)", "revenue": "Revenue (₹)"},
                 hover_data={"mom": ":.1f"}, color_discrete_sequence=[BLUE])
    fig.add_scatter(x=m.month, y=m.revenue, mode="lines+markers", line=dict(color=ORANGE), name="Trend", showlegend=False)
    fig.update_layout(margin=dict(t=50, b=10))
    left.plotly_chart(fig, width="stretch")

    cat = f.groupby("category").revenue.sum().sort_values().reset_index()
    cat["share"] = cat.revenue / cat.revenue.sum() * 100
    fig = px.bar(cat, x="revenue", y="category", orientation="h", title="Revenue by category",
                 labels={"revenue": "Revenue (₹)", "category": "Category"}, text=cat.share.map("{:.1f}%".format),
                 color_discrete_sequence=[BLUE])
    fig.update_layout(margin=dict(t=50, b=10))
    right.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    city = f[f.city != "Unknown"].groupby("city").revenue.sum().sort_values(ascending=False).head(3).reset_index()
    fig = px.bar(city, x="city", y="revenue", title="Top 3 cities by revenue", labels={"city": "City", "revenue": "Revenue (₹)"},
                 color_discrete_sequence=[BLUE])
    fig.update_layout(margin=dict(t=50, b=10))
    left.plotly_chart(fig, width="stretch")

    prod = f.groupby("product").revenue.sum().sort_values(ascending=False).head(10).sort_values().reset_index()
    fig = px.bar(prod, x="revenue", y="product", orientation="h", title="Top 10 products by revenue",
                 labels={"revenue": "Revenue (₹)", "product": "Product"}, color_discrete_sequence=[BLUE])
    fig.update_layout(margin=dict(t=50, b=10))
    right.plotly_chart(fig, width="stretch")

    if len(cat) and len(m):
        top = cat.iloc[-1]
        st.info(f"**Insight:** {top.category} leads with {inr(top.revenue)} ({top.share:.1f}% of the selected revenue); "
                f"the best month is {m.loc[m.revenue.idxmax(), 'month']} at {inr(m.revenue.max())}.")

# ------------------------------------------------------------------ Outcomes
with tab2:
    st.subheader("What share of orders fail?")
    overall = (f_all.order_status != "Delivered").mean()
    a, b = st.columns([1, 2])
    status = f_all.order_status.value_counts().reset_index()
    fig = px.pie(status, names="order_status", values="count", hole=.55, title="Order status mix",
                 color="order_status", color_discrete_map=STATUS_COLORS)
    a.plotly_chart(fig, width="stretch")
    dim = b.radio("Break down by", ["category", "city", "payment_method"], horizontal=True,
                  format_func=lambda s: s.replace("_", " ").title())
    seg = (f_all[f_all[dim] != "Unknown"].groupby(dim).order_status
           .value_counts(normalize=True).rename("share").reset_index())
    seg = seg[seg.order_status != "Delivered"]
    fig = px.bar(seg, x=dim, y="share", color="order_status", barmode="stack", color_discrete_map=STATUS_COLORS,
                 title=f"Cancelled and returned share by {dim.replace('_', ' ')}",
                 labels={"share": "Share of orders", dim: dim.replace("_", " ").title(), "order_status": "Status"})
    fig.update_yaxes(tickformat=".0%")
    b.plotly_chart(fig, width="stretch")
    lost = f_all.loc[f_all.order_status != "Delivered", "revenue"].sum()
    st.info(f"**Insight:** {overall*100:.1f}% of the selected orders were cancelled or returned, putting {inr(lost)} of order "
            f"value at risk. In the full dataset this rate is almost identical across categories, cities and payment methods "
            f"(no chi-square test is significant), which points to a process-wide issue.")

    st.subheader("Do discounts lift volume?")
    g = f_all.groupby("discount_pct").agg(avg_qty=("quantity", "mean"), aov=("revenue", "mean")).reset_index()
    g["discount"] = g.discount_pct.astype(int).astype(str) + "%"
    x, y = st.columns(2)
    x.plotly_chart(px.bar(g, x="discount", y="avg_qty", title="Units per order by discount",
                          labels={"discount": "Discount", "avg_qty": "Average quantity"},
                          color_discrete_sequence=[BLUE]).update_yaxes(range=[0, 3]), width="stretch")
    y.plotly_chart(px.bar(g, x="discount", y="aov", title="Average order value by discount",
                          labels={"discount": "Discount", "aov": "Average order value (₹)"},
                          color_discrete_sequence=[ORANGE]), width="stretch")

# ------------------------------------------------------------------ RFM
with tab3:
    st.subheader("Customer segments")
    st.caption("Built from Delivered orders in the selected category, city and date range. "
               "Recency, frequency and monetary value are each scored 1–5.")
    dd = df[df.category.isin(cats) & df.city.isin(cities) & (df.order_status == "Delivered")
            & df.order_date.between(pd.Timestamp(start), pd.Timestamp(end))]
    r = rfm(dd)
    if r is None:
        st.warning("Too few customers in this selection to segment. Widen the filters.")
    else:
        s = r.groupby("segment").agg(customers=("monetary", "size"), revenue=("monetary", "sum"),
                                     avg_recency_days=("recency", "mean"), avg_orders=("frequency", "mean")).reset_index()
        s["Share of customers"] = s.customers / s.customers.sum()
        s["Share of revenue"] = s.revenue / s.revenue.sum()
        s = s.sort_values("revenue", ascending=False)
        long = s.melt(id_vars="segment", value_vars=["Share of customers", "Share of revenue"], var_name="Metric", value_name="Share")
        fig = px.bar(long, x="segment", y="Share", color="Metric", barmode="group",
                     color_discrete_map={"Share of customers": GREY, "Share of revenue": BLUE},
                     labels={"segment": "RFM segment"}, title="Share of customers vs share of revenue")
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, width="stretch")
        show = s.rename(columns={"segment": "Segment", "customers": "Customers", "revenue": "Revenue (₹)",
                                 "avg_recency_days": "Avg days since last order", "avg_orders": "Avg orders"})
        st.dataframe(show.style.format({"Revenue (₹)": "₹{:,.0f}", "Avg days since last order": "{:.0f}", "Avg orders": "{:.1f}",
                                        "Share of customers": "{:.1%}", "Share of revenue": "{:.1%}"}),
                     width="stretch", hide_index=True)
        ar = s[s.segment == "At Risk (high value)"]
        if not ar.empty:
            st.info(f"**Insight:** {int(ar.customers.iloc[0])} high-value customers ({ar['Share of revenue'].iloc[0]*100:.1f}% of revenue) "
                    f"have not ordered in about {ar.avg_recency_days.iloc[0]:.0f} days, making them the clearest win-back target.")

# ------------------------------------------------------------------ Data quality
with tab4:
    st.subheader("What was fixed")
    raw_rows = int(log.rows_after.iloc[0])
    a, b, c = st.columns(3)
    a.metric("Raw rows", f"{raw_rows:,}")
    b.metric("Rows after cleaning", f"{len(df):,}")
    c.metric("Rows removed", f"{raw_rows - len(df):,}")
    st.dataframe(log.rename(columns={"step": "Step", "action": "Action", "rows_removed": "Rows removed",
                                     "values_changed": "Values changed", "rows_after": "Rows after", "note": "Note"}),
                 width="stretch", hide_index=True)
    st.caption("Known limitation: about 90 dates in numeric format with a day of 12 or less could be mm-dd-yyyy, "
               "but were read as dd-mm-yyyy (under 2% of rows).")
    st.download_button("Download cleaned data (CSV)", df.to_csv(index=False).encode("utf-8"),
                       file_name="sales_data_cleaned.csv", mime="text/csv")