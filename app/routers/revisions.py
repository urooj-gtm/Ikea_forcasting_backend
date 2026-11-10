import numpy as np
from fastapi import APIRouter, HTTPException, Query

from ..services.spi import baseline_metrics, compare_snapshots, records, select_scope
from ..store import store

router = APIRouter(prefix="/api", tags=["revisions"])

SCATTER_MAX = 2000
HIST_BINS = 30


@router.post("/compare")
def compare(old_snapshot: str, new_snapshot: str, status: list[str] = Query(default=[])):
    old, new = store.get(old_snapshot), store.get(new_snapshot)
    if old is None or new is None:
        raise HTTPException(404, "Both snapshots must be loaded.")
    try:
        cmp = compare_snapshots(select_scope(old[0], status, []), select_scope(new[0], status, []))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if cmp.empty:
        return {"metrics": {}, "directions": [], "top_articles": [], "scatter": [], "histogram": [], "top_revisions": []}

    directions = cmp.direction.value_counts().rename_axis("direction").reset_index(name="count")
    by_article = (cmp.groupby("article", as_index=False)
                  .agg(abs_revision=("revision_units", lambda x: x.abs().sum()), name=("name", "first"))
                  .nlargest(15, "abs_revision"))
    counts, edges = np.histogram(cmp.revision_units, bins=HIST_BINS)
    histogram = [{"start": float(edges[i]), "end": float(edges[i + 1]), "count": int(counts[i])} for i in range(len(counts))]
    scatter = cmp if len(cmp) <= SCATTER_MAX else cmp.sample(SCATTER_MAX, random_state=0)
    top = cmp.reindex(cmp.revision_units.abs().sort_values(ascending=False).index).head(50)
    return {
        "metrics": baseline_metrics(cmp),
        "directions": records(directions),
        "top_articles": records(by_article),
        "scatter": records(scatter[["article", "target_week", "old_qty", "new_qty", "direction", "revision_units"]]),
        "scatter_sampled": len(cmp) > SCATTER_MAX,
        "histogram": histogram,
        "top_revisions": records(top),
    }
