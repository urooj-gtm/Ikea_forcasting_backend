"""SPI parser and leakage-safe forecast baseline primitives (vendored from the original Streamlit project core.py)."""
from __future__ import annotations
import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

META_COLUMNS = ["snapshot_week", "article", "name", "status", "rec_type", "rec_code", "target_week", "planned_qty", "sales_fc_52w", "supply_plan_52w", "dc_stock", "safety_stock", "in_transit", "open_orders", "sales_recent_4w"]


def number(s: str) -> float:
    try:
        return float(str(s).replace(",", "").strip()) if str(s).strip() else 0.0
    except (ValueError, TypeError):
        return 0.0


def read_spi(content: bytes, filename: str = "") -> tuple[pd.DataFrame, dict]:
    """Read IKEA tab-separated legacy .xls export; NOT an actual BIFF workbook."""
    if content[:2] == b"PK" or content[:8] == bytes.fromhex("d0cf11e0a1b11ae1"):
        raise ValueError("This app accepts IKEA's tab-delimited .xls SPI export, not binary Excel. Export as tab-delimited text first.")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:  # IKEA exports are Windows-1252 (e.g. Å, Ä, Ö in article names)
        decoded = content.decode("cp1252", errors="replace")
    rows = list(csv.reader(io.StringIO(decoded), delimiter="\t"))
    if len(rows) < 6:
        raise ValueError("SPI file is incomplete.")
    header = [c.strip() for c in rows[4]]
    if header[:4] != ["Art No.", "Art Name", "Art Status", "Rec Type"]:
        raise ValueError("Unrecognized SPI format. Expected 'Art No.' at row 5.")
    found = re.search(r"(?:20\d{4})", rows[2][0] if rows[2] else "")
    if not found:
        found = re.search(r"20\d{4}", filename)
    if not found:
        raise ValueError("Unable to locate SPI snapshot week in file metadata.")
    snapshot_week = found.group(0)
    weeks = [x.strip() for x in header[21:73]]
    if len(weeks) != 52 or not all(re.fullmatch(r"20\d{4}", v) for v in weeks):
        raise ValueError("Expected 52 YYYYWW supply columns from column 22.")
    out = []
    product_rows = 0
    summaries = 0
    status_counts: dict[str, int] = {}
    sum_supply = 0.0
    sum_sales = 0.0
    discrepancies = 0
    for row in rows[5:]:
        if len(row) < 73 or not row[0].strip():
            continue
        product_rows += 1
        rec_code = row[5].strip()
        if row[3].strip().lower() != "summary":
            continue
        summaries += 1
        status = row[2].strip()
        status_counts[status] = status_counts.get(status, 0) + 1
        qtys = [number(x) for x in row[21:73]]
        sum_supply += number(row[20]);sum_sales += number(row[19])
        if abs(sum(qtys) - number(row[20])) > 0.001:
            discrepancies += 1
        common = dict(snapshot_week=snapshot_week, article=row[0].strip(), name=row[1].strip(), status=status, rec_type=row[3].strip(), rec_code=rec_code, sales_fc_52w=number(row[19]), supply_plan_52w=number(row[20]), dc_stock=number(row[11]), safety_stock=number(row[12]), in_transit=number(row[13]), open_orders=number(row[14]), sales_recent_4w=sum(number(v) for v in row[15:19]))
        for w, q in zip(weeks, qtys):
            out.append({**common, "target_week": w, "planned_qty": q})
    if not summaries:
        raise ValueError("No 'Summary' product rows found.")
    df = pd.DataFrame(out, columns=META_COLUMNS)
    meta = {"snapshot_week": snapshot_week, "records": product_rows, "summary_rows": summaries, "status_counts": status_counts, "supply_total": sum_supply, "sales_total": sum_sales, "bucket_discrepancies": discrepancies, "target_weeks": weeks}
    return df, meta


def iso_week(week: str):
    return pd.to_datetime(f"{week}1", format="%G%V%u", errors="coerce")


def select_scope(df: pd.DataFrame, status: list[str], articles: list[str]) -> pd.DataFrame:
    x = df
    if status:
        x = x[x.status.isin(status)]
    if articles:
        x = x[x.article.isin(articles)]
    return x.copy()


def weekly_totals(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("target_week", as_index=False, sort=False)["planned_qty"].sum()
    grouped["date"] = grouped.target_week.apply(iso_week)
    return grouped.sort_values("date")


def next_snapshot_baseline(df: pd.DataFrame) -> pd.DataFrame:
    result = df[["snapshot_week", "article", "name", "status", "target_week", "planned_qty"]].copy()
    result["predicted_next_qty"] = result.planned_qty
    result["predicted_revision_units"] = 0.0
    result["predicted_revision_pct"] = 0.0
    return result


def compare_snapshots(old: pd.DataFrame, newer: pd.DataFrame) -> pd.DataFrame:
    """Compare SAME article and target delivery week only, not shifted columns."""
    old_snap = old.snapshot_week.iloc[0]
    newer_snap = newer.snapshot_week.iloc[0]
    if iso_week(newer_snap) <= iso_week(old_snap):
        raise ValueError("Second snapshot must be newer than first snapshot.")
    keys = ["article", "target_week"]
    a = old[keys + ["planned_qty", "name", "status"]].rename(columns={"planned_qty":"old_qty"})
    b = newer[keys + ["planned_qty"]].rename(columns={"planned_qty":"new_qty"})
    # No artificial zeros for disappeared articles or target weeks.
    merged = a.merge(b, on=keys, how="inner", validate="one_to_one")
    merged["revision_units"] = merged.new_qty - merged.old_qty
    merged["revision_pct"] = (merged.revision_units / merged.old_qty).where(merged.old_qty != 0)
    merged["direction"] = "unchanged"
    merged.loc[merged.revision_units > 0, "direction"] = "increase"
    merged.loc[merged.revision_units < 0, "direction"] = "decrease"
    merged["baseline_next_qty"] = merged.old_qty
    merged["baseline_revision_units"] = 0.0
    merged["absolute_error"] = merged.revision_units.abs()
    return merged


def baseline_metrics(comparison: pd.DataFrame) -> dict:
    if comparison.empty:
        return {}
    denom = comparison.new_qty.abs().sum()
    return {"matched_pairs": len(comparison), "MAE_units": float(comparison.absolute_error.mean()), "WAPE_pct": (float(comparison.absolute_error.sum() / denom * 100) if denom else None), "no_change_accuracy_pct": float((comparison.direction == "unchanged").mean() * 100), "net_revision_units": float(comparison.revision_units.sum())}


def prophet_scenario(weekly: pd.DataFrame, periods: int = 8) -> pd.DataFrame:
    """Illustrative extrapolation of one snapshot's future plan curve; NOT validated demand or revision forecast."""
    try:
        from prophet import Prophet
    except ImportError as exc:
        raise RuntimeError("Prophet is optional. Install it using `pip install prophet`.") from exc
    training = weekly[["date", "planned_qty"]].rename(columns={"date":"ds", "planned_qty":"y"}).dropna()
    if len(training) < 12:
        raise ValueError("Need at least 12 target weeks to show a Prophet scenario.")
    model = Prophet(weekly_seasonality=False, daily_seasonality=False, yearly_seasonality=False, interval_width=.8, changepoint_prior_scale=.05)
    model.fit(training)
    future = model.make_future_dataframe(periods=periods, freq="W-MON")
    p = model.predict(future)
    extra = p[p.ds > training.ds.max()][["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    for col in ["yhat", "yhat_lower", "yhat_upper"]:
        extra[col] = extra[col].clip(lower=0)
    return extra
