"""Weekly -> monthly/yearly aggregation of planned supply.

PROVISIONAL: periods are assigned by each ISO week's Monday date until planning
approves the calendar/allocation rule (Jira IF-6).
"""
from __future__ import annotations

import pandas as pd

from .spi import weekly_totals

FULL_WEEKS = {"month": 4, "year": 52}  # minimum weeks for a period to count as complete


def aggregate(scope: pd.DataFrame, granularity: str) -> pd.DataFrame:
    w = weekly_totals(scope)
    if granularity == "week":
        w["period"] = w.target_week
        return w.groupby("period", as_index=False, sort=False).agg(planned_qty=("planned_qty", "sum"), weeks=("target_week", "nunique"))
    fmt = "%Y-%m" if granularity == "month" else "%Y"
    w["period"] = w.date.dt.strftime(fmt)
    out = w.groupby("period", as_index=False, sort=True).agg(planned_qty=("planned_qty", "sum"), weeks=("target_week", "nunique"))
    out["partial"] = out.weeks < FULL_WEEKS[granularity]
    return out
