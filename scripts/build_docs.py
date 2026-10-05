"""Regenerate docs/measures.md, docs/data_model.md and docs/kpi_overview.png from the .pbix itself."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pbix_model as pm  # noqa: E402

DOCS = Path(__file__).resolve().parents[1] / "docs"
EXPLAIN = {
    "Total Sales": "Revenue: sum of the Sales column.",
    "Total Sales (Prev Month)": "Total Sales shifted to the previous calendar month (needs the date table).",
    "MoM Sales Change %": "Month-over-month sales growth; blank when there is no prior month.",
    "Total Boxes": "Units shipped.",
    "Total Costs": "Cost of goods: boxes x the product's cost per box (computed per shipment row).",
    "Total Shipments": "Number of shipment rows.",
    "Total Profit": "Sales minus costs.",
    "Profit %": "Profit margin on sales.",
    "LBS Count": "Shipments under 50 boxes (\"low box shipments\").",
    "LBS %": "Share of shipments that are low-box.",
    "Profit Target": "Margin target (60%) used by the indicator below.",
    "Profit Target Indicator": "2 = above target, 1 = within 10% of target (>= 54%), 0 = below that.",
}


def measures_md(m) -> str:
    rows = ["# Measures and calculated columns", "",
            "Generated from the model by `scripts/build_docs.py`, so the DAX below is what is in the report.", "",
            "## Measures", "", "| Measure | DAX | Meaning |", "|---|---|---|"]
    for _, r in m.dax_measures.iterrows():
        dax = " ".join(str(r["Expression"]).split()).replace("|", "\\|")
        rows.append(f"| `{r['Name']}` | `{dax}` | {EXPLAIN.get(r['Name'], '')} |")
    rows += ["", "## Calculated columns", "", "| Table | Column | DAX |", "|---|---|---|"]
    for _, r in m.dax_columns.iterrows():
        rows.append(f"| {r['TableName']} | `{r['ColumnName']}` | `{' '.join(str(r['Expression']).split())}` |")
    rows += ["", "## Calculated table", "", "`Measure Selector` drives the field-parameter slicer on the dashboard page "
             "(Sales, Boxes, Shipments, Costs, Profit):", "", "```dax"]
    rows += [str(m.dax_tables.iloc[0]["Expression"]).strip(), "```", ""]
    return "\n".join(rows)


def model_md(m, t, s) -> str:
    rel = m.relationships
    er = ["```mermaid", "erDiagram"]
    for _, r in rel.iterrows():
        er.append(f"    {r['FromTableName']} }}o--|| {r['ToTableName']} : \"{r['FromColumnName']} to {r['ToColumnName']}\"")
    er.append("```")
    out = ["# Data model", "", "Star schema: one fact table (`shipments`) and four dimensions, all many-to-one with single-direction filtering.", ""]
    out += er + ["", "| Table | Rows | Role |", "|---|---|---|"]
    roles = {"shipments": "fact: one row per shipment", "products": "dimension: product, category, cost per box",
             "people": "dimension: salesperson and team", "locations": "dimension: country and region",
             "calender": "date dimension (the table name is misspelled in the model)"}
    for n, d in t.items():
        out.append(f"| `{n}` | {len(d):,} | {roles[n]} |")
    out += ["", f"Shipments span **{s['Date'].min():%Y-%m-%d} to {s['Date'].max():%Y-%m-%d}**.", "",
            "## Source and refresh", "",
            "All tables are loaded by Power Query from one Excel workbook, `ac-sample-data.xlsx`, through a hard-coded path on the "
            "author's machine (`C:\\Users\\...\\Downloads\\...`). Refresh therefore fails anywhere else until the source is re-pointed "
            "(Transform data > Data source settings); the workbook is not included in this repository. The pictures in `people` link to "
            "`files.chandoo.org`, which indicates the data is Chandoo.org's public Power BI tutorial data set.", ""]
    return "\n".join(out)


def figure(s: pd.DataFrame) -> None:
    SURF, INK, MUTED, GRID, BLUE, ORANGE, NEUTRAL = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1", "#2a78d6", "#eb6834", "#9a9992"
    mo, pp = pm.monthly(s), pm.by_person(s)
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 5.2), gridspec_kw={"width_ratios": [1, 1.1]})
    fig.set_facecolor(SURF)
    x = mo.index.to_timestamp()
    a.plot(x, mo["sales"] / 1e6, color=BLUE, lw=2, marker="o", ms=5)
    a.set_ylim(2.0, 3.2)
    a.set_title("Monthly sales ($M)", loc="left", fontsize=11, fontweight="bold", color=INK)
    for xi, yi, mom in zip(x, mo["sales"] / 1e6, mo["mom_change"]):
        if pd.notna(mom) and abs(mom) > 0.15:
            a.annotate(f"{mom:+.0%}", (xi, yi), textcoords="offset points", xytext=(0, 9 if mom > 0 else -15), ha="center", fontsize=8, color=INK)
    col = {2: BLUE, 1: NEUTRAL, 0: ORANGE}
    b.hlines(pp.index, pm.PROFIT_TARGET * 100, pp["profit_pct"] * 100, color=GRID, lw=2, zorder=1)  # dot plot: no zero baseline needed
    b.scatter(pp["profit_pct"] * 100, pp.index, c=[col[i] for i in pp["indicator"]], s=46, zorder=3)
    b.axvline(pm.PROFIT_TARGET * 100, color=INK, lw=1, ls="--")
    b.set_xlim(52, 68)
    b.set_title("Profit % by salesperson vs 60% target", loc="left", fontsize=11, fontweight="bold", color=INK)
    b.tick_params(axis="y", labelsize=7)
    from matplotlib.patches import Patch
    b.legend(handles=[Patch(color=BLUE, label="Above target (2)"), Patch(color=NEUTRAL, label="Within 10% (1)"),
                      Patch(color=ORANGE, label="Below (0)")], frameon=False, fontsize=8, loc="lower right", labelcolor=MUTED)
    for ax in (a, b):
        ax.set_facecolor(SURF)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.grid(axis="y" if ax is a else "x", color=GRID, lw=0.8)  # noqa
        ax.set_axisbelow(True)
    fig.text(0.01, 0.005, "Regenerated from the data model with pandas (not a screenshot of the report).", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(DOCS / "kpi_overview.png", dpi=150)


def main() -> None:
    m = pm.load()
    t = pm.tables(m)
    s = pm.enriched(t)
    DOCS.mkdir(exist_ok=True)
    (DOCS / "measures.md").write_text(measures_md(m))
    (DOCS / "data_model.md").write_text(model_md(m, t, s))
    figure(s)
    print("docs regenerated")


if __name__ == "__main__":
    main()
