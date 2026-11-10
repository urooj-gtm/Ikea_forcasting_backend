"""Shared FastAPI dependencies."""
from __future__ import annotations
from typing import Annotated

import pandas as pd
from fastapi import Depends, HTTPException, Query

from .services.spi import select_scope
from .store import store


def snapshot_frame(snapshot: str | None = None) -> tuple[pd.DataFrame, dict]:
    if not store:
        raise HTTPException(404, "No snapshot loaded.")
    found = store.get(snapshot)
    if found is None:
        raise HTTPException(404, f"Snapshot {snapshot} not loaded.")
    return found


Snapshot = Annotated[tuple[pd.DataFrame, dict], Depends(snapshot_frame)]


def scoped_frame(snap: Snapshot, status: list[str] = Query(default=[]), article: list[str] = Query(default=[])) -> pd.DataFrame:
    """Snapshot rows filtered by ?status= and ?article= (both repeatable)."""
    return select_scope(snap[0], status, article)


Scoped = Annotated[pd.DataFrame, Depends(scoped_frame)]
