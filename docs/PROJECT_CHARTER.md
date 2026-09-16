# Sentinel Alpha Project Charter

## Objective

Build a read-only, evidence-driven market intelligence system that combines independent market, macroeconomic, fundamental, technical, and behavioral evidence into explainable research signals.

## MVP scope

The first release covers a fixed 15-asset universe: NVDA, AMD, TSM, AVGO, ASML, MSFT, AAPL, AMZN, META, GOOGL, BTC, ETH, USDC, USDT, and DAI.

## Non-goals

- No automatic trading
- No brokerage integration in the MVP
- No leverage
- No options
- No trader-copying automation
- No opaque AI-only decisions

## Core operating rules

1. A candidate signal requires at least two independent confirmations.
2. No more than two new candidate entries may be recorded in a calendar week.
3. Human review is required before any financial action.
4. Every signal must preserve its evidence, source, timestamp, and conflicts.
5. Research experiments cannot silently modify production rules.
6. Provider terms, licensing, and API permissions must be verified before automated ingestion.

## Success criteria for v0.1

- Reproducible local development environment
- Validated data-provider interfaces
- Market-regime engine with auditable inputs
- Explainable confirmation engine
- Risk gate
- Historical signal log
- Automated tests for core rules
- No secrets committed to the repository
