# Business Understanding - dataBank CI Customer 360

> *[Version française disponible : [business_understanding.md](business_understanding.md)]*

**Author:** Ibrahima TRAORÉ - Analytics Engineer
**Date:** July 2026

## 1. Context

dataBank CI is a retail bank operating in Côte d'Ivoire (WAEMU zone, XOF
currency). The source portfolio covers 140 customers across 4 segments
(Mass, Affluent, Premier, Youth), with accounts, loans, cards, transactions,
interactions and complaints.

## 2. Five business decisions this project needs to support

1. **Advisor visit prioritization** - which customers should be contacted
   first this week among those showing disengagement signals?
2. **Cross-sell targeting** - which customers holding few products (e.g. the
   42 customers without a card) are good candidates for a targeted offer?
3. **Complaint triage** - which open complaints should be escalated first
   based on severity and potential impact on retention?
4. **Salary domiciliation upsell** - which high-income customers haven't yet
   domiciled their salary with dataBank CI?
5. **Credit risk monitoring** - which borrowers are approaching a payment
   delay threshold (15 days) and need follow-up before escalating to
   `Watchlist` or `Delinquent`?

## 3. Segment-driven KPIs

| Segment | Priority KPI | Why |
|---------|------------------|----------|
| Mass | Digital activation rate, open complaints | High volume (84 customers), sensitive to cost-to-serve |
| Affluent | 90-day average balance, number of products held | Highest cross-sell potential |
| Premier | Estimated NBI, high-severity complaints | High-value portfolio, low tolerance for dissatisfaction |
| Youth | Mobile app activation, offers accepted | Digitally native segment, engagement KPIs over balance |

Cross-segment KPIs tracked in the dashboard: number of at-risk customers,
offer conversion rate, average complaint resolution time, proportion of
customers with domiciled salary.

## 4. What is missing for a production-grade Customer 360

- **GDPR/local consent and data governance**: no granular purpose-based
  consent mechanism is modeled beyond the `marketing_opt_in` field.
- **Real-time data**: the dataset is a static extract; a production Customer
  360 would need incremental (CDC) ingestion rather than full loads.
- **Fraud scoring**: no transactional fraud detection data is available
  separately from the `is_disputed` flag.
- **Multi-year history**: the data window (2024-02 to 2025-12) is short for
  robust trend analysis.
- **External credit bureau integration** and **real accounting NBI** - see
  `docs/ml_problem_definition_en.md` section 4.
- **Human validation step** before any automated action triggered by the
  score (this project remains a decision-support tool, not an autonomous
  decision engine).
