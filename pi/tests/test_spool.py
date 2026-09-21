from pi.node.spool import Spool


def test_append_then_pending_returns_it(tmp_path):
    spool = Spool(str(tmp_path / "spool.db"))

    row_id = spool.append({"imsi": "111222333444555"})
    pending = spool.pending()

    assert len(pending) == 1
    assert pending[0]["id"] == row_id
    assert pending[0]["observation"] == {"imsi": "111222333444555"}
    assert pending[0]["attempts"] == 0


def test_mark_sent_then_delete_removes_from_pending(tmp_path):
    spool = Spool(str(tmp_path / "spool.db"))
    row_id = spool.append({"imsi": "111222333444555"})

    spool.mark_sent([row_id])
    spool.delete([row_id])

    assert spool.pending() == []


def test_survives_reopen(tmp_path):
    db_path = str(tmp_path / "spool.db")
    spool1 = Spool(db_path)
    spool1.append({"imsi": "111222333444555"})

    spool2 = Spool(db_path)
    pending = spool2.pending()

    assert len(pending) == 1
    assert pending[0]["observation"] == {"imsi": "111222333444555"}


def test_record_attempt_increments_attempts_counter(tmp_path):
    spool = Spool(str(tmp_path / "spool.db"))
    row_id = spool.append({"imsi": "111222333444555"})

    spool.record_attempt([row_id])
    spool.record_attempt([row_id])

    pending = spool.pending()
    assert pending[0]["attempts"] == 2


def test_counts_reports_pending_and_sent(tmp_path):
    spool = Spool(str(tmp_path / "spool.db"))
    id1 = spool.append({"imsi": "111222333444555"})
    spool.append({"imsi": "222333444555666"})
    spool.mark_sent([id1])

    counts = spool.counts()

    assert counts == {"pending": 1, "sent": 1}


def test_pending_respects_limit(tmp_path):
    spool = Spool(str(tmp_path / "spool.db"))
    for i in range(5):
        spool.append({"imsi": f"11122233344455{i}"})

    pending = spool.pending(limit=3)

    assert len(pending) == 3


def test_connect_sets_busy_timeout_to_avoid_lock_races(tmp_path):
    spool = Spool(str(tmp_path / "spool.db"))

    conn = spool._connect()
    try:
        row = conn.execute("PRAGMA busy_timeout").fetchone()
    finally:
        conn.close()

    assert row[0] == 5000
