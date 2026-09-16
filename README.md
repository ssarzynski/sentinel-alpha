# Sentinel Alpha

Evidence-driven market intelligence and research platform.

## Mission

Sentinel Alpha is a read-only decision-support system designed to combine independent market, macroeconomic, fundamental, technical, and behavioral evidence into explainable research signals.

It is not an autonomous trading system, brokerage, or source of investment advice.

## MVP guardrails

- No leverage
- No options
- No automatic trading
- Minimum 2 independent confirmations before a candidate signal
- Maximum 2 new candidate entries per week
- Human review required before any financial action
- Every signal must retain its supporting evidence, source, timestamp, and conflicts
- Experimental research must not silently change production signal rules

## Initial asset universe

Equities: NVDA, AMD, TSM, AVGO, ASML, MSFT, AAPL, AMZN, META, GOOGL

Crypto/stablecoins: BTC, ETH, USDC, USDT, DAI

## Initial data-source strategy

- Federal Reserve / FRED: monetary policy and macroeconomic series
- U.S. Treasury: Treasury yields and related public data
- SEC: filings and corporate disclosures
- Messari: permitted crypto market, research, and fundamental/network intelligence
- Finviz: permitted equity screening, breadth, technical, fundamental, and news inputs
- Invo: only permitted/authorized aggregate behavioral or positioning data; no automatic copying of traders

## Development path

1. Foundation
2. Data providers and validation
3. Macro market-regime engine
4. Asset analysis and confirmation engine
5. Risk gate and audit trail
6. Historical backtesting
7. Read-only dashboard
8. Paper-trading validation

## Security

This repository is public during initial development. Never commit API keys, passwords, tokens, private account data, broker credentials, or other secrets. Use environment variables and local `.env` files that are ignored by Git.

## Status

**v0.1 — Foundation initialized**
