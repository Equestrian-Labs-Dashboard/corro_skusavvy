#!/usr/bin/env python3
"""
Generate static dashboard data for GitHub Pages.
- Reads SKUSAVVY_TOKEN from GitHub Actions secrets / environment.
- Writes data/dashboard.json and data/schema-debug.json.
- Does not print or save the token.
"""
from __future__ import annotations

import json
import os
import csv
import glob
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, date, timedelta
from typing import Any, Dict, List, Tuple

GRAPHQL_URL = os.getenv("SKUSAVVY_GRAPHQL", "https://app.skusavvy.com/graphql")
TOKEN = os.getenv("SKUSAVVY_TOKEN", "").strip()
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "100"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "250"))
PAGE_DELAY_SECONDS = float(os.getenv("PAGE_DELAY_SECONDS", "1.2"))
DEFAULT_WAREHOUSE_ID = "019b6b44-4eea-7613-9f82-9af97d2d255d"
SHOPIFY_STORE_DOMAIN = os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_ADMIN_ACCESS_TOKEN = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "").strip()
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-01").strip()
SHOPIFY_MONTHS_BACK = int(os.getenv("SHOPIFY_MONTHS_BACK", "18"))

KNOWN_WAREHOUSES = [
    {"id": DEFAULT_WAREHOUSE_ID, "name": "Wellington Warehouse", "location": "Wellington, FL"},
    {"id": "019b6b44-4eba-72db-9c86-a971207c9559", "name": "Drop Ship", "location": "Wellington, FL"},
    {"id": "019e03cc-afca-721a-a553-1946248e9883", "name": "Corro Trailer 1", "location": "Saugerties, NY"},
]

WAREHOUSE_NAME_TO_ID = {
    "wellington warehouse": DEFAULT_WAREHOUSE_ID,
    "wellington": DEFAULT_WAREHOUSE_ID,
    "drop ship": "019b6b44-4eba-72db-9c86-a971207c9559",
    "dropship": "019b6b44-4eba-72db-9c86-a971207c9559",
    "drop_ship": "019b6b44-4eba-72db-9c86-a971207c9559",
    "corro trailer 1": "019e03cc-afca-721a-a553-1946248e9883",
    "corro_trailer_1": "019e03cc-afca-721a-a553-1946248e9883",
}

CSV_PRODUCT_DETAILS: Dict[str, Dict[str, Any]] = {}

VARIANTS_QUERY = """
query DashboardVariants($limit: Int, $offset: Int) {
  variants(limit: $limit, offset: $offset) {
    id
    sku
    price
    averageSales
    totalQuantity
    backorderable
    shopifyId
    product {
      id
      name
      type
      status
      shopifyId
      deletedAt
    }
    inventoryItem {
      id
      sku
      totalQuantity
    }
  }
}
"""

WAREHOUSE_VARIANTS_QUERY = """
query DashboardVariantsByWarehouse($limit: Int, $offset: Int, $warehouseId: UUID!) {
  variants(limit: $limit, offset: $offset, inStock: $warehouseId) {
    id
    sku
    price
    averageSales
    totalQuantity
    backorderable
    shopifyId
    product {
      id
      name
      type
      status
      shopifyId
      deletedAt
    }
    inventoryItem {
      id
      sku
      totalQuantity
    }
  }
}
"""

# Discover warehouse list. SKUSavvy warehouses has no limit/offset args.
# We only require id/name so the dropdown can use real UUIDs for Wellington, Drop Ship, etc.
WAREHOUSES_CANDIDATES = [
    ("warehouses_id_name", """
    query Warehouses {
      warehouses { id name }
    }
    """),
    ("warehouses_with_location_name", """
    query Warehouses {
      warehouses { id name location { name } }
    }
    """),
    ("warehouses_with_location_city_state", """
    query Warehouses {
      warehouses { id name location { city state } }
    }
    """),
]

# Candidate warehouse inventory queries. They are intentionally isolated: one invalid query does not stop the dashboard.
WAREHOUSE_INVENTORY_CANDIDATES = [
    ("warehouse_inventory_id", """
    query WarehouseInventory($id: ID!) {
      warehouse(id: $id) {
        id name
        inventory { sku quantity qty totalQuantity availableQuantity onHand onHandQuantity unitCost variant { id sku } inventoryItem { id sku totalQuantity } product { id name } }
      }
    }
    """, lambda wid: {"id": wid}),
    ("warehouse_inventory_string", """
    query WarehouseInventory($id: String!) {
      warehouse(id: $id) {
        id name
        inventory { sku quantity qty totalQuantity availableQuantity onHand onHandQuantity unitCost variant { id sku } inventoryItem { id sku totalQuantity } product { id name } }
      }
    }
    """, lambda wid: {"id": wid}),
    ("inventory_warehouseId", """
    query InventoryByWarehouse($warehouseId: ID!, $limit: Int, $offset: Int) {
      inventory(warehouseId: $warehouseId, limit: $limit, offset: $offset) { sku quantity qty totalQuantity availableQuantity onHand onHandQuantity unitCost variant { id sku } inventoryItem { id sku totalQuantity } product { id name } }
    }
    """, lambda wid: {"warehouseId": wid, "limit": PAGE_SIZE, "offset": 0}),
    ("inventory_warehouse", """
    query InventoryByWarehouse($warehouse: ID!, $limit: Int, $offset: Int) {
      inventory(warehouse: $warehouse, limit: $limit, offset: $offset) { sku quantity qty totalQuantity availableQuantity onHand onHandQuantity unitCost variant { id sku } inventoryItem { id sku totalQuantity } product { id name } }
    }
    """, lambda wid: {"warehouse": wid, "limit": PAGE_SIZE, "offset": 0}),
    ("inventoryItems_warehouseId", """
    query InventoryItemsByWarehouse($warehouseId: ID!, $limit: Int, $offset: Int) {
      inventoryItems(warehouseId: $warehouseId, limit: $limit, offset: $offset) { sku quantity qty totalQuantity availableQuantity onHand onHandQuantity unitCost variant { id sku } product { id name } }
    }
    """, lambda wid: {"warehouseId": wid, "limit": PAGE_SIZE, "offset": 0}),
    ("inventoryItems_warehouse", """
    query InventoryItemsByWarehouse($warehouse: ID!, $limit: Int, $offset: Int) {
      inventoryItems(warehouse: $warehouse, limit: $limit, offset: $offset) { sku quantity qty totalQuantity availableQuantity onHand onHandQuantity unitCost variant { id sku } product { id name } }
    }
    """, lambda wid: {"warehouse": wid, "limit": PAGE_SIZE, "offset": 0}),
    ("warehouse_inventoryItems", """
    query WarehouseInventoryItems($id: ID!, $limit: Int, $offset: Int) {
      warehouse(id: $id) {
        id name
        inventoryItems(limit: $limit, offset: $offset) { sku quantity qty totalQuantity availableQuantity onHand onHandQuantity unitCost variant { id sku } product { id name } }
      }
    }
    """, lambda wid: {"id": wid, "limit": PAGE_SIZE, "offset": 0}),
    ("warehouse_items", """
    query WarehouseItems($id: ID!, $limit: Int, $offset: Int) {
      warehouse(id: $id) {
        id name
        items(limit: $limit, offset: $offset) { sku quantity qty totalQuantity availableQuantity onHand onHandQuantity unitCost variant { id sku } inventoryItem { id sku totalQuantity } product { id name } }
      }
    }
    """, lambda wid: {"id": wid, "limit": PAGE_SIZE, "offset": 0}),
    ("bins_by_warehouse", """
    query BinsByWarehouse($warehouseId: ID!, $limit: Int, $offset: Int) {
      bins(warehouseId: $warehouseId, limit: $limit, offset: $offset) { id name inventory { sku quantity qty totalQuantity availableQuantity onHand onHandQuantity variant { id sku } inventoryItem { id sku totalQuantity } } }
    }
    """, lambda wid: {"warehouseId": wid, "limit": PAGE_SIZE, "offset": 0}),
]

