# Advanced analytics findings

## 1. Cancellations and returns
- Overall: 32.9% of orders were cancelled or returned (17.0% cancelled, 15.9% returned).
- Category: failure rates range 32.5%-33.5%; chi-square p = 0.989, Cramér's V = 0.008 (not significant).
- City: failure rates range 30.0%-35.3%; chi-square p = 0.601, Cramér's V = 0.033 (not significant).
- Payment method: failure rates range 29.4%-36.5%; chi-square p = 0.119, Cramér's V = 0.039 (not significant).
- COD vs prepaid: 66.6% of COD orders and 67.0% of prepaid orders were delivered (chi-square p = 0.97).
  **Conclusion:** cash-on-delivery is not riskier than prepaid payment here, so restricting COD would not reduce failures. About one in three orders fails in every segment, which suggests a company-wide process issue rather than a problem in one category, city or payment type.
- Revenue at risk: ₹5.62M of ₹16.73M order value (33.6%). Cutting the failure rate by 5 percentage points would recover roughly ₹0.84M.

## 2. Discount effectiveness
- Average quantity per order is flat across discount levels (2.00-2.03 units; Kruskal-Wallis p = 1.00).
- Discounted orders failed 34.1% of the time vs 31.4% for full-price orders (p = 0.048; borderline, and one of several tests, so treat with caution).
- Discounts on delivered orders gave away ₹0.79M (6.7% of pre-discount sales).
  **Conclusion:** in this data, deeper discounts are not associated with more units per order, so they reduce revenue without raising volume (observational evidence, not proof of cause). A test that withholds discounts for a sample of customers would confirm this before any policy change.

## 3. Customer segmentation (RFM, delivered orders)
- 1,262 customers placed at least one delivered order; 77.6% ordered more than once; the top 10% of customers account for 29.7% of revenue.
- Champions: 193 customers (15.3%), 30.4% of revenue, last order 22 days ago on average.
- At Risk (high value): 257 customers (20.4%), 24.2% of revenue, last order 165 days ago on average.
- Loyal: 201 customers (15.9%), 18.0% of revenue, last order 46 days ago on average.
- Needs Attention: 237 customers (18.8%), 14.0% of revenue, last order 50 days ago on average.
- New / Promising: 126 customers (10.0%), 7.0% of revenue, last order 25 days ago on average.
- Lapsed: 248 customers (19.7%), 6.5% of revenue, last order 212 days ago on average.