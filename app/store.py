"""In-memory snapshot store. Replace with a database once history is archived."""
from __future__ import annotations
from threading import Lock

import pandas as pd


class SnapshotStore:
    def __init__(self) -> None:
        self._data: dict[str, tuple[pd.DataFrame, dict]] = {}
        self._lock = Lock()

    def put(self, df: pd.DataFrame, meta: dict) -> None:
        with self._lock:
            self._data[meta["snapshot_week"]] = (df, meta)

    def get(self, week: str | None) -> tuple[pd.DataFrame, dict] | None:
        """Return the requested week, or the latest when week is None."""
        with self._lock:
            if not self._data:
                return None
            return self._data.get(week or max(self._data))

    def weeks(self) -> list[str]:
        with self._lock:
            return sorted(self._data)

    def metas(self) -> list[dict]:
        with self._lock:
            return [self._data[w][1] for w in sorted(self._data)]

    def __bool__(self) -> bool:
        return bool(self._data)


store = SnapshotStore()
