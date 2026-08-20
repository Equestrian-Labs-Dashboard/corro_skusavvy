# Cavali filter — Ceci final correction

This version keeps the Cavali Inventory section and adds Cavali as a real dashboard scope.

## Warehouse selector
From August 2026 onward the Warehouse selector contains:
- Wellington Warehouse
- Corro Trailer 1
- Drop Ship
- Cavali — Total
- All Warehouses

Choosing `Cavali — Total` automatically activates `Cavali only` in the inventory scope filter and recalculates the KPI strip.

## Inventory scope selector
- All inventory
- Cavali only
- Exclude Cavali
- Legacy only
- Exclude legacy

`Cavali only` recalculates Active Products, Inventory Units, Stockout Risk, Slow Movers, Inventory Turnover, Inventory Value, Retail Value and Gross Margin using Cavali rows only.

`Exclude Cavali` removes Cavali SKUs from the normal SKUSavvy inventory rows.

## Cavali scope
The current Cavali filter contains:
- Collective inventory from Cavali Shopify at Cavali Club HQ + Kensington via Shopify Collective.
- Split inventory from Corro Shopify at New Wellington Warehouse + Corro Trailer 1.

It does not claim that Wellington + Trailer is the entire company-wide Split inventory.

## Cost safety
Inventory Value uses matched SKUSavvy AvgCost by SKU. If a Cavali SKU has no matched cost, the dashboard does not invent a cost and shows a warning while excluding that unknown cost from Inventory Value / Gross Margin.

## Date rule
Cavali is available from August 2026 onward only.
