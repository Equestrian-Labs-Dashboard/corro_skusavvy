# Cavali filter update — 2026-08-20

This additive change integrates Cavali into the main Inventory Intelligence filters without changing the existing SKUSavvy source rows.

## Inventory scope filter

The previous Legacy inventory selector is now one unified inventory selector:

- All inventory
- Cavali only
- Exclude Cavali
- Legacy only
- Exclude legacy

`Cavali only` is available from August 2026 onward. Selecting it temporarily changes the Warehouse selector to `Cavali — all included locations` because the Cavali scope spans Cavali Club HQ, Kensington via Shopify Collective, New Wellington Warehouse, and Corro Trailer 1.

## KPI behavior

When Cavali is selected, the main KPI strip recalculates from the current Cavali inventory rows. A new `Inventory Units` KPI was added so the user can see unit quantity directly, alongside Active Products, Inventory Value, Retail Value, Gross Margin and the other existing KPIs.

Collective rows come from Cavali Shopify using product tags `Shopify Collective` / `ALL COLLECTIVE` and the two real locations. Split rows come from Corro Shopify using `CAVALI INVENTORY SPLIT` at New Wellington Warehouse and Corro Trailer 1.

Retail price is read from the Cavali Shopify variant. Inventory Value / Gross Margin use the existing SKUSavvy AvgCost matched by SKU, preserving SKUSavvy as the established cost source for this dashboard. No quantity/value constants are hardcoded.

The existing Cavali four-card snapshot section remains unchanged.
