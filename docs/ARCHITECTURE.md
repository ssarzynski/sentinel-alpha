# Sentinel Alpha — Complete Build Architecture

## Mission
Build an evidence-first investment intelligence and research platform. Sentinel collects verifiable data, preserves provenance, evaluates deterministic versioned rules, measures outcomes, learns through controlled research, and never places trades automatically.

## Non-negotiable guardrails
1. Facts and derived analysis remain distinguishable.
2. Every material claim retains source/provenance and timestamps.
3. Evidence, decisions, rule versions, journal entries, and audit events are append-only or versioned.
4. A signal requires at least two independent confirmation categories before becoming eligible for human review.
5. No score authorizes a trade. Human approval is mandatory.
6. Hypotheses do not become production rules without historical testing and documented review.
7. Statistical/ML models must beat the simpler rules baseline out-of-sample before promotion.

## End-to-end pipeline
Sources -> Ingestion -> Normalization/Verification -> Evidence Objects -> Feature Engines -> Rule Engine -> Signal/Prediction -> Human Review -> Outcome Tracker -> Accuracy/Calibration -> Research Journal -> Pattern Discovery -> Backtest/OOS Validation -> Rule Proposal -> Human Approval -> Versioned Rule

## Product surfaces
### Sentinel Alpha
Investor/research dashboard: watchlists, evidence timeline, signals, scores, research journal, challenge log, accuracy, portfolio intelligence, and research lab.

### Sentinel Studio
Administrative control plane: rule editor, source manager, research manager, AI-agent manager, audit viewer, release manager, health/operations.

## Platform modules
### 1. Data Source + Market Data Engine
Primary/authoritative sources first: SEC EDGAR, issuer filings/IR, exchanges and official market sources, Treasury/Federal Reserve and other government economic sources. Secondary reputable providers may add context but cannot silently replace primary evidence. Collect U.S. equities, ETFs, indexes, Treasury yields, VIX, dollar index, commodities, BTC, ETH and stablecoins with timestamps, provider identity, quality state and provenance.

### 2. SEC Intelligence Engine
Form 4, 8-K, 10-Q, 10-K, 13F, 13D, 13G. Preserve accession identifiers, filing timestamps, original links, verification state, summaries, materiality and derived explanations separately.

### 3. Insider Intelligence
Classify CEO/CFO/director transactions, discretionary open-market purchases/sales, cluster activity, 10b5-1 transactions, option exercises and tax-related transactions. Do not collapse economically different transactions into a generic buy/sell flag.

### 4. Technical Engine
Deterministic statistics: trend, momentum, relative strength, support/resistance, volume, ATR, EMA, MACD and RSI. Indicators are features, not opinions or automatic trade instructions.

### 5. Fundamental Engine
Revenue, margins, EPS, cash, debt, ROIC, FCF, growth and valuation. Preserve period, units, source and restatement/version information.

### 6. Crypto Intelligence
BTC, ETH, stablecoins, ETF flows, hashrate, difficulty, exchange inflows/outflows and later validated on-chain/whale features. Provider methodology must be recorded.

### 7. News Intelligence
Measure importance, source credibility, sentiment, novelty, market reaction and historical source/signal accuracy. Headline volume alone is not a signal.

### 8. Central Evidence Database
Canonical Evidence Objects link event ID, asset/ticker, source, observed/event timestamps, raw reference/hash, normalized facts, verification state, confidence, category, score, outcome and notes. Evidence provenance is immutable.

### 9. Rule & Confirmation Engine
Versioned YAML rules evaluated deterministically. Store exact rule version, facts, evidence IDs, condition results and output for every evaluation. Independent confirmation is based on evidence categories/provenance, not duplicate articles repeating one fact.

### 10. Signal & Prediction Ledger
Every emitted alert records asset, prediction/direction, confidence, reference price/time, evidence IDs, rule versions, regime/context and human-review state.

### 11. Outcome & Accuracy Tracker
Evaluate predictions at 1d, 5d, 30d and 90d. Track returns, benchmark-relative returns, winner/loser criteria, accuracy, average return, false positives, drawdown, Sharpe where statistically appropriate, and confidence calibration. Freeze the information set at prediction time to prevent look-ahead bias.

### 12. Research Journal
Append-only/versioned hypotheses and experiments: hypothesis, rationale, data window, methodology, metrics, results, limitations, decision (approved/rejected/modified), confidence and links to evidence/rules/backtests.

### 13. Pattern Discovery Lab
Ask which signals worked/failed, whether false positives changed, whether macro/insider/context features mattered, and whether weights merit a proposal. Discovery may propose changes; it cannot silently mutate production rules.

### 14. Historical Intelligence / Quant Research
Point-in-time datasets, transaction-cost assumptions, benchmark comparison, walk-forward/out-of-sample validation, regime analysis, leakage controls, reproducibility, backtesting and paper trading. Advanced models must compete against the rules baseline.

### 15. Portfolio Intelligence
Risk, exposure, correlation, concentration, allocation research and decision ledger. Research only; no automatic execution.

### 16. AI Research Agents
SEC Analyst, Macro Analyst, Crypto Analyst, Risk Officer, Portfolio Analyst and Research Librarian. Agents produce attributed research artifacts and proposals; they cannot invent evidence, rewrite immutable history, approve their own production changes, or execute trades.

### 17. Audit & Governance
Audit ingestion, evidence transformations, rule evaluations, signal creation, human approvals, rule promotions, model releases and administrative changes. Record actor, timestamp, object/version and reason.

### 18. Infrastructure
FastAPI, PostgreSQL, SQLAlchemy/Alembic, React/TypeScript, Redis, Docker Compose, Nginx, CI/CD, structured logging, health checks, backups, monitoring and security hardening.

## Current implementation status
- M1 application foundation: baseline built.
- SEC ingestion/evidence foundation: built and being extended.
- Immutable Evidence Engine: baseline built.
- M4 versioned YAML Rule Engine: active; deterministic evaluator and first confirmation rule implemented.
- Next active slice: immutable rule-evaluation audit records + evidence independence/provenance counting.
- Immediately after: Signal/Prediction Ledger + Outcome/Accuracy Tracker + Research Journal foundation.

## Build sequence
M1 Foundation -> M2 SEC -> M3 Evidence -> M4 Rules/Audit/Provenance -> M5 Signal/Outcome/Accuracy/Journal -> M6 Technical/Fundamental/Insider -> M7 Market/Crypto/News connectors -> M8 Pattern Discovery/Historical Intelligence -> M9 Portfolio/Quant Lab -> M10 AI Research Agents -> M11 Sentinel Studio -> M12 Production hardening/deployment.

## Definition of done
A feature is not complete without source code, tests, migration when persistent state changes, API/docs, release notes, observability/error behavior, and research/challenge-log documentation when it affects investment logic.
