from fastapi import APIRouter, HTTPException, Query

from ..deps import Scoped
from ..services.spi import prophet_scenario, records, weekly_totals

router = APIRouter(prefix="/api", tags=["scenario"])


@router.get("/prophet")
def prophet(scope: Scoped, periods: int = Query(8, ge=1, le=26)):
    weekly = weekly_totals(scope)
    try:
        extra = prophet_scenario(weekly, periods)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    extra["ds"] = extra.ds.dt.strftime("%Y-%m-%d")
    history = weekly.assign(ds=weekly.date.dt.strftime("%Y-%m-%d"))[["ds", "planned_qty"]]
    return {"disclaimer": "Unvalidated planning scenario, not a demand or revision forecast.",
            "history": records(history), "points": records(extra)}
