from fastapi import APIRouter, HTTPException, Query

from ..deps import Snapshot
from ..services.spi import next_snapshot_baseline, records, select_scope

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("")
def list_articles(snap: Snapshot, q: str = "", status: list[str] = Query(default=[]), limit: int = Query(100, ge=1, le=1000)):
    df = select_scope(snap[0], status, [])
    base = df.drop_duplicates("article")[["article", "name", "status", "supply_plan_52w", "sales_fc_52w", "dc_stock", "open_orders"]]
    base = base.sort_values("supply_plan_52w", ascending=False)
    if q:
        base = base[base.article.str.contains(q, case=False, regex=False) | base.name.str.contains(q, case=False, regex=False)]
    return records(base.head(limit))


@router.get("/{article}")
def article_detail(article: str, snap: Snapshot):
    df = select_scope(snap[0], [], [article])
    if df.empty:
        raise HTTPException(404, "Article not found.")
    forecast = next_snapshot_baseline(df).sort_values("target_week")
    d = df.iloc[0]
    return {"article": article, "name": d["name"], "status": d.status,
            "supply_plan_52w": float(d.supply_plan_52w), "sales_fc_52w": float(d.sales_fc_52w),
            "stock": {"dc_stock": float(d.dc_stock), "safety_stock": float(d.safety_stock),
                      "in_transit": float(d.in_transit), "open_orders": float(d.open_orders)},
            "schedule": records(forecast[["target_week", "planned_qty", "predicted_next_qty"]])}
