"""Aggregates behind the overview charts (ported from the Streamlit dashboard)."""
from fastapi import APIRouter, Query

from ..deps import Scoped
from ..services.spi import records

router = APIRouter(prefix="/api/insights", tags=["insights"])


def _per_article(scope):
    return scope.drop_duplicates("article")


@router.get("/lifecycle")
def lifecycle(scope: Scoped):
    c = _per_article(scope).groupby("status").size().reset_index(name="articles")
    return records(c)


@router.get("/top-articles")
def top_articles(scope: Scoped, n: int = Query(15, ge=1, le=100)):
    top = _per_article(scope).nlargest(n, "supply_plan_52w")[["article", "name", "status", "supply_plan_52w"]]
    return records(top)


@router.get("/balance")
def balance(scope: Scoped):
    """One point per article: 52-week sales forecast vs planned supply, sized by DC stock."""
    d = _per_article(scope)[["article", "name", "status", "sales_fc_52w", "supply_plan_52w", "dc_stock"]].copy()
    d["ratio"] = d.supply_plan_52w.div(d.sales_fc_52w.where(d.sales_fc_52w.ne(0)))
    return records(d)


@router.get("/exposure")
def exposure(scope: Scoped):
    e = _per_article(scope).groupby("status", as_index=False).agg(
        dc_stock=("dc_stock", "sum"), safety_stock=("safety_stock", "sum"),
        in_transit=("in_transit", "sum"), open_orders=("open_orders", "sum"))
    return records(e)
