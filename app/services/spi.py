"""Single adapter onto the SPI parsing / baseline logic (spi_core.py)."""
from __future__ import annotations

import pandas as pd

from .spi_core import (baseline_metrics, compare_snapshots, next_snapshot_baseline,
                       prophet_scenario, read_spi, select_scope, weekly_totals)

__all__ = ["baseline_metrics", "compare_snapshots", "next_snapshot_baseline", "prophet_scenario",
           "read_spi", "select_scope", "weekly_totals", "records", "public_meta"]


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe list of dicts (NaN -> None)."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


def public_meta(meta: dict) -> dict:
    return {k: v for k, v in meta.items() if k != "target_weeks"}
