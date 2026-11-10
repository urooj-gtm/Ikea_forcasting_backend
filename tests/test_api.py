import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

# The sample SPI file is business data and is not committed; these tests need it in data/.
pytestmark = pytest.mark.skipif(not config.DEFAULT_SNAPSHOT.exists(), reason="sample SPI file not present in data/")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_snapshot_loaded(client):
    snaps = client.get("/api/snapshots").json()
    assert snaps[0]["snapshot_week"] == "202637" and snaps[0]["summary_rows"] == 1784


def test_overview_totals(client):
    ov = client.get("/api/overview").json()
    assert ov["articles"] == 1784 and round(ov["planned_total"]) == 18092508


def test_status_filter(client):
    ov = client.get("/api/overview", params={"status": ["Active"]}).json()
    assert ov["articles"] == 539


def test_weekly_reconciles_across_granularities(client):
    totals = {g: sum(r["planned_qty"] for r in client.get("/api/weekly", params={"granularity": g}).json()) for g in ("week", "month", "year")}
    assert len({round(v) for v in totals.values()}) == 1


def test_bad_granularity(client):
    assert client.get("/api/weekly", params={"granularity": "decade"}).status_code == 422


def test_article_detail_and_404(client):
    art = client.get("/api/articles", params={"limit": 1}).json()[0]["article"]
    d = client.get(f"/api/articles/{art}").json()
    assert len(d["schedule"]) == 52
    assert client.get("/api/articles/does-not-exist").status_code == 404


def test_unknown_snapshot_404(client):
    assert client.get("/api/overview", params={"snapshot": "209999"}).status_code == 404


def test_compare_same_snapshot_rejected(client):
    r = client.post("/api/compare", params={"old_snapshot": "202637", "new_snapshot": "202637"})
    assert r.status_code == 422


def test_upload_rejects_garbage(client):
    r = client.post("/api/snapshots", files={"file": ("x.xls", b"not an spi file")})
    assert r.status_code == 422


def test_insights(client):
    life = client.get("/api/insights/lifecycle").json()
    assert {r["status"]: r["articles"] for r in life} == {"Active": 539, "Discontinued": 921, "New": 324}
    top = client.get("/api/insights/top-articles", params={"n": 5}).json()
    assert len(top) == 5 and top[0]["supply_plan_52w"] >= top[-1]["supply_plan_52w"]
    assert len(client.get("/api/insights/balance").json()) == 1784
    exp = client.get("/api/insights/exposure", params={"status": ["Active"]}).json()
    assert [r["status"] for r in exp] == ["Active"]


def test_article_detail_has_stock(client):
    art = client.get("/api/articles", params={"limit": 1}).json()[0]["article"]
    d = client.get(f"/api/articles/{art}").json()
    assert set(d["stock"]) == {"dc_stock", "safety_stock", "in_transit", "open_orders"}


def test_prophet_includes_history(client):
    p = client.get("/api/prophet", params={"periods": 4}).json()
    assert len(p["history"]) == 52 and len(p["points"]) == 4


def test_compare_payload_shape(client):
    # Shift a copy of the loaded snapshot one week later with a few edits to exercise the full payload.
    from app.store import store
    df, meta = store.get("202637")
    new = df.copy()
    new["snapshot_week"] = "202638"
    new.loc[new.index[:200], "planned_qty"] += 5
    store.put(new, {**meta, "snapshot_week": "202638"})
    r = client.post("/api/compare", params={"old_snapshot": "202637", "new_snapshot": "202638"}).json()
    assert r["metrics"]["matched_pairs"] == 1784 * 52
    assert {d["direction"] for d in r["directions"]} == {"increase", "unchanged"}
    assert len(r["histogram"]) == 30 and len(r["top_articles"]) <= 15
    assert len(r["scatter"]) == 2000 and r["scatter_sampled"] is True
