# Provider Terms & Automation Readiness

Verified: 2026-09-18. This is an engineering compliance gate, not legal advice. Re-check provider terms before production activation and whenever terms, plans, or intended redistribution change.

| Provider | Automated ingestion status | Requirements / restrictions | Sentinel action |
|---|---|---|---|
| SEC EDGAR | APPROVED WITH CONTROLS | Public EDGAR data is freely accessible. SEC fair-access guidance caps automated access at 10 requests/second total and requires efficient, classified automation. | Keep descriptive User-Agent, global <=10 req/s limiter, caching/backoff, and provenance. |
| FRED | APPROVED WITH CONTROLS | API key required. FRED requires attribution/endorsement disclaimer; individual series may have third-party rights/restrictions. Limits may be imposed or changed. | Use API key from secrets, add required notice, preserve series/source attribution, and maintain per-series rights metadata. |
| U.S. Treasury Fiscal Data | APPROVED FOR PUBLIC API DATA; RECHECK DATASET NOTES | Treasury publishes machine-readable historical/current datasets and accessible APIs. Dataset metadata/known limitations remain authoritative. | Use documented API endpoints; retain dataset metadata and source provenance. Re-check dataset-specific notes. |
| Alpha Vantage | BLOCKED PENDING LICENSE CONFIRMATION | Current terms describe the standard grant as personal, non-commercial unless otherwise agreed; the terms classify investment analysis/research/testing/monitoring beyond personal usage as commercial use. | Do not enable production Sentinel ingestion until the account/license is confirmed to cover Sentinel Alpha's intended use. |
| Messari | CONDITIONAL / ACCOUNT PERMISSION REQUIRED | API uses API-key/x402 authentication and exposes account permissions/credits. Messari documentation states API data is for internal use and directs redistribution requests to Messari. 429 responses require backoff. | Permit only endpoints granted to the configured account; internal analysis only unless redistribution rights are confirmed; implement credit/rate-limit controls. |
| Finviz | BLOCKED PENDING OFFICIAL AUTOMATION LICENSE VERIFICATION | No sufficiently clear current official API/automation permission was verified in this review. | Do not scrape or automate production ingestion. Use only after official permission/licensing is documented. |
| Invo | BLOCKED / PROVIDER IDENTITY & TERMS UNVERIFIED | No authoritative market-data API/terms source matching the planned Sentinel provider was verified. | Keep disabled. Identify exact vendor/product and official terms before any automated retrieval. |

## Enforcement principles

1. A configured API key is not itself proof of redistribution or commercial-use rights.
2. Providers marked BLOCKED must fail closed: no automated production retrieval.
3. Provider credentials remain deployment secrets and never enter Git, logs, evidence payloads, or client-side code.
4. Cache and retention must respect provider-specific rights. Sentinel provenance should identify provider, endpoint/dataset, retrieval time, and applicable source identity.
5. Rate limiting and exponential backoff are mandatory where provider guidance or HTTP 429 responses require them.
6. Derived analysis must not silently strip source attribution or convert restricted source data into an unrestricted redistribution feed.
7. Re-verify this matrix before launch and record the review date.

## Official references

- SEC Developer Resources / EDGAR fair access: https://www.sec.gov/about/developer-resources
- SEC Accessing EDGAR Data: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- FRED API Terms: https://fred.stlouisfed.org/docs/api/terms_of_use.html
- FRED API keys: https://fred.stlouisfed.org/docs/api/api_key.html
- Treasury Fiscal Data: https://fiscaldata.treasury.gov/
- Alpha Vantage Terms: https://www.alphavantage.co/terms_of_service/
- Alpha Vantage API documentation: https://www.alphavantage.co/documentation/
- Messari API: https://api.messari.io/
- Messari API documentation: https://docs.messari.io/
