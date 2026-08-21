# Cavali / Corro source-switch correction

This version fixes the dashboard source switching logic.

## Corro
- Existing SKUSavvy dataset remains the source.
- Existing warehouse/status/category/search filters continue unchanged.

## Cavali
- Cavali warehouse options use Shopify-derived detail rows only.
- No SKUSavvy/Corro rows are used as fallback if Cavali Shopify data is missing.
- KPI cards are recalculated from the same filtered Cavali rows shown in the table.
- Inventory Value = Shopify inventoryItem.unitCost * available inventory units.
- Retail Value = Shopify variant price * available inventory units.
- Gross Margin is calculated from those two values.
- Rotation / slow-mover metrics use Shopify sales-by-SKU for the selected period.
- Product status is fetched from Shopify and powers the Status filter.
- Expiring and Damaged remain unavailable for Cavali because those fields are not provided by this Shopify feed.

## Date rule
Cavali options remain available only from August 2026 onward. Daily detail snapshots continue to be upserted by date without deleting prior days.
