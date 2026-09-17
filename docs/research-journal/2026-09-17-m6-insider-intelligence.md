# Research Journal — Milestone 6 Insider Intelligence
Date: 2026-09-17

## Hypothesis
SEC Form 4 data can improve Sentinel Alpha's research process if transaction semantics, provenance and distinct-insider behavior are preserved instead of treating every insider filing as equivalent.

## Engineering conclusion
The useful research object is not simply "a Form 4 exists." Sentinel must distinguish open-market purchases/sales from awards, gifts, exercises, tax-related activity and derivatives; preserve the filing as evidence; and avoid double-counting repeated filings by the same person as independent confirmation.

## Implementation consequences
1. Normalize filings into immutable Evidence with accession/source provenance.
2. Keep deterministic transaction classification separate from scoring.
3. Require distinct insiders for cluster semantics.
4. Treat role information as context rather than automatic proof of signal quality.
5. Persist ingestion execution/failures so missing data cannot silently masquerade as "no insider activity."
6. Prevent overlapping workers because duplicate ingestion cycles can distort operational confidence even when record-level deduplication exists.

## Validation lesson
Unit tests and frontend builds were insufficient to prove runtime readiness. Docker Compose smoke testing exposed missing production dependencies (`email-validator` and `python-multipart`) only when FastAPI booted inside the real container stack. System-level smoke testing is therefore a permanent completion gate.

## Research boundary
Insider activity is one evidence family, not a standalone trade instruction. Future calibration should measure whether particular transaction classes, insider clusters and timing windows add predictive value after controlling for market regime, price trend and independent evidence.