SCHEMA_DEBUG_QUERY = """
query QueryArgsDebug {
  __schema {
    queryType {
      fields {
        name
        args { name type { name kind ofType { name kind ofType { name kind ofType { name kind } } } } }
        type { name kind ofType { name kind ofType { name kind ofType { name kind } } } }
      }
    }
  }
}
"""

TYPE_DEBUG_QUERY = """
query TypeDebug($name: String!) {
  __type(name: $name) {
    name kind
    fields {
      name
      args { name type { name kind ofType { name kind } } }
      type { name kind ofType { name kind } }
    }
  }
}
"""


TYPE_CACHE: Dict[str, Any] = {}
# SKUSavvy exposes unit cost on InventoryItem, not Variant. These BigInt money fields are cents.
# weightedAvgCost is preferred because it is the closest match to current inventory COGS.
COST_FIELD_CANDIDATES = ["weightedAvgCost", "suggestedLandedCost", "defaultLandedCost"]

def get_type(type_name: str) -> Dict[str, Any] | None:
    if type_name in TYPE_CACHE:
        return TYPE_CACHE[type_name]
    try:
        TYPE_CACHE[type_name] = gql(TYPE_DEBUG_QUERY, {"name": type_name}).get("__type")
    except Exception as exc:  # noqa: BLE001
        TYPE_CACHE[type_name] = {"error": str(exc), "fields": []}
    return TYPE_CACHE[type_name]

def type_field_names(type_name: str) -> set[str]:
    t = get_type(type_name) or {}
    return {f.get("name") for f in (t.get("fields") or []) if f.get("name")}

def inventory_item_selection() -> str:
    names = type_field_names("InventoryItem")
    base = ["id", "sku", "totalQuantity"]
    cost_fields = [f for f in COST_FIELD_CANDIDATES if f in names]
    fields = []
    for f in base + cost_fields:
        if f in names and f not in fields:
            fields.append(f)
    return " ".join(fields or base)

def build_variants_query(by_warehouse: bool = False) -> str:
    args = "limit: $limit, offset: $offset, inStock: $warehouseId" if by_warehouse else "limit: $limit, offset: $offset"
    vars_decl = "$limit: Int, $offset: Int, $warehouseId: UUID!" if by_warehouse else "$limit: Int, $offset: Int"
    inv_sel = inventory_item_selection()
    return f"""
query DashboardVariants({vars_decl}) {{
  variants({args}) {{
    id
    sku
    price
    averageSales
    totalQuantity
    backorderable
    shopifyId
    product {{
      id
      name
      type
      status
      shopifyId
      deletedAt
    }}
    inventoryItem {{ {inv_sel} }}
    inventory {{
      warehouseId
      quantity
    }}
    quantities {{
      warehouseId
      quantity
      cost
      unitCosts {{
        cost
        quantity
      }}
    }}
  }}
}}
"""

def ensure_dirs() -> None:
    os.makedirs("data", exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def gql(query: str, variables: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not TOKEN:
        raise RuntimeError("Missing SKUSAVVY_TOKEN. Add it in GitHub → Settings → Secrets and variables → Actions.")
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={"accept": "application/json", "content-type": "application/json", "x-token": TOKEN},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=75) as res:
            payload = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="ignore")[:700]
        raise RuntimeError(f"SKUSavvy HTTP {exc.code}: {message}") from exc
    if payload.get("errors"):
        raise RuntimeError(" | ".join(str(e.get("message", e)) for e in payload["errors"]))
    return payload.get("data") or {}


def to_num(value: Any, fallback: float = 0) -> float:
    try:
        if value is None or value == "":
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def row_get(row: Dict[str, Any], *names: str) -> Any:
    """Case-insensitive CSV field getter."""
    lower = {str(k).strip().lower(): v for k, v in row.items()}
    for name in names:
        key = str(name).strip().lower()
        if key in lower:
            return lower[key]
    return None


def money_field(value: Any) -> float:
    """Convert SKUSavvy money BigInt values to dollars.

    In this account the inventory export and GraphQL price use 3 decimal places:
    165990 = $165.99, 130380 = $130.38.
    Using /100 inflated retail and COGS by 10x.
    """
    return round(to_num(value, 0) / 1000, 2)


def clean_status(status: Any) -> str:
    return str(status or "active").lower()


