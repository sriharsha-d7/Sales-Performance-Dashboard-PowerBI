"""Integrity checks on the .pbix itself: the model, its DAX, and independent recomputation of its KPIs."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pbix_model as pm  # noqa: E402


@pytest.fixture(scope="module")
def m():
    return pm.load()


@pytest.fixture(scope="module")
def t(m):
    return pm.tables(m)


@pytest.fixture(scope="module")
def s(t):
    return pm.enriched(t)


def test_star_schema_relationships(m):
    rel = m.relationships
    assert set(rel["FromTableName"]) == {"shipments"}
    assert set(rel["ToTableName"]) == {"people", "products", "calender", "locations"}
    assert (rel["Cardinality"] == "M:1").all() and (rel["IsActive"] == 1).all()


def test_no_orphan_keys_and_unique_dimension_keys(t):
    sh = t["shipments"]
    assert sh["Sales Person"].isin(t["people"]["Sales person"]).all()
    assert sh["Product"].isin(t["products"]["Product"]).all()
    assert sh["Geography"].isin(t["locations"]["Geo"]).all()
    assert sh["Date"].isin(t["calender"]["Date"]).all()
    assert t["people"]["Sales person"].is_unique and t["products"]["Product"].is_unique and t["locations"]["Geo"].is_unique


def test_costs_column_equals_boxes_times_cost_per_box(s):
    assert (s["Costs"] - s["Boxes"] * s["Cost per box"]).abs().max() < 1e-6


def test_dax_for_core_measures_has_not_drifted(m):
    dax = {r["Name"]: " ".join(str(r["Expression"]).split()) for _, r in m.dax_measures.iterrows()}
    assert dax["Total Sales"] == "SUM(shipments[Sales])"
    assert dax["Total Profit"] == "[Total Sales]-[Total Costs]"
    assert dax["LBS Count"] == "CALCULATE([Total Shipments],shipments[Boxes]<50)"
    assert dax["Profit Target"] == "0.6"
    assert len(dax) == 12


def test_kpis_recomputed_independently(s):
    k = pm.kpis(s)
    assert k["Total Sales"] == pytest.approx(34042511.25)
    assert k["Total Costs"] == pytest.approx(13518440.91, abs=0.01)
    assert k["Total Profit"] == pytest.approx(k["Total Sales"] - k["Total Costs"])
    assert k["Profit %"] == pytest.approx(0.6029, abs=1e-4)
    assert k["Total Shipments"] == 6113 and k["Total Boxes"] == 2077844
    assert k["LBS %"] == pytest.approx(0.1021, abs=1e-4)


def test_indicator_buckets_and_mom_blank_first_month(s):
    pp = pm.by_person(s)
    assert pp["indicator"].value_counts().to_dict() == {2: 14, 1: 8, 0: 3}
    mo = pm.monthly(s)
    assert mo["mom_change"].isna().iloc[0] and mo["mom_change"].notna().iloc[1:].all()
