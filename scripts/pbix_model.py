"""Read the Power BI model (tables, DAX, relationships) and recompute its KPIs independently in pandas."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from pbixray import PBIXRay

PBIX = Path(__file__).resolve().parents[1] / "report" / "sales_report.pbix"
PROFIT_TARGET = 0.6  # the model's [Profit Target] measure


def load(path: Path = PBIX) -> PBIXRay:
    return PBIXRay(str(path))


def tables(m: PBIXRay) -> dict[str, pd.DataFrame]:
    return {n: m.get_table(n) for n in ("shipments", "products", "people", "locations", "calender")}


def enriched(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """shipments joined to its dimensions (same joins as the model's relationships)."""
    s = t["shipments"].copy()
    s["Sales"] = s["Sales"].astype(float)
    s["Costs"] = s["Costs"].astype(float)
    s["Boxes"] = s["Boxes"].astype("int64")
    s = s.merge(t["products"], on="Product", validate="m:1")
    s = s.merge(t["people"], left_on="Sales Person", right_on="Sales person", validate="m:1")
    s = s.merge(t["locations"], left_on="Geography", right_on="Geo", validate="m:1")
    s["Profit"] = s["Sales"] - s["Costs"]
    return s


def kpis(s: pd.DataFrame) -> dict[str, float]:
    """Python equivalents of the model's measures over the whole data set."""
    sales, costs = s["Sales"].sum(), s["Costs"].sum()
    return {
        "Total Sales": sales, "Total Boxes": int(s["Boxes"].sum()), "Total Shipments": int(s["Boxes"].count()),
        "Total Costs": costs, "Total Profit": sales - costs, "Profit %": (sales - costs) / sales,
        "LBS Count": int((s["Boxes"] < 50).sum()), "LBS %": float((s["Boxes"] < 50).mean()),
    }


def monthly(s: pd.DataFrame) -> pd.DataFrame:
    mo = s.groupby(s["Date"].dt.to_period("M")).agg(sales=("Sales", "sum"), profit=("Profit", "sum"))
    mo["mom_change"] = mo["sales"].pct_change()  # DAX: DIVIDE(this - prev, prev), blank for the first month
    mo["profit_pct"] = mo["profit"] / mo["sales"]
    return mo


def by_person(s: pd.DataFrame) -> pd.DataFrame:
    g = s.groupby("Sales Person").agg(sales=("Sales", "sum"), profit=("Profit", "sum"), shipments=("Sales", "size"))
    g["profit_pct"] = g["profit"] / g["sales"]
    # DAX: IF(p > target, 2, IF(p > 0.9 * target, 1, 0))
    g["indicator"] = g["profit_pct"].apply(lambda p: 2 if p > PROFIT_TARGET else (1 if p > 0.9 * PROFIT_TARGET else 0))
    return g.sort_values("profit_pct")
