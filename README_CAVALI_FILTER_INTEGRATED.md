# Cavali integrated warehouse filter

Cavali is integrated into the existing SKUSavvy inventory dashboard; it is not a separate tab or permanent section.

From August 2026 onward the Warehouse selector contains a Cavali / Shopify group with:
- Cavali — All tracked locations
- Cavali — Cavali Club HQ
- Cavali — Kensington via Shopify Collective
- Cavali Split — Wellington WH
- Cavali Split — Corro Trailer

Selecting a Cavali option recalculates the existing KPI cards and the existing product table with Cavali Shopify inventory. The regular Corro / SKUSavvy warehouse options remain unchanged.

Cavali costs use matching SKUSavvy AvgCost when available, otherwise Shopify InventoryItem.unitCost. Retail Value uses Shopify variant price. Sales/turnover for Collective use Cavali Shopify orders; Split uses Corro Shopify sales.

Expiring Inventory and Damaged are disabled while Cavali is selected because the current Shopify extraction does not provide lot-expiration/damage records.

Daily SKU/location snapshots are stored in data/cavali_inventory_detail_snapshots.csv. A rerun on the same day replaces only that day's Cavali detail rows and preserves prior days.
