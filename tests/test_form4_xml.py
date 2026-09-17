from decimal import Decimal

import pytest

from app.ingestion.form4_xml import parse_form4_xml


FORM4 = """<?xml version="1.0"?>
<ownershipDocument>
  <issuer><issuerName>NVIDIA CORP</issuerName><issuerTradingSymbol>NVDA</issuerTradingSymbol></issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>DOE JANE</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>0</isDirector><isOfficer>1</isOfficer><isTenPercentOwner>0</isTenPercentOwner>
      <officerTitle>Chief Financial Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>1,250</value></transactionShares>
        <transactionPricePerShare><value>200.50</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
      <ownershipNature><directOrIndirectOwnership><value>D</value></directOrIndirectOwnership></ownershipNature>
      <footnoteId id="F1"/>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
  <derivativeTable>
    <derivativeTransaction>
      <transactionCoding><transactionCode>M</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>100</value></transactionShares>
        <transactionPricePerShare><value>10</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </derivativeTransaction>
  </derivativeTable>
</ownershipDocument>"""


def test_parses_non_derivative_and_derivative_transactions():
    rows = parse_form4_xml(FORM4)
    assert len(rows) == 2
    purchase, option = rows
    assert purchase.issuer == "NVIDIA CORP"
    assert purchase.ticker == "NVDA"
    assert purchase.owner_name == "DOE JANE"
    assert "officer" in purchase.owner_roles
    assert "Chief Financial Officer" in purchase.owner_roles
    assert purchase.transaction_code == "P"
    assert purchase.shares == Decimal("1250")
    assert purchase.price_per_share == Decimal("200.50")
    assert purchase.is_derivative is False
    assert purchase.footnotes == ("F1",)
    assert option.transaction_code == "M"
    assert option.is_derivative is True


def test_ticker_override_is_normalized():
    assert parse_form4_xml(FORM4, ticker="nvda")[0].ticker == "NVDA"


def test_invalid_xml_and_missing_owner_fail_closed():
    with pytest.raises(ValueError, match="invalid Form 4 XML"):
        parse_form4_xml("<broken")
    with pytest.raises(ValueError, match="no reporting owner"):
        parse_form4_xml("<ownershipDocument><issuer><issuerName>X</issuerName></issuer></ownershipDocument>")


def test_invalid_numeric_data_fails_closed():
    bad = FORM4.replace("1,250", "not-a-number")
    with pytest.raises(ValueError, match="invalid decimal"):
        parse_form4_xml(bad)
