# Cavali Inventory tab — final UI behavior

This revision keeps Cavali separate from the physical Warehouse dimension.

- `Cavali — Total` was removed from the Warehouse dropdown.
- A dedicated `Cavali Inventory` tab was added to the main navigation.
- The Cavali Collective & Split cards are only visible while that tab is active.
- While the Cavali tab is active, the Warehouse selector is disabled because the Cavali scope combines multiple locations/stores.
- All top KPI cards recalculate from the Cavali SKU/location rows while the Cavali tab is active.
- Leaving the Cavali tab restores the normal warehouse-based dashboard and hides the Cavali cards.
- The normal inventory-scope filter keeps `Exclude Cavali`, so users can remove Cavali SKUs from the regular inventory view.
- Cavali is unavailable before August 2026; the tab is disabled for earlier months.
- No historical inventory is synthesized from the current snapshot.
