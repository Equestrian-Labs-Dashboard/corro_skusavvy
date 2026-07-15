# SKU / SKUSavvy Dashboard Fix

Files to replace in GitHub:

1. `index.html`
2. `scripts/generate_data.py`

What this fixes:

- KPIs now update when filters are applied, including Rotation +90 days.
- Added Legacy filter.
- Added Category/Product Type filter.
- Search now checks product name, SKU, SKU list, variant/option fields, vendor, category, tags, and child SKUs.
- `generate_data.py` now preserves tags from SKUSavvy/CSV/API when available so the Legacy filter can work.

Important:

- If the Legacy tag is not present in SKUSavvy CSV/API data, the Legacy filter cannot calculate the expected ~$154k COGS until tags are included in the export/API payload.
- Category filter uses `productType` / category from the SKUSavvy CSV or Shopify/SKUSavvy product type.
