# Cavali Inventory — final value integration

This revision connects the Cavali Shopify inventory scope to the same Inventory Intelligence KPI model used by the dashboard.

When Warehouse = `Cavali — Total`:
- Cavali Inventory tab is activated.
- Other report tabs are locked until another warehouse is selected.
- KPI cards are recalculated from Cavali rows only.
- The Cavali section displays total Inventory Units, Inventory Value, Retail Value and Gross Margin.
- Each Collective/Split card also displays Inventory Value, Retail Value and Gross Margin.
- The detail table shows Product, SKU, Vendor, Location, Total Stock, Avg Unit Cost, Inventory Value, Retail Value, Coverage, Rotation and Status.

Cost priority:
1. Existing SKUSavvy AvgCost matched by SKU.
2. Shopify InventoryItem.unitCost fallback.
3. If neither exists, cost is not invented and the UI warns about missing cost.

Retail value uses Shopify variant price × available inventory at the allowed Cavali locations.

Cavali remains available only from August 2026 onward and snapshots are not backfilled from current inventory.
