# Sentinel Alpha Data Source Registry

| Source | Domain | Initial role | Integration status |
|---|---|---|---|
| Federal Reserve / FRED | Macro | Policy rates, macro series | Planned |
| U.S. Treasury | Macro | Treasury yields and public debt-market data | Planned |
| SEC | Equities | Filings and corporate disclosures | Planned |
| Messari | Crypto | Market, research, and permitted fundamental/network data | Planned |
| Finviz | Equities | Screening, breadth, technical/fundamental inputs, news | Planned |
| Invo | Behavioral | Authorized aggregate trader/positioning information | Research / permissions review |

## Integration rules

1. Prefer official APIs, exports, or documented access methods.
2. Do not bypass authentication, paywalls, rate limits, robots controls, or technical restrictions.
3. Verify terms/licensing before automated ingestion or redistribution.
4. Record provider, retrieval time, and data-quality status.
5. Do not treat any provider as a sole source of truth for a material signal.
6. Provider outages must degrade Sentinel safely rather than create fabricated data.
