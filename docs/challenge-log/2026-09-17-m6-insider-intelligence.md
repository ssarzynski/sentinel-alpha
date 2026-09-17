# Challenge Log — Milestone 6 Insider Intelligence
Date: 2026-09-17

## Claim challenged
"Insider buying/selling data can be converted directly into a high-confidence market signal."

## Strongest counterarguments
- Form 4 transaction codes have materially different economic meanings.
- Awards, exercises, gifts and tax-related dispositions can look directionally meaningful when they are not discretionary open-market decisions.
- Several filings by one insider are not several independent confirmations.
- Filing activity can be stale relative to market price and macro regime.
- A missing or failed ingestion run can be mistaken for absence of activity unless operational failures are explicit.
- Strong company-level insider evidence can still conflict with price, liquidity, macro or sector evidence.

## Design response
Milestone 6 separates transaction classification, Evidence persistence, cluster semantics and operational health. Derivative/non-discretionary activity is not promoted mechanically. Cluster detection requires distinct insiders. Worker runs persist success/error/failure state, and scheduled execution uses a PostgreSQL advisory lock to prevent overlap.

## Residual risks
- Issuer-specific compensation structures may require richer interpretation.
- Amended filings can alter earlier conclusions.
- SEC availability/rate limiting can delay evidence.
- Insider behavior can be informative without being predictive over a fixed horizon.
- Current rules require historical calibration before any scoring weight should be treated as validated.

## Decision
Retain insider intelligence as a contextual Evidence family. Do not allow it to independently authorize a trade or bypass the two-confirmation/human-approval decision gate.
