# Cavali filter correction — Ceci feedback

This revision keeps the existing Cavali Inventory cards and makes Cavali a real dashboard filter.

## Warehouse filter
From August 2026 onward the top Warehouse dropdown includes:
- Cavali — Total (all included locations)

Selecting it switches the inventory scope to Cavali and recalculates the top KPI strip.

## Inventory group filter
The lower inventory group dropdown includes:
- All inventory
- Cavali
- Exclude Cavali
- Legacy only
- Exclude legacy

Exclude Cavali removes SKUs contained in the current Cavali Shopify dataset, with product tags as a secondary check.

## Cavali KPI behavior
When Cavali is active, the top KPIs use the Cavali filter dataset and a visible summary confirms:
- Inventory Units
- Inventory Value
- Retail Value
- Gross Margin

The current report scope is Collective inventory plus the Corro-side Split inventory included by the approved requirements. The note that Corro-side Split is not the whole company Split total remains intact.
