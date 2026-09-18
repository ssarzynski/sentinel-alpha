# Sentinel Studio Frontend Architecture

## Purpose
Sentinel Studio is an authenticated, read-oriented intelligence console. Its frontend presents portfolio analytics, provenance-controlled market data, policy findings, SEC ingestion operations and primary-source filings. It is decision support only; UI refactors must not introduce order placement or automatic trading.

## Component boundaries
- `frontend/src/main.tsx` — application controller. Owns authentication headers, API loading, selected-portfolio state, policy-evaluation request state and top-level composition. Keep detailed table/card rendering out of this file.
- `frontend/src/components.tsx` — small reusable presentation primitives and formatters: badges, empty states, section headers, dates, money and percentages.
- `frontend/src/portfolioPanels.tsx` — portfolio risk/exposure, market provenance, correlation and Decision Ledger presentation.
- `frontend/src/operations.tsx` — durable ingestion-run history and SEC filing presentation.
- `frontend/src/style.css` — shared visual system, responsive behavior and accessibility states.

## API ownership
`main.tsx` currently coordinates these authenticated backend resources:
- `/api/sec/filings`
- `/api/studio/ingestion/health`
- `/api/studio/ingestion/runs`
- `/api/portfolios`
- `/api/portfolios/{key}/analytics`
- `/api/portfolios/{key}/risk`
- `/api/portfolios/{key}/policy/history`
- `/api/portfolios/{key}/provenance`
- explicit `POST /api/portfolios/{key}/policy/evaluate`

Panel components receive typed data and callbacks; they should not silently perform financial actions or duplicate API orchestration.

## UI conventions
- Green badges mean accepted/current/healthy states, not a recommendation to buy or trade.
- Warning badges mean stale, withheld, incomplete-confirmation or review-needed states.
- Failure badges represent operational failure.
- Empty states must distinguish legitimate missing/insufficient data from loading/authentication/backend failure where possible.
- Tables may scroll horizontally on small screens rather than compressing financial data until unreadable.
- Interactive controls require visible keyboard focus and practical mobile touch targets.
- Respect `prefers-reduced-motion`.

## Debugging workflow
1. Confirm the frontend production build succeeds.
2. Check the top-level operational message for authentication/backend failure.
3. For SEC problems, inspect ingestion health/runs and then use `M7_SIGNAL_AND_FORM4_DEBUGGING.md`.
4. For portfolio gaps, distinguish unavailable analytics from provenance/risk intentionally withheld by backend quality gates.
5. Do not "fix" a withheld backend value by calculating an ungoverned substitute in the browser.

## Maintenance rules
- Keep `main.tsx` focused on state/orchestration.
- Add reusable visual behavior to `components.tsx` rather than cloning markup/styles.
- Add domain presentation to the appropriate panel module.
- Preserve backend reason/status semantics in the UI.
- Update this document when component ownership, API ownership or safety behavior changes.
- Run frontend build, backend tests and Compose smoke verification before considering a structural UI change complete.
