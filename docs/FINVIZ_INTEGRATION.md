# Finviz integration gate

Sentinel Alpha must not scrape Finviz pages or treat unlicensed page data as an automated production feed.

As verified against Finviz's official product/help material on 2026-09-17, Finviz Elite advertises export/API access and automated workflows, while the regular service uses delayed stock quotes. Raw historical data redistribution is restricted. The repository therefore keeps `FINVIZ_SCREENING` as a normalization/provenance adapter only until an authorized Elite/API credential and exact endpoint/response contract are configured and verified.

## Production rule

- No HTML scraping.
- No synthetic market confirmation when credentials or authorized data are unavailable.
- Finviz evidence remains independent from SEC evidence only when it is obtained through the authorized Finviz channel and represents market/screening observations rather than redistributed SEC filing content.
- Credentials belong in environment/secret storage and must never be committed.
- Provider failures fail closed: no record means no confirmation.

## Next implementation gate

Before adding network retrieval, verify the account's enabled API/export capability and the current official endpoint/response schema. Add fixture-driven parsing tests first, then a credential-gated integration test. Production code must not infer an endpoint by scraping the website.