def fetch_variants() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen = set()
    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        data = gql(build_variants_query(False), {"limit": PAGE_SIZE, "offset": offset})
        batch = data.get("variants") or []
        for item in batch:
            key = item.get("id") or item.get("sku")
            if key and key not in seen:
                seen.add(key)
                rows.append(item)
        print(f"variants offset={offset} page={len(batch)} total={len(rows)}")
        if len(batch) < PAGE_SIZE:
            break
        time.sleep(PAGE_DELAY_SECONDS)
    return rows



def fetch_variants_by_warehouse(warehouse_id: str) -> List[Dict[str, Any]]:
    """Fetch variants that SKUSavvy reports as in stock for a warehouse.

    This uses the schema-provided variants(inStock: UUID) argument. It is the closest
    match to the warehouse inventory screen until the account exposes a bulk
    InventoryQty query. It makes the dashboard change by warehouse and avoids showing
    SKUs that are not present in the selected warehouse.
    """
    rows: List[Dict[str, Any]] = []
    seen = set()
    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        data = gql(build_variants_query(True), {"limit": PAGE_SIZE, "offset": offset, "warehouseId": warehouse_id})
        batch = data.get("variants") or []
        for item in batch:
            key = item.get("id") or item.get("sku")
            if key and key not in seen:
                seen.add(key)
                rows.append(item)
        print(f"warehouse variants warehouse={warehouse_id} offset={offset} page={len(batch)} total={len(rows)}")
        if len(batch) < PAGE_SIZE:
            break
        time.sleep(PAGE_DELAY_SECONDS)
    return rows

