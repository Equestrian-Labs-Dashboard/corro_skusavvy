# Cavali — Final warehouse behavior

This version fixes the runtime error `cavaliScopeActive is not defined` and implements Cavali as a special Warehouse option.

## Normal warehouses
- Wellington Warehouse
- Corro Trailer 1
- Drop Ship
- All Warehouses

All existing report tabs remain enabled and work normally.

## Cavali — Total
Available only from August 2026 onward.

When `Cavali — Total` is selected in Warehouse:
- the dashboard automatically switches to Cavali Inventory;
- all top KPI cards recalculate from Cavali filter rows;
- the Collective & Split snapshot cards are shown;
- all other report tabs are disabled to prevent mixing Cavali scope with regular warehouse analyses;
- Warehouse remains enabled so the user can leave Cavali mode by choosing another warehouse.

When another Warehouse is selected:
- Cavali cards are hidden;
- the dashboard returns to Inventory Rotation;
- all report tabs are re-enabled;
- normal warehouse calculations resume.

The regular Inventory filter still includes Exclude Cavali for removing Cavali SKUs from the standard inventory view.
