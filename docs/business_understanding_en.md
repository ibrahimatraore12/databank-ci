# Business Understanding - dataBank CI Customer 360

> *[Version française disponible : [business_understanding.md](business_understanding.md)]*

**Author:** Ibrahima TRAORÉ - Analytics Engineer
**Date:** July 2026

## 1. Context

dataBank CI is a retail bank operating in Côte d'Ivoire (WAEMU zone, XOF
currency). The source file covers 140 customers, split into 4 groups called
"segments" (Mass, Affluent, Premier, Youth). For each customer, we have
their accounts, loans, cards, transactions, interactions with the bank, and
complaints.

## 2. Five business decisions this project needs to support

1. **Advisor visit prioritization** - among customers showing signs of
   disengagement, who should be contacted first this week?
2. **Cross-sell targeting** - among customers who hold few products (for
   example the 42 customers without a card), who are good candidates for a
   targeted offer?
3. **Complaint triage** - among open complaints, which ones should be
   escalated first, based on how severe they are and how much they could
   affect customer retention?
4. **Salary domiciliation upsell** - which high-income customers haven't
   yet chosen to receive their salary at dataBank CI?
5. **Credit risk monitoring** - which borrowers are approaching a payment
   delay (15-day threshold) and need follow-up before being classified as
   `Watchlist` (to monitor) or `Delinquent` (in default)?

## 3. Key indicators (KPIs) to track per segment

| Segment | Priority KPI | Why |
|---------|------------------|----------|
| Mass | Digital activation rate, open complaints | Largest segment (84 customers), cost-to-serve to watch |
| Affluent | 90-day average balance, number of products held | Highest cross-sell potential |
| Premier | Estimated revenue per customer (NBI), high-severity complaints | High-value customers, low tolerance for dissatisfaction |
| Youth | Mobile app activation, offers accepted | Digitally native segment, track engagement rather than balance |

Indicators tracked for every segment in the dashboard: number of at-risk
customers, offer acceptance rate, average complaint resolution time,
proportion of customers with a domiciled salary.

## 4. What would be missing for a real production Customer 360

- **GDPR consent (personal data protection) and data governance**: today,
  there is no detailed per-purpose consent mechanism (marketing, sharing,
  etc.), only a simple `marketing_opt_in` field.
- **Real-time data**: the file used is a snapshot taken at one point in
  time. A real Customer 360 tool would need a continuous update stream
  (called CDC, "Change Data Capture") instead of a full reload every time.
- **Fraud detection**: there is no dedicated fraud-detection data for
  transactions, other than the simple `is_disputed` flag (disputed
  transaction).
- **Multi-year history**: the time period covered (February 2024 to
  December 2025) is short for reliably analyzing trends.
- **Connection to an external credit bureau** and **computing the
  customer's real income (accounting NBI)** - see
  `docs/ml_problem_definition_en.md`, section 4.
- **A human validation step** before any automatic action triggered by a
  score. This project stays a decision-support tool: it never makes a
  decision on its own.
