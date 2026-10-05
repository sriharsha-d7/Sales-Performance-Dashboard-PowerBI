# Measures and calculated columns

Generated from the model by `scripts/build_docs.py`, so the DAX below is what is in the report.

## Measures

| Measure | DAX | Meaning |
|---|---|---|
| `Total Sales` | `SUM(shipments[Sales])` | Revenue: sum of the Sales column. |
| `Total Sales (Prev Month)` | `CALCULATE([Total Sales], PREVIOUSMONTH(calender[Date]))` | Total Sales shifted to the previous calendar month (needs the date table). |
| `MoM Sales Change %` | `var this_month = [Total Sales] var prev_month = [Total Sales (Prev Month)] return DIVIDE(this_month-prev_month, prev_month)` | Month-over-month sales growth; blank when there is no prior month. |
| `Total Boxes` | `SUM(shipments[Boxes])` | Units shipped. |
| `Total Costs` | `SUM(shipments[Costs])` | Cost of goods: boxes x the product's cost per box (computed per shipment row). |
| `Total Shipments` | `COUNT(shipments[Boxes])` | Number of shipment rows. |
| `Total Profit` | `[Total Sales]-[Total Costs]` | Sales minus costs. |
| `Profit %` | `DIVIDE([Total Profit], [Total Sales])` | Profit margin on sales. |
| `LBS Count` | `CALCULATE([Total Shipments],shipments[Boxes]<50)` | Shipments under 50 boxes ("low box shipments"). |
| `LBS %` | `DIVIDE([LBS Count],[Total Shipments])` | Share of shipments that are low-box. |
| `Profit Target` | `0.6` | Margin target (60%) used by the indicator below. |
| `Profit Target Indicator` | `IF([Profit %]>[Profit Target],2 ,IF([Profit %]>0.9*[Profit Target],1,0))` | 2 = above target, 1 = within 10% of target (>= 54%), 0 = below that. |

## Calculated columns

| Table | Column | DAX |
|---|---|---|
| shipments | `Costs` | `RELATED(products[Cost per box])*shipments[Boxes]` |
| shipments | `Boxes (bins)` | `IF( ISBLANK('shipments'[Boxes]), BLANK(), INT('shipments'[Boxes] / 20) * 20 )` |

## Calculated table

`Measure Selector` drives the field-parameter slicer on the dashboard page (Sales, Boxes, Shipments, Costs, Profit):

```dax
{
    ("Sales", NAMEOF('Measure'[Total Sales]), 0),
    ("Boxes", NAMEOF('Measure'[Total Boxes]), 1),
    ("Shipments", NAMEOF('Measure'[Total Shipments]), 2),
    ("Costs", NAMEOF('Measure'[Total Costs]), 3),
    ("Profit", NAMEOF('Measure'[Total Profit]), 4)
}
```
