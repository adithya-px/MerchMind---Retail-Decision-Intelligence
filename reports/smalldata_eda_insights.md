# RetailPulse Project - Small Dataset EDA Insights

## Project Overview
Exploratory Data Analysis was performed on the cleaned small online retail transactional dataset to understand customer purchasing behavior, revenue patterns, product performance, geographic contribution, and business opportunities.

Dataset Summary:
- Rows: 392,693
- Customers: 4,338
- Products: 3,665
- Countries: 37
- Orders: 18,532

---

## 1. Business Type Understanding
The dataset represents an international retail transactional business focused primarily on consumer products.

Observations:
- Product descriptions indicate decorative, household, and gift-oriented products.
- Most transactions involve relatively small purchase quantities.
- Most products are low-priced.

Business Meaning:
The business follows a volume-driven retail model focused on affordable products.

---

## 2. Revenue Drivers
Transaction quantity shows a strong positive relationship with revenue.

Evidence:
- Scatter plot analysis between Quantity and TotalPrice
- Correlation analysis confirms strong positive relationship

Business Meaning:
Revenue growth depends significantly on increasing the number of items sold.

Recommendation:
Promote bulk purchases through bundle offers, quantity discounts, and promotional packs.

---

## 3. Product Pricing Insights
Unit price shows only a weak influence on total transaction revenue.

Evidence:
- Weak correlation between UnitPrice and TotalPrice
- Scatter plot shows weak upward relationship

Business Meaning:
Expensive products alone do not strongly drive business revenue.
Affordable products can generate substantial revenue through bulk sales.

Recommendation:
Maintain strong focus on fast-moving affordable inventory while supporting premium offerings.

---

## 4. Bulk Buyer Behavior
Customers purchasing larger quantities tend to buy lower-priced products.

Evidence:
- Quantity vs UnitPrice scatter analysis

Business Meaning:
Bulk buyers prefer economical products.

Recommendation:
Design wholesale pricing strategies and volume-based promotions around affordable products.

---

## 5. Product Performance Insights
Top-selling products by quantity differ from top revenue-generating products.

Observations:
- Certain products dominate quantity sales.
- Different products dominate revenue generation.
- Some products perform strongly in both categories.

Business Meaning:
Products serve different business roles:
- volume drivers
- revenue drivers
- star products

Recommendation:
Use differentiated inventory management and product promotion strategies.

---

## 6. Geographic Insights
The United Kingdom contributes the largest share of total revenue.

Observations:
- UK significantly outperforms all other countries.
- Revenue distribution is heavily concentrated geographically.

Business Meaning:
The business is highly dependent on the UK market.

Risk:
Strong geographic concentration risk.

Recommendation:
Expand business presence across additional international markets.

---

## 7. Seasonal Revenue Trends
Revenue increases significantly toward the later months of the year.

Peak Month:
- November

Observations:
- Revenue shows clear upward seasonal growth.
- Late-year months outperform earlier periods.

Business Meaning:
The business exhibits strong seasonal demand patterns, likely influenced by festive or holiday purchasing.

Recommendation:
Prepare inventory, staffing, and logistics in advance of seasonal peaks.

---

## 8. Weekly Sales Pattern
Customer purchasing activity is strongest during weekdays.

Observations:
- Midweek performance is strongest.
- Weekend activity is comparatively lower.

Business Meaning:
Purchasing behavior follows predictable weekly operational patterns.

Recommendation:
Align campaigns, support, and inventory planning around peak weekdays.

---

## 9. Hourly Purchasing Behavior
Revenue is concentrated during daytime business hours.

Peak Window:
- 10 AM to 3 PM

Peak Hour:
- Around 12 PM

Business Meaning:
Customers primarily purchase during active daytime hours.

Recommendation:
Schedule promotional campaigns, customer engagement, and support during peak activity windows.

---

## 10. Customer Value Insights
A small number of customers contribute disproportionately to business revenue.

Observations:
- Top customers generate significantly higher revenue than average customers.

Business Meaning:
VIP customer dependency exists.

Risk:
Revenue impact from losing high-value customers.

Recommendation:
Develop customer retention strategies, loyalty programs, and personalized engagement for high-value customers.

---

## 11. Customer Segmentation Opportunity
Customer purchasing behavior differs significantly across spending and ordering frequency.

Observed Segments:
- high spending / low frequency customers
- repeat moderate-spending customers
- VIP customers
- bulk buyers

Business Meaning:
Distinct customer segments exist and can be targeted differently.

Recommendation:
Perform customer segmentation analysis such as RFM analysis in future project phases.

---

## 12. Outlier Behavior
The dataset contains significant extreme transaction values.

Observed In:
- Quantity
- UnitPrice
- TotalPrice

Business Meaning:
Extreme transactions may represent:
- wholesale purchases
- premium product purchases
- exceptional customer orders

Important Note:
These outliers are not automatically invalid and may represent legitimate business behavior.

Recommendation:
Handle outliers carefully based on business context instead of blindly removing them.

---

## 13. Correlation Analysis
Numeric variable relationships were evaluated mathematically.

Findings:
- Quantity vs TotalPrice → strong positive correlation
- UnitPrice vs TotalPrice → weak positive correlation
- Quantity vs UnitPrice → negligible relationship

Business Meaning:
Revenue depends more strongly on sales volume than product pricing.

Recommendation:
Focus revenue growth strategies on transaction volume optimization.

---

## Final Business Summary
The small retail dataset represents a volume-driven international retail business centered around affordable consumer products.
Revenue is influenced primarily by transaction quantity rather than premium pricing.
Customer demand demonstrates seasonal behavior, daytime purchasing concentration, and strong geographic dependence on the United Kingdom.
A small number of high-value customers contribute significantly to revenue, while distinct customer behavioral segments provide strong opportunities for advanced customer analytics.

Key Opportunities:
- bulk sales optimization
- customer retention strategies
- seasonal operational planning
- geographic expansion
- customer segmentation
- product strategy optimization