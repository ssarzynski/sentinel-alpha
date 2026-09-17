from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class DataQualityFinding:
    asset: str
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class DataQualityGate:
    status: str
    risk_signals_allowed: bool
    findings: tuple[DataQualityFinding, ...]


def evaluate_data_quality_gate(rows: Iterable[Mapping[str, object]]) -> DataQualityGate:
    """Gate risk-dependent signals using provenance/freshness facts only.

    WITHHOLD means risk-dependent signals must not be emitted. DEGRADED means
    accepted data is usable but quality concerns must remain attached. This
    function never creates orders or authorizes financial actions.
    """
    findings: list[DataQualityFinding] = []
    withhold = False
    degraded = False

    for row in rows:
        asset = str(row.get("asset", "UNKNOWN"))
        accepted = int(row.get("accepted_observations", 0) or 0)
        rejected = int(row.get("rejected_observations", 0) or 0)
        families = int(row.get("independent_source_families", 0) or 0)
        fresh = bool(row.get("fresh", False))

        if accepted == 0:
            withhold = True
            findings.append(DataQualityFinding(asset, "no_accepted_data", "block", "No accepted market observations are available"))
        if families < 2:
            withhold = True
            findings.append(DataQualityFinding(asset, "insufficient_independent_confirmation", "block", "Fewer than two independent source families confirm the asset"))
        if not fresh:
            withhold = True
            findings.append(DataQualityFinding(asset, "stale_market_data", "block", "Latest accepted market observation is stale or missing"))
        if rejected > 0:
            degraded = True
            findings.append(DataQualityFinding(asset, "rejected_or_disputed_observations", "warning", "Rejected or disputed observations exist and were excluded"))

    findings.sort(key=lambda item: (item.asset, item.severity, item.code))
    if withhold:
        status = "WITHHOLD"
    elif degraded:
        status = "DEGRADED"
    else:
        status = "PASS"
    return DataQualityGate(status=status, risk_signals_allowed=not withhold, findings=tuple(findings))