def simple_location(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = [value.get("city"), value.get("state"), value.get("name")]
        return ", ".join(str(x) for x in parts if x) or ""
    return ""


def fetch_warehouses() -> List[Dict[str, str]]:
    for name, query in WAREHOUSES_CANDIDATES:
        try:
            data = gql(query)
            items = data.get("warehouses") or []
            out = []
            for wh in items:
                if isinstance(wh, dict) and wh.get("id") and wh.get("name"):
                    out.append({"id": str(wh["id"]), "name": str(wh["name"]), "location": simple_location(wh.get("location") or wh)})
            if out:
                print(f"warehouses OK via {name}: {len(out)}")
                # Keep Wellington first/default if present.
                out.sort(key=lambda x: 0 if x["id"] == DEFAULT_WAREHOUSE_ID else 1)
                return out
        except Exception as exc:  # noqa: BLE001
            print(f"warehouse list candidate failed {name}: {exc}")
    return KNOWN_WAREHOUSES


def extract_sku(obj: Dict[str, Any]) -> str | None:
    for key in ("sku", "SKU"):
        if obj.get(key):
            return str(obj[key])
    for nested_key in ("variant", "inventoryItem", "productVariant", "item"):
        nested = obj.get(nested_key)
        if isinstance(nested, dict) and nested.get("sku"):
            return str(nested["sku"])
    return None


def extract_qty(obj: Dict[str, Any]) -> float | None:
    # Prefer on-hand / total style quantities. Use available only if that is all the API returns.
    for key in ("onHandQuantity", "onHand", "quantity", "qty", "totalQuantity", "stock", "stockAvailable", "availableQuantity"):
        if key in obj and obj[key] is not None:
            return to_num(obj[key], 0)
    inv = obj.get("inventoryItem")
    if isinstance(inv, dict) and inv.get("totalQuantity") is not None:
        return to_num(inv.get("totalQuantity"), 0)
    return None


def walk_inventory(node: Any, out: Dict[str, float]) -> None:
    if isinstance(node, list):
        for item in node:
            walk_inventory(item, out)
        return
    if isinstance(node, dict):
        sku = extract_sku(node)
        qty = extract_qty(node)
        if sku and qty is not None:
            out[sku] = out.get(sku, 0) + qty
        for value in node.values():
            if isinstance(value, (list, dict)):
                walk_inventory(value, out)


def fetch_warehouse_inventory(warehouse_id: str) -> Tuple[Dict[str, float], str | None, str | None]:
    errors: List[str] = []
    for name, query, variables_fn in WAREHOUSE_INVENTORY_CANDIDATES:
        try:
            data = gql(query, variables_fn(warehouse_id))
            stock_by_sku: Dict[str, float] = {}
            walk_inventory(data, stock_by_sku)
            if stock_by_sku:
                print(f"warehouse inventory OK via {name}: {len(stock_by_sku)} SKUs")
                return stock_by_sku, None, name
            errors.append(f"{name}: query returned but no SKU/QTY pairs were found")
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            errors.append(f"{name}: {msg[:280]}")
            print(f"warehouse inventory candidate failed {name}: {msg[:280]}")
    return {}, " || ".join(errors[-4:]), None



def variant_stock_map(variants: List[Dict[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for v in variants:
        sku = str(v.get("sku") or (v.get("inventoryItem") or {}).get("sku") or "").strip()
        if not sku:
            continue
        qty = to_num(v.get("totalQuantity"), to_num((v.get("inventoryItem") or {}).get("totalQuantity"), 0))
        out[sku] = qty
    return out

def write_schema_debug() -> None:
    debug: Dict[str, Any] = {"generatedAt": now_iso()}
    try:
        data = gql(SCHEMA_DEBUG_QUERY)
        fields = data.get("__schema", {}).get("queryType", {}).get("fields", [])
        debug["queryFields"] = [
            f for f in fields if any(term in f.get("name", "").lower() for term in ["warehouse", "inventory", "location", "bin", "stock", "variant"])
        ]
        for type_name in ["Warehouse", "Inventory", "InventoryItem", "Variant", "ProductVariant", "Bin", "Lot"]:
            try:
                debug[type_name] = gql(TYPE_DEBUG_QUERY, {"name": type_name}).get("__type")
            except Exception as exc:  # noqa: BLE001
                debug[type_name] = {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        debug["error"] = str(exc)
    write_json("data/schema-debug.json", debug)



def _warehouse_id_from_text(value: Any, filename: str = "") -> str | None:
    text = str(value or "").strip().lower()
    file_text = str(filename or "").strip().lower()
    for key, wid in WAREHOUSE_NAME_TO_ID.items():
        if key in text or key in file_text:
            return wid
    return None


def load_inventory_csv_maps(warehouses: List[Dict[str, str]]) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, float]], Dict[str, Dict[str, float]], Dict[str, Dict[str, float]], Dict[str, str]]:
    """Load SKUSavvy Warehouse → Inventory CSV exports if they are committed in the repo.

    Supported locations:
      - data/wellington_inventory.csv
      - data/corro_trailer_1_inventory.csv
      - data/inventory-*.csv
      - inventory-*.csv

    These CSV exports contain the cost shown by SKUSavvy UI. GraphQL may return null for
    the same SKU, so CSV values override API cost for COGS validation.
    """
    allowed = {str(w.get("id")) for w in warehouses if w.get("id")}
    stock_maps: Dict[str, Dict[str, float]] = {wid: {} for wid in allowed}
    cost_value_maps: Dict[str, Dict[str, float]] = {wid: {} for wid in allowed}
    unit_cost_maps: Dict[str, Dict[str, float]] = {wid: {} for wid in allowed}
    retail_value_maps: Dict[str, Dict[str, float]] = {wid: {} for wid in allowed}
    sources: Dict[str, str] = {}

    patterns = [
        "data/wellington_inventory.csv",
        "data/corro_trailer_1_inventory.csv",
        "data/drop_ship_inventory.csv",
        "data/inventory-*.csv",
        "inventory-*.csv",
    ]
    files: List[str] = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    files = sorted(set(files))

    for file_path in files:
        try:
            with open(file_path, newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    sku = str(row_get(row, "sku", "SKU") or "").strip()
                    if not sku:
                        continue
                    wid = _warehouse_id_from_text(row_get(row, "warehouse", "warehouseName", "WarehouseName"), file_path)
                    if not wid or (allowed and wid not in allowed):
                        continue
                    qty = to_num(row_get(row, "quantity", "qty", "Qty"), 0)
                    avg_cost = money_field(row_get(row, "avgCost", "AvgCost", "unitCost", "UnitCost", "minCost", "MinCost", "cost", "Cost"))
                    price = money_field(row_get(row, "price", "Price", "retail", "Retail"))
                    CSV_PRODUCT_DETAILS.setdefault(sku, {
                        "sku": sku,
                        "productName": row_get(row, "productName", "ProductName") or sku,
                        "category": row_get(row, "productType", "ProductType") or "—",
                        "vendor": row_get(row, "vendor", "Vendor", "vendorName", "VendorName", "brand", "Brand") or "—",
                        "price": price,
                    })
                    if CSV_PRODUCT_DETAILS.get(sku, {}).get("vendor") in (None, "", "—"):
                        CSV_PRODUCT_DETAILS.setdefault(sku, {})["vendor"] = row_get(row, "vendor", "Vendor", "vendorName", "VendorName", "brand", "Brand") or "—"
                    stock_maps.setdefault(wid, {})[sku] = stock_maps.setdefault(wid, {}).get(sku, 0) + qty
                    if avg_cost > 0 and qty > 0:
                        cost_value_maps.setdefault(wid, {})[sku] = round(cost_value_maps.setdefault(wid, {}).get(sku, 0) + (qty * avg_cost), 4)
                    elif avg_cost > 0 and qty <= 0:
                        # Keep the negative stock row for reconciliation, but do not subtract it from inventory value.
                        unit_cost_maps.setdefault(wid, {})[sku] = avg_cost
                    if price > 0 and qty > 0:
                        retail_value_maps.setdefault(wid, {})[sku] = round(retail_value_maps.setdefault(wid, {}).get(sku, 0) + (qty * price), 4)
                    sources[wid] = file_path
        except Exception as exc:  # noqa: BLE001
            print(f"CSV inventory load failed {file_path}: {exc}")

    for wid, sku_costs in cost_value_maps.items():
        for sku, cost_total in sku_costs.items():
            qty_total = stock_maps.get(wid, {}).get(sku, 0)
            if qty_total > 0:
                unit_cost_maps.setdefault(wid, {})[sku] = round(cost_total / qty_total, 4)
                cost_value_maps[wid][sku] = round(cost_total, 2)
    retail_value_maps = {wid: {sku: round(v, 2) for sku, v in sku_map.items()} for wid, sku_map in retail_value_maps.items() if sku_map}
    stock_maps = {wid: sku_map for wid, sku_map in stock_maps.items() if sku_map}
    cost_value_maps = {wid: sku_map for wid, sku_map in cost_value_maps.items() if sku_map}
    unit_cost_maps = {wid: sku_map for wid, sku_map in unit_cost_maps.items() if sku_map}
    return stock_maps, cost_value_maps, unit_cost_maps, retail_value_maps, sources

def parse_date(value: Any):
    if value is None or value == "":
        return None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "nat", "none", "null"}:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        return None


def load_expiring_rows(warehouses: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Build Expiring Inventory rows from SKUSavvy Warehouse Inventory CSV exports.

    Damaged quantities are not present in this Inventory export. Expiration is present
    in the `expiration` column, so this tab reports expired and upcoming expirations.
    """
    allowed = {str(w.get("id")) for w in warehouses if w.get("id")}
    today = datetime.now(timezone.utc).date()
    rows: List[Dict[str, Any]] = []
    patterns = [
        "data/wellington_inventory.csv",
        "data/corro_trailer_1_inventory.csv",
        "data/drop_ship_inventory.csv",
        "data/inventory-*.csv",
        "inventory-*.csv",
    ]
    files: List[str] = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    for file_path in sorted(set(files)):
        try:
            with open(file_path, newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    exp = parse_date(row_get(row, "expiration", "LotExpiration", "lotExpiration"))
                    if not exp:
                        continue
                    sku = str(row_get(row, "sku", "SKU") or "").strip()
                    if not sku:
                        continue
                    wid = _warehouse_id_from_text(row_get(row, "warehouse", "warehouseName", "WarehouseName"), file_path)
                    if not wid or (allowed and wid not in allowed):
                        continue
                    qty = to_num(row_get(row, "quantity", "qty", "Qty"), 0)
                    if qty <= 0:
                        continue
                    avg_cost = money_field(row_get(row, "avgCost", "AvgCost", "unitCost", "UnitCost", "minCost", "MinCost", "cost", "Cost"))
                    price = money_field(row_get(row, "price", "Price", "retail", "Retail"))
                    days = (exp - today).days
                    if days < 0:
                        bucket = "expired"
                        status = "Expired"
                    elif exp.year == today.year and exp.month == today.month:
                        bucket = "this_month"
                        status = "This month"
                    elif days <= 60:
                        bucket = "next_60"
                        status = "Next 60 days"
                    elif days <= 90:
                        bucket = "next_90"
                        status = "Next 90 days"
                    else:
                        bucket = "future"
                        status = "Future"
                    rows.append({
                        "sku": sku,
                        "productName": row_get(row, "productName", "ProductName") or sku,
                        "category": row_get(row, "productType", "ProductType") or "—",
                        "warehouseId": wid,
                        "warehouseName": row_get(row, "warehouse", "warehouseName", "WarehouseName") or _warehouse_name_from_id(wid, warehouses),
                        "vendor": row_get(row, "vendor", "Vendor", "vendorName", "VendorName", "brand", "Brand") or CSV_PRODUCT_DETAILS.get(sku, {}).get("vendor") or "—",
                        "lotName": row_get(row, "lotName", "LotName") or "—",
                        "expiration": exp.isoformat(),
                        "daysToExpire": days,
                        "quantity": qty,
                        "unitCost": avg_cost,
                        "inventoryValue": round(qty * avg_cost, 2),
                        "retailValue": round(qty * price, 2),
                        "bucket": bucket,
                        "status": status,
                        "source": file_path,
                    })
        except Exception as exc:  # noqa: BLE001
            print(f"CSV expiration load failed {file_path}: {exc}")
    # Show urgent first: expired, this month, 60, 90, then future.
    order = {"expired": 0, "this_month": 1, "next_60": 2, "next_90": 3, "future": 4}
    rows.sort(key=lambda r: (order.get(str(r.get("bucket")), 99), r.get("expiration") or "9999-12-31", r.get("sku") or ""))
    return rows


def _warehouse_name_from_id(wid: str, warehouses: List[Dict[str, str]]) -> str:
    for wh in warehouses:
        if str(wh.get("id")) == str(wid):
            return str(wh.get("name") or wid)
    return wid


def stock_and_cost_maps_from_variants(variants: List[Dict[str, Any]], warehouses: List[Dict[str, str]]) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
    """Build warehouse stock and COGS maps from SKUSavvy Variant.inventory / Variant.quantities.

    Stock source:
      Variant.inventory { warehouseId quantity } -> matches Warehouse → Inventory counts.

    Cost source:
      Variant.quantities { warehouseId quantity cost unitCosts { cost quantity } }.
      The Qty.cost field is the unit cost shown on the SKUSavvy inventory screen.
      Costs are BigInt cents, so we convert to dollars before multiplying by quantity.
    """
    allowed = {str(w.get("id")) for w in warehouses if w.get("id")}
    stock_maps: Dict[str, Dict[str, float]] = {wid: {} for wid in allowed}
    cost_value_maps: Dict[str, Dict[str, float]] = {wid: {} for wid in allowed}
    cost_qty_maps: Dict[str, Dict[str, float]] = {wid: {} for wid in allowed}

    # 1) InventoryQty records are the best stock source.
    for v in variants:
        sku = str(v.get("sku") or (v.get("inventoryItem") or {}).get("sku") or "").strip()
        if not sku:
            continue
        for q in v.get("inventory") or []:
            if not isinstance(q, dict):
                continue
            wid = str(q.get("warehouseId") or "").strip()
            if not wid or (allowed and wid not in allowed):
                continue
            qty = to_num(q.get("quantity"), 0)
            if qty <= 0:
                continue
            stock_maps.setdefault(wid, {})[sku] = stock_maps.setdefault(wid, {}).get(sku, 0) + qty

    # 2) Qty records carry cost. They can be split by bin/lot, so aggregate cost by SKU+warehouse.
    for v in variants:
        sku = str(v.get("sku") or (v.get("inventoryItem") or {}).get("sku") or "").strip()
        if not sku:
            continue
        for q in v.get("quantities") or []:
            if not isinstance(q, dict):
                continue
            wid = str(q.get("warehouseId") or "").strip()
            if not wid or (allowed and wid not in allowed):
                continue
            qty = to_num(q.get("quantity"), 0)
            if qty <= 0:
                continue
            unit_cost = 0.0
            if q.get("cost") is not None:
                unit_cost = money_field(q.get("cost"))
            if unit_cost <= 0:
                for uc in q.get("unitCosts") or []:
                    if isinstance(uc, dict) and uc.get("cost") is not None:
                        unit_cost = money_field(uc.get("cost"))
                        break
            if unit_cost <= 0:
                continue
            cost_value_maps.setdefault(wid, {})[sku] = cost_value_maps.setdefault(wid, {}).get(sku, 0) + (qty * unit_cost)
            cost_qty_maps.setdefault(wid, {})[sku] = cost_qty_maps.setdefault(wid, {}).get(sku, 0) + qty

    unit_cost_maps: Dict[str, Dict[str, float]] = {}
    for wid, sku_costs in cost_value_maps.items():
        for sku, cost_total in sku_costs.items():
            qty_total = cost_qty_maps.get(wid, {}).get(sku, 0)
            if qty_total > 0:
                unit_cost_maps.setdefault(wid, {})[sku] = round(cost_total / qty_total, 4)
                cost_value_maps[wid][sku] = round(cost_total, 2)

    # Keep only warehouses that have data.
    stock_maps = {wid: sku_map for wid, sku_map in stock_maps.items() if sku_map}
    cost_value_maps = {wid: sku_map for wid, sku_map in cost_value_maps.items() if sku_map}
    unit_cost_maps = {wid: sku_map for wid, sku_map in unit_cost_maps.items() if sku_map}
    return stock_maps, cost_value_maps, unit_cost_maps


def add_csv_only_variants(variants: List[Dict[str, Any]], stock_maps: Dict[str, Dict[str, float]], retail_value_maps: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    """Add rows for SKUs present in CSV exports but absent from GraphQL variants.

    This prevents a warehouse from showing zero if SKUSavvy GraphQL omits a CSV SKU.
    """
    existing = {str(v.get("sku") or (v.get("inventoryItem") or {}).get("sku") or "").strip() for v in variants}
    all_skus = set()
    for sku_map in stock_maps.values():
        all_skus.update(sku_map.keys())
    extra = []
    for sku in sorted(all_skus - existing):
        details = CSV_PRODUCT_DETAILS.get(sku, {})
        price = details.get("price") or 0
        # Convert dollars back to SKUSavvy BigInt scale so normalize_rows/money_field returns the same value.
        price_bigint = int(round(float(price) * 1000)) if price else 0
        extra.append({
            "id": f"csv-{sku}",
            "sku": sku,
            "price": price_bigint,
            "averageSales": 0,
            "totalQuantity": sum(m.get(sku, 0) for m in stock_maps.values()),
            "backorderable": False,
            "shopifyId": "—",
            "product": {
                "id": f"csv-{sku}",
                "name": details.get("productName") or sku,
                "type": details.get("category") or "—",
                "status": "ACTIVE",
                "shopifyId": "—",
                "deletedAt": None,
            },
            "inventoryItem": {"id": f"csv-{sku}", "sku": sku, "totalQuantity": sum(m.get(sku, 0) for m in stock_maps.values())},
            "vendor": details.get("vendor") or "—",
        })
    if extra:
        print(f"Added CSV-only SKU rows: {len(extra)}")
    return variants + extra


def normalize_rows(variants: List[Dict[str, Any]], stock_maps: Dict[str, Dict[str, float]], cost_value_maps: Dict[str, Dict[str, float]], unit_cost_maps: Dict[str, Dict[str, float]], retail_value_maps: Dict[str, Dict[str, float]] | None = None, shopify_sales: Dict[str, Dict[str, Dict[str, float]]] | None = None) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for idx, v in enumerate(variants):
        sku = str(v.get("sku") or (v.get("inventoryItem") or {}).get("sku") or "—")
        total_stock = to_num(v.get("totalQuantity"), to_num((v.get("inventoryItem") or {}).get("totalQuantity"), 0))
        price = money_field(v.get("price"))
        
        inv_item = v.get("inventoryItem") or {}
        unit_cost = 0
        for cost_key in COST_FIELD_CANDIDATES:
            if inv_item.get(cost_key) is not None:
                unit_cost = money_field(inv_item.get(cost_key))
                break
        avg_daily = to_num(v.get("averageSales"), 0)
        product = v.get("product") or {}
        csv_details = CSV_PRODUCT_DETAILS.get(sku, {})
        vendor = v.get("vendor") or product.get("vendor") or product.get("vendorName") or csv_details.get("vendor") or "—"
        status = clean_status(product.get("status") or ("archived" if product.get("deletedAt") else "active"))
        stock_by_wh = {wid: stock_map.get(sku, 0) for wid, stock_map in stock_maps.items()}
        unit_cost_by_wh = {wid: unit_map.get(sku, 0) for wid, unit_map in unit_cost_maps.items() if unit_map.get(sku, 0) > 0}
        cost_value_by_wh = {wid: cost_map.get(sku, 0) for wid, cost_map in cost_value_maps.items() if cost_map.get(sku, 0) > 0}
        retail_value_by_wh = {wid: retail_map.get(sku, 0) for wid, retail_map in (retail_value_maps or {}).items() if retail_map.get(sku, 0) > 0}
        all_qty_cost = sum(cost_qty for cost_qty in cost_value_by_wh.values())
        all_retail_value = sum(v for v in retail_value_by_wh.values())
        if unit_cost <= 0 and unit_cost_by_wh:
            qty_for_weight = sum(stock_by_wh.get(wid, 0) for wid in unit_cost_by_wh)
            if qty_for_weight > 0:
                unit_cost = round(sum(unit_cost_by_wh[wid] * stock_by_wh.get(wid, 0) for wid in unit_cost_by_wh) / qty_for_weight, 4)
        normalized.append({
            "rank": idx + 1,
            "id": v.get("id"),
            "sku": sku,
            "productName": product.get("name") or csv_details.get("productName") or sku or "Untitled product",
            "category": product.get("type") or csv_details.get("category") or "—",
            "vendor": vendor,
            "productStatus": status,
            "shopifyId": v.get("shopifyId") or product.get("shopifyId") or "—",
            "variantId": v.get("id"),
            "inventoryItemId": (v.get("inventoryItem") or {}).get("id"),
            "movementDraftSource": "coverage_proxy",
            "movementDraftNote": "Draft metric. SKUSavvy inventoryLogs confirmed available on sample SKU; bulk extraction not enabled in this review version.",
            "backorderable": bool(v.get("backorderable")),
            "totalStock": total_stock,
            "stockByWarehouse": stock_by_wh,
            "negativeStockByWarehouse": {wid: qty for wid, qty in stock_by_wh.items() if qty < 0},
            "price": price,
            "unitCost": unit_cost,
            "unitCostByWarehouse": unit_cost_by_wh,
            "costValueByWarehouse": cost_value_by_wh,
            "retailValueByWarehouse": retail_value_by_wh,
            "retailValueTotal": round(all_retail_value if all_retail_value > 0 else total_stock * price, 2),
            "costValueTotal": round(all_qty_cost if all_qty_cost > 0 else total_stock * unit_cost, 2),
            "avgDailySales": avg_daily,
            "marginBySku": round(((price - unit_cost) / price) * 100, 2) if price > 0 and unit_cost > 0 else None,
            "shopifySalesByMonth": (shopify_sales or {}).get(sku, {}),
        })
    return normalized



def month_key(dt: date) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def month_ranges(months_back: int = 18) -> List[Tuple[str, datetime, datetime]]:
    today = datetime.now(timezone.utc).date().replace(day=1)
    out: List[Tuple[str, datetime, datetime]] = []
    y, m = today.year, today.month
    for i in range(months_back):
        mm = m - i
        yy = y
        while mm <= 0:
            yy -= 1
            mm += 12
        start_date = date(yy, mm, 1)
        if mm == 12:
            end_date = date(yy + 1, 1, 1)
        else:
            end_date = date(yy, mm + 1, 1)
        out.append((month_key(start_date), datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc), datetime(end_date.year, end_date.month, end_date.day, tzinfo=timezone.utc)))
    return out


def normalize_shop_domain(value: str) -> str:
    v = (value or "").strip().replace("https://", "").replace("http://", "").strip("/")
    if v and "." not in v:
        v = f"{v}.myshopify.com"
    return v


def parse_link_next(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        if 'rel="next"' in part:
            start = part.find("<")
            end = part.find(">")
            if start >= 0 and end > start:
                return part[start + 1:end]
    return None


def shopify_request_json(url: str) -> Tuple[Dict[str, Any], str | None]:
    req = urllib.request.Request(
        url,
        headers={"accept": "application/json", "X-Shopify-Access-Token": SHOPIFY_ADMIN_ACCESS_TOKEN},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=75) as res:
            payload = json.loads(res.read().decode("utf-8"))
            link = res.headers.get("Link")
            return payload, parse_link_next(link)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="ignore")[:700]
        raise RuntimeError(f"Shopify HTTP {exc.code}: {message}") from exc


def add_shopify_sale(sales: Dict[str, Dict[str, Dict[str, float]]], sku: str, month: str, quantity: float, net_sales: float) -> None:
    sku = str(sku or "").strip()
    if not sku:
        return
    month_map = sales.setdefault(sku, {})
    row = month_map.setdefault(month, {"units": 0.0, "sales": 0.0})
    row["units"] = round(row.get("units", 0) + quantity, 4)
    row["sales"] = round(row.get("sales", 0) + net_sales, 2)


def load_shopify_sales_csv() -> Dict[str, Dict[str, Dict[str, float]]]:
    """Optional fallback: data/shopify_sales.csv with real Shopify sales by SKU.

    Supported columns include:
      month, sku, quantity/units_sold, net_sales/sales/total_sales
    """
    sales: Dict[str, Dict[str, Dict[str, float]]] = {}
    for file_path in sorted(set(glob.glob("data/shopify_sales*.csv") + glob.glob("shopify_sales*.csv"))):
        try:
            with open(file_path, newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    sku = row_get(row, "sku", "SKU", "Variant SKU", "variant_sku")
                    raw_month = row_get(row, "month", "Month", "YYYY-MM", "year_month")
                    if raw_month:
                        month = str(raw_month).strip()[:7]
                    else:
                        raw_date = row_get(row, "date", "Date", "created_at", "Created At")
                        parsed = parse_date(raw_date)
                        month = month_key(parsed) if parsed else ""
                    qty = to_num(row_get(row, "quantity", "qty", "units", "units_sold", "Quantity", "Net quantity"), 0)
                    amount = to_num(row_get(row, "net_sales", "sales", "total_sales", "gross_sales", "Net sales", "Total sales"), 0)
                    if sku and month:
                        add_shopify_sale(sales, str(sku), month, qty, amount)
        except Exception as exc:  # noqa: BLE001
            print(f"Shopify sales CSV load failed {file_path}: {exc}")
    return sales


def fetch_shopify_sales_api() -> Tuple[Dict[str, Dict[str, Dict[str, float]]], Dict[str, Any]]:
    """Fetch real paid Shopify order line sales by SKU using Admin REST API.

    Required GitHub Actions secrets:
      SHOPIFY_STORE_DOMAIN, SHOPIFY_ADMIN_ACCESS_TOKEN
    The token needs read_orders access. For older orders, Shopify may require read_all_orders.
    """
    meta: Dict[str, Any] = {"source": "none", "months": [], "error": None}
    sales: Dict[str, Dict[str, Dict[str, float]]] = {}
    domain = normalize_shop_domain(SHOPIFY_STORE_DOMAIN)
    if not domain or not SHOPIFY_ADMIN_ACCESS_TOKEN:
        meta["error"] = "Missing SHOPIFY_STORE_DOMAIN or SHOPIFY_ADMIN_ACCESS_TOKEN."
        return sales, meta
    base = f"https://{domain}/admin/api/{SHOPIFY_API_VERSION}/orders.json"
    for month, start, end in month_ranges(SHOPIFY_MONTHS_BACK):
        created_min = start.isoformat().replace("+00:00", "Z")
        created_max = end.isoformat().replace("+00:00", "Z")
        url = (
            f"{base}?status=any&financial_status=paid,partially_refunded,refunded"
            f"&created_at_min={created_min}&created_at_max={created_max}"
            f"&limit=250&fields=id,created_at,currency,line_items"
        )
        page = 0
        while url:
            payload, next_url = shopify_request_json(url)
            orders = payload.get("orders") or []
            for order in orders:
                for li in order.get("line_items") or []:
                    sku = str(li.get("sku") or "").strip()
                    if not sku:
                        continue
                    qty = to_num(li.get("quantity"), 0)
                    price = to_num(li.get("price"), 0)
                    discount = to_num(li.get("total_discount"), 0)
                    net_sales = max((price * qty) - discount, 0)
                    add_shopify_sale(sales, sku, month, qty, net_sales)
            page += 1
            print(f"shopify orders month={month} page={page} orders={len(orders)} sales_skus={len(sales)}")
            url = next_url
            time.sleep(0.5)
        meta["months"].append(month)
    meta["source"] = f"Shopify Admin REST API {SHOPIFY_API_VERSION}"
    return sales, meta


def load_real_shopify_sales() -> Tuple[Dict[str, Dict[str, Dict[str, float]]], Dict[str, Any]]:
    csv_sales = load_shopify_sales_csv()
    api_sales, meta = fetch_shopify_sales_api()
    if api_sales:
        meta["status"] = "ok"
        return api_sales, meta
    if csv_sales:
        return csv_sales, {"source": "data/shopify_sales.csv", "status": "csv", "error": meta.get("error")}
    return {}, {"source": "none", "status": "missing", "error": meta.get("error") or "No Shopify API credentials or sales CSV found."}

def main() -> None:
    ensure_dirs()
    if not TOKEN:
        write_json("data/dashboard.json", {
            "generatedAt": now_iso(),
            "error": "Missing SKUSAVVY_TOKEN. Add it as a GitHub Actions secret and run the workflow again.",
            "warehouses": KNOWN_WAREHOUSES,
            "defaultWarehouseId": DEFAULT_WAREHOUSE_ID,
            "warehouseDataStatus": "missing_token",
            "rows": [],
        })
        return

    warehouse_errors: Dict[str, str] = {}
    warehouse_query_used: Dict[str, str] = {}
    stock_maps: Dict[str, Dict[str, float]] = {}
    cost_value_maps: Dict[str, Dict[str, float]] = {}
    unit_cost_maps: Dict[str, Dict[str, float]] = {}

    write_schema_debug()
    warehouses = fetch_warehouses()
    variants = fetch_variants()

    # Primary source for warehouse stock: Variant.inventory -> InventoryQty { warehouseId, quantity }.
    # This uses the exact schema fields confirmed in GraphiQL and should match
    # SKUSavvy Warehouse → Inventory much more closely than Variant.totalQuantity.
    stock_maps, cost_value_maps, unit_cost_maps = stock_and_cost_maps_from_variants(variants, warehouses)
    for wid in stock_maps:
        warehouse_query_used[wid] = "variants { inventory { warehouseId quantity } quantities { warehouseId quantity cost unitCosts { cost quantity } } }"

    # Fallback: if quantities are not returned for a warehouse/account, use inStock
    # only to show which SKUs belong to the warehouse. It is less exact for QTY, so
    # Variant.quantities always wins when present.
    for wh in warehouses:
        if wh["id"] in stock_maps:
            continue
        try:
            wh_variants = fetch_variants_by_warehouse(wh["id"])
            stock = variant_stock_map(wh_variants)
            if stock:
                stock_maps[wh["id"]] = stock
                fb_stock_maps, fb_cost_value_maps, fb_unit_cost_maps = stock_and_cost_maps_from_variants(wh_variants, warehouses)
                cost_value_maps.update(fb_cost_value_maps)
                unit_cost_maps.update(fb_unit_cost_maps)
                warehouse_query_used[wh["id"]] = "fallback: variants(inStock: warehouseId)"
            else:
                warehouse_errors[wh["id"]] = "No Variant.quantities records and variants(inStock) returned no SKUs for this warehouse"
        except Exception as exc:  # noqa: BLE001
            warehouse_errors[wh["id"]] = str(exc)[:500]
            print(f"warehouse variants failed {wh['name']} {wh['id']}: {exc}")

    # CSV exports from SKUSavvy Warehouse → Inventory are the source of truth for Unit Cost/COGS.
    # They also confirm retail values using the same money scale as SKUSavvy UI.
    retail_value_maps: Dict[str, Dict[str, float]] = {}
    csv_stock_maps, csv_cost_value_maps, csv_unit_cost_maps, csv_retail_value_maps, csv_sources = load_inventory_csv_maps(warehouses)
    if csv_stock_maps:
        print(f"CSV warehouse inventory loaded: {csv_sources}")
        stock_maps.update(csv_stock_maps)
        cost_value_maps.update(csv_cost_value_maps)
        unit_cost_maps.update(csv_unit_cost_maps)
        retail_value_maps.update(csv_retail_value_maps)
        for wid in csv_stock_maps:
            warehouse_query_used[wid] = "SKUSavvy Warehouse Inventory CSV export"

    shopify_sales, shopify_sales_meta = load_real_shopify_sales()

    warehouse_status = "ok" if stock_maps else "needs_mapping"
    warning = None
    if stock_maps:
        warning = (
            "Warehouse filter uses SKUSavvy Variant.inventory for stock and Variant.quantities / Qty.cost for unit cost by warehouse. "
            "Validate COGS against SKUSavvy Warehouse → Inventory exports."
        )
    else:
        warning = (
            "Warehouse-level inventory was not confirmed from SKUSavvy GraphQL. "
            "The dashboard will keep showing total inventory as a safe fallback instead of false zeroes."
        )

    payload = {
        "generatedAt": now_iso(),
        "source": "SKUSavvy GraphQL via GitHub Actions Python",
        "warehouses": warehouses,
        "defaultWarehouseId": DEFAULT_WAREHOUSE_ID,
        "warehouseDataStatus": warehouse_status,
        "warehouseWarning": warning,
        "warehouseErrors": warehouse_errors,
        "warehouseQueryUsed": warehouse_query_used,
        "inventoryCsvSources": csv_sources if 'csv_sources' in locals() else {},
        "expiringRows": load_expiring_rows(warehouses),
        "turnoverDefinition": "Inventory turnover buckets are calculated from coverage days = current warehouse stock / SKUSavvy average daily sales. If an inventory received date is not available, this is the reviewable proxy. If average daily sales is zero or missing, the SKU is treated as +90 days / no movement.",
        "rotationDefinition": "Rotation Estimate uses coverage days = current warehouse stock / average daily sales. It is not an exact received-date aging report. SKUSavvy inventoryLogs exists and was validated on APF-E02, but this version does not bulk-query logs for every SKU to avoid API cost/time.",
        "shopifySalesStatus": shopify_sales_meta,
        "expiringDefinition": "Expiring / Damaged uses CSV LotExpiration/expiration and can be filtered by selected/current month, next 60 days, next 90 days and warehouse. Damaged requires a separate SKUSavvy damaged/loss log if needed.",
        "rows": normalize_rows(add_csv_only_variants(variants, stock_maps, retail_value_maps), stock_maps, cost_value_maps, unit_cost_maps, retail_value_maps, shopify_sales),
    }
    write_json("data/dashboard.json", payload)
    print(f"Wrote data/dashboard.json rows={len(payload['rows'])} warehouse_status={warehouse_status}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Always write a JSON file so GitHub Pages never returns a 404/HTML error.
        ensure_dirs()
        write_json("data/dashboard.json", {
            "generatedAt": now_iso(),
            "source": "SKUSavvy GraphQL via GitHub Actions Python",
            "error": str(exc),
            "warehouses": KNOWN_WAREHOUSES,
            "defaultWarehouseId": DEFAULT_WAREHOUSE_ID,
            "warehouseDataStatus": "error",
            "warehouseWarning": "Data generation failed. Check GitHub Actions logs and verify SKUSAVVY_TOKEN.",
            "rows": [],
        })
        print(f"Wrote fallback data/dashboard.json because generation failed: {exc}")
        raise
