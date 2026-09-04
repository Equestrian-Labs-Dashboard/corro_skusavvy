# SKU Savvy Inventory Fix - September 2026

## Issue
Inventory dashboard showed approximately $4K instead of the expected ~$700K+.

## Root cause
Warehouse CSV exports changed format. Current August exports contain values already expressed in dollars (example: 130.38), while historical exports used scaled values (example: 130380).

The previous normalization divided all values by 1000, causing valid August inventory costs and retail values to be reduced.

## Fix
Updated the money normalization function to support both formats:
- Decimal dollar values remain unchanged.
- Historical scaled values are converted.

No dashboard tabs, warehouse filters, status logic, or existing calculations were modified.

## Validation
Compared July and August Warehouse exports:
- July requires scale normalization.
- August already contains dollar values.
- After normalization both periods reconcile in the expected inventory valuation range.
