from fastapi import APIRouter, Query

from ..deps import Scoped, Snapshot
from ..services.aggregation import aggregate
from ..services.spi import records

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview")
def overview(snap: Snapshot, scope: Scoped):
    _, meta = snap
    per_article = scope.drop_duplicates("article")
    sales = per_article.sales_fc_52w.sum()
    return {
        "snapshot_week": meta["snapshot_week"],
        "articles": int(scope.article.nunique()),
        "planned_total": float(scope.planned_qty.sum()),
        "sales_forecast_total": float(sales),
        "status_counts": meta["status_counts"],
        "supply_to_sales": float(scope.planned_qty.sum() / sales) if sales else None,
        "summary_rows": meta["summary_rows"],
        "records": meta["records"],
        "bucket_discrepancies": meta["bucket_discrepancies"],
    }


@router.get("/weekly")
def weekly(scope: Scoped, granularity: str = Query("week", pattern="^(week|month|year)$")):
    return records(aggregate(scope, granularity))
