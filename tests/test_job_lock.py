from app.services.job_lock import _lock_id, advisory_job_lock


class FakeSession:
    def __init__(self, acquired=True): self.acquired = acquired; self.calls = []
    def scalar(self, statement, params):
        sql = str(statement); self.calls.append((sql, params))
        if "try_advisory_lock" in sql: return self.acquired
        return True


def test_lock_id_is_stable_and_name_specific():
    assert _lock_id("SEC_FORM4") == _lock_id("SEC_FORM4")
    assert _lock_id("SEC_FORM4") != _lock_id("OTHER")


def test_acquired_lock_is_always_released():
    db = FakeSession(True)
    with advisory_job_lock(db, "SEC_FORM4") as acquired:
        assert acquired is True
    assert len(db.calls) == 2
    assert "pg_try_advisory_lock" in db.calls[0][0]
    assert "pg_advisory_unlock" in db.calls[1][0]


def test_busy_lock_prevents_overlap_without_unlocking_other_owner():
    db = FakeSession(False)
    with advisory_job_lock(db, "SEC_FORM4") as acquired:
        assert acquired is False
    assert len(db.calls) == 1


def test_exception_still_releases_owned_lock():
    db = FakeSession(True)
    try:
        with advisory_job_lock(db, "SEC_FORM4"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert "pg_advisory_unlock" in db.calls[-1][0]
