# Cavali Inventory — Collective & Split

This section is isolated from the existing SKUSavvy dashboard logic and starts on 2026-08-01.

## GitHub Secrets

The existing Corro Shopify connection continues to use:
- `SHOPIFY_STORE_DOMAIN`
- `SHOPIFY_ADMIN_ACCESS_TOKEN`

Add the Cavali Shopify connection as:
- `CAVALI_SHOPIFY_STORE_DOMAIN`
- `CAVALI_SHOPIFY_ADMIN_ACCESS_TOKEN`

The Shopify custom app/token used for each store must be able to read products, inventory, and locations.

## Daily snapshot

The workflow `.github/workflows/update-dashboard.yml` runs daily and writes `data/cavali_inventory_snapshots.csv`.

A successful day contains these metrics:
- `Collective Inventory`
- `Split Inventory — Wellington WH`
- `Split Inventory — Corro Trailer`
- `Split Inventory — Corro Side Total`

A rerun on the same day replaces the metrics successfully fetched for that day and does not duplicate them. Older days are preserved.

## Source rules

Collective:
- Store: Cavali Shopify
- Product tags: `Shopify Collective` OR `ALL COLLECTIVE`
- Locations: `Cavali Club HQ` and `Kensington via Shopify Collective`

Split:
- Store: Corro Shopify
- Product tag: `CAVALI INVENTORY SPLIT`
- Locations: `New Wellington Warehouse` and `Corro Trailer 1`

Inventory is read from Shopify inventory items / inventory levels and `available` quantity by location. No Sidekick or Excel quantity is hardcoded.

## Date behavior

- Before August 2026: the section is hidden and no Cavali snapshot is created.
- August 2026 onward: the section is available.
- A selected month only uses snapshots saved inside that month.
- Current inventory is never reused as historical inventory for a month with no snapshot.
- `All dates` shows the latest saved daily snapshot and labels it as such.

## Validation references only

The previously observed 45 products / 163 variants / 10,488 Collective units and approximately 950 Wellington / 189 Trailer units are reference values only. The implementation recalculates the live values from Shopify on each workflow run.
