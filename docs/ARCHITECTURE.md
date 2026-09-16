# Sentinel Alpha Architecture v0.1

```text
External Sources
  |-- Federal Reserve / FRED
  |-- U.S. Treasury
  |-- SEC
  |-- Messari
  |-- Finviz
  |-- Invo (authorized data only)
        |
        v
Data Provider Layer
        |
        v
Normalization + Validation
        |
        +------> Evidence Store
        |
        v
Feature / Analysis Layer
        |
        +--> Macro Regime Engine
        +--> Technical Engine
        +--> Fundamental Engine
        +--> Behavioral/Sentiment Engine
        |
        v
Confirmation Engine
        |
        v
Risk Gate
        |
        v
Signal Record + Audit Trail
        |
        v
Read-only Dashboard / Research API
```

## Design principles

- Separate ingestion, analysis, decision rules, and presentation.
- Treat external data as untrusted until validated.
- Preserve source and timestamp metadata for every material observation.
- Keep deterministic production rules separate from AI-generated explanations.
- Fail closed when required data is stale, missing, contradictory, or unauthorized.
- Never allow an AI explanation to override a hard risk or confirmation rule.

## Initial technology direction

- Python for core analytics
- FastAPI for service/API layer
- PostgreSQL for durable structured data
- Redis for caching/queues where justified
- React + TypeScript for the eventual dashboard
- Docker for reproducible development and deployment
- GitHub Actions for automated tests and quality checks
