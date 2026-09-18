from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET


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


OPEN_MARKET_CODES = {"P", "S"}
OPTION_EXERCISE_CODES = {"M", "X"}
GRANT_AWARD_CODES = {"A"}
GIFT_CODES = {"G"}
TAX_CODES = {"F"}


def _value(node: ET.Element, path: str) -> str:
    found = node.find(path)
    return (found.text or "").strip() if found is not None else ""


def _decimal(value: str) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def parse_form4_xml(xml_text: str) -> tuple[InsiderTransaction, ...]:
    """Parse SEC ownership XML into normalized transactions without inferring motive."""
    root = ET.fromstring(xml_text)
    issuer = _value(root, "issuer/issuerName")
    ticker = _value(root, "issuer/issuerTradingSymbol") or None
    owner = root.find("reportingOwner")
    owner_name = _value(owner, "reportingOwnerId/rptOwnerName") if owner is not None else ""
    relationship = owner.find("reportingOwnerRelationship") if owner is not None else None
    roles: list[str] = []
    if relationship is not None:
        if _value(relationship, "isDirector") == "1": roles.append("director")
        if _value(relationship, "isOfficer") == "1": roles.append("officer")
        if _value(relationship, "isTenPercentOwner") == "1": roles.append("10% owner")
        title = _value(relationship, "officerTitle")
        if title: roles.append(title)

    output: list[InsiderTransaction] = []
    for derivative, path in ((False, ".//nonDerivativeTransaction"), (True, ".//derivativeTransaction")):
        for node in root.findall(path):
            footnotes = tuple(ref.attrib.get("id", "") for ref in node.findall(".//footnoteId") if ref.attrib.get("id"))
            output.append(InsiderTransaction(
                issuer=issuer,
                ticker=ticker,
                owner_name=owner_name,
                owner_roles=tuple(roles),
                transaction_code=_value(node, "transactionCoding/transactionCode"),
                acquired_disposed=_value(node, "transactionAmounts/transactionAcquiredDisposedCode/value"),
                shares=_decimal(_value(node, "transactionAmounts/transactionShares/value")),
                price_per_share=_decimal(_value(node, "transactionAmounts/transactionPricePerShare/value")),
                direct_or_indirect=_value(node, "ownershipNature/directOrIndirectOwnership/value") or None,
                is_derivative=derivative,
                footnotes=footnotes,
            ))
    return tuple(output)


def classify_transaction(tx: InsiderTransaction) -> InsiderClassification:
    code = tx.transaction_code.upper().strip(); ad = tx.acquired_disposed.upper().strip(); reasons: list[str] = []
    if code == "P": economic_type, direction, discretionary = "open_market_purchase", "buy", True
    elif code == "S": economic_type, direction, discretionary = "open_market_sale", "sell", True
    elif code in OPTION_EXERCISE_CODES:
        economic_type, direction, discretionary = "option_exercise", "acquire" if ad == "A" else "dispose", False; reasons.append("option/exercise transaction is not equivalent to an open-market trade")
    elif code in GRANT_AWARD_CODES:
        economic_type, direction, discretionary = "grant_or_award", "acquire" if ad == "A" else "dispose", False; reasons.append("issuer grant/award is not an open-market purchase")
    elif code in GIFT_CODES:
        economic_type, direction, discretionary = "gift", "transfer", False; reasons.append("gift transaction is non-market")
    elif code in TAX_CODES:
        economic_type, direction, discretionary = "tax_withholding_or_payment", "dispose" if ad == "D" else "acquire", False; reasons.append("tax-related disposition must not be treated as discretionary selling")
    else:
        economic_type, direction, discretionary = "other", "acquire" if ad == "A" else "dispose" if ad == "D" else "unknown", False; reasons.append(f"transaction code {code or 'UNKNOWN'} requires separate interpretation")
    if tx.is_derivative: reasons.append("derivative transaction")
    return InsiderClassification(economic_type, direction, discretionary, discretionary and not tx.is_derivative, tuple(reasons))


def role_weight(roles: tuple[str, ...]) -> float:
    normalized = {role.lower().strip() for role in roles}
    if "ceo" in normalized or "chief executive officer" in normalized: return 1.0
    if "cfo" in normalized or "chief financial officer" in normalized: return 0.95
    if "officer" in normalized: return 0.85
    if "director" in normalized: return 0.75
    if "10% owner" in normalized or "ten percent owner" in normalized: return 0.70
    return 0.50
