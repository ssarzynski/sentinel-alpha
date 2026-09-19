import math
import sqlite3

import pytest

from sentinel_alpha.paper_ledger import PaperLedger


def database(tmp_path):
    path = tmp_path / "sentinel.db"
    with sqlite3.connect(path) as connection:
        connection.execute("""CREATE TABLE evaluations (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT, evaluation_id TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL, asset TEXT NOT NULL, payload TEXT NOT NULL,
            previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL UNIQUE)""")
        connection.execute("INSERT INTO evaluations(evaluation_id,created_at,asset,payload,previous_hash,entry_hash) VALUES('eval-1','now','NVDA','{}','p','h')")
    return path


def test_paper_lifecycle_and_integrity(tmp_path):
    ledger = PaperLedger(database(tmp_path))
    ledger.append(evaluation_id="eval-1", asset="nvda", action="entry", price=100.0, quantity=2.0)
    ledger.append(evaluation_id="eval-1", asset="NVDA", action="exit", price=110.0, quantity=1.0)
    assert ledger.verify_integrity() is True


@pytest.mark.parametrize("price,quantity", [(0,1),(-1,1),(math.nan,1),(math.inf,1),(1,0),(1,math.nan)])
def test_invalid_prices_and_quantities_rejected(tmp_path, price, quantity):
    ledger = PaperLedger(database(tmp_path))
    with pytest.raises(ValueError):
        ledger.append(evaluation_id="eval-1", asset="NVDA", action="ENTRY", price=price, quantity=quantity)


def test_exit_cannot_exceed_open_paper_position(tmp_path):
    ledger = PaperLedger(database(tmp_path))
    ledger.append(evaluation_id="eval-1", asset="NVDA", action="ENTRY", price=100, quantity=1)
    with pytest.raises(ValueError, match="exceeds open"):
        ledger.append(evaluation_id="eval-1", asset="NVDA", action="EXIT", price=101, quantity=2)


def test_event_requires_matching_evaluation(tmp_path):
    ledger = PaperLedger(database(tmp_path))
    with pytest.raises(ValueError, match="existing evaluation"):
        ledger.append(evaluation_id="missing", asset="NVDA", action="ENTRY", price=100, quantity=1)
    with pytest.raises(ValueError, match="must match"):
        ledger.append(evaluation_id="eval-1", asset="BTC", action="ENTRY", price=100, quantity=1)


def test_tampering_is_detected(tmp_path):
    path = database(tmp_path)
    ledger = PaperLedger(path)
    event = ledger.append(evaluation_id="eval-1", asset="NVDA", action="ENTRY", price=100, quantity=1)
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE paper_events SET price=999 WHERE event_id=?", (event,))
    assert ledger.verify_integrity() is False
