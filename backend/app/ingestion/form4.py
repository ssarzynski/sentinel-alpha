from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class InsiderTransaction:
    issuer: str
    ticker: str | None
    owner_name: str
    owner_roles: tuple[str, ...]
    transaction_code: str
    acquired_disposed: str
    shares: Decimal | None
    price_per_share: Decimal | None
    direct_or_indirect: str | None
    is_derivative: bool
    footnotes: tuple[str, ...] = ()


@dataclass(frozen=True)
class InsiderClassification:
    economic_type: str
    direction: str
    discretionary_open_market: bool
    signal_eligible: bool
    reasons: tuple[str, ...]


# SEC Form 4 transaction codes have distinct economic meanings. Do not reduce
# them to a generic buy/sell flag.
OPEN_MARKET_CODES = {"P", "S"}
OPTION_EXERCISE_CODES = {"M", "X"}
GRANT_AWARD_CODES = {"A"}
GIFT_CODES = {"G"}
TAX_CODES = {"F"}


def classify_transaction(tx: InsiderTransaction) -> InsiderClassification:
    code = tx.transaction_code.upper().strip()
    ad = tx.acquired_disposed.upper().strip()
    reasons: list[str] = []

    if code == "P":
        economic_type = "open_market_purchase"
        direction = "buy"
        discretionary = True
    elif code == "S":
        economic_type = "open_market_sale"
        direction = "sell"
        discretionary = True
    elif code in OPTION_EXERCISE_CODES:
        economic_type = "option_exercise"
        direction = "acquire" if ad == "A" else "dispose"
        discretionary = False
        reasons.append("option/exercise transaction is not equivalent to an open-market trade")
    elif code in GRANT_AWARD_CODES:
        economic_type = "grant_or_award"
        direction = "acquire" if ad == "A" else "dispose"
        discretionary = False
        reasons.append("issuer grant/award is not an open-market purchase")
    elif code in GIFT_CODES:
        economic_type = "gift"
        direction = "transfer"
        discretionary = False
        reasons.append("gift transaction is non-market")
    elif code in TAX_CODES:
        economic_type = "tax_withholding_or_payment"
        direction = "dispose" if ad == "D" else "acquire"
        discretionary = False
        reasons.append("tax-related disposition must not be treated as discretionary selling")
    else:
        economic_type = "other"
        direction = "acquire" if ad == "A" else "dispose" if ad == "D" else "unknown"
        discretionary = False
        reasons.append(f"transaction code {code or 'UNKNOWN'} requires separate interpretation")

    if tx.is_derivative:
        reasons.append("derivative transaction")

    # Signal eligibility is deliberately narrow. Open-market transactions may
    # contribute evidence, but still require independent confirmation elsewhere.
    signal_eligible = discretionary and not tx.is_derivative
    return InsiderClassification(
        economic_type=economic_type,
        direction=direction,
        discretionary_open_market=discretionary,
        signal_eligible=signal_eligible,
        reasons=tuple(reasons),
    )


def role_weight(roles: tuple[str, ...]) -> float:
    normalized = {role.lower().strip() for role in roles}
    if "ceo" in normalized or "chief executive officer" in normalized:
        return 1.0
    if "cfo" in normalized or "chief financial officer" in normalized:
        return 0.95
    if "officer" in normalized:
        return 0.85
    if "director" in normalized:
        return 0.75
    if "10% owner" in normalized or "ten percent owner" in normalized:
        return 0.70
    return 0.50
