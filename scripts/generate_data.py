#!/usr/bin/env python3
"""
Genera site/data/dashboard.json para GitHub Pages.
El token SKUSAVVY_TOKEN se lee desde GitHub Secrets / variable de entorno.
No imprime ni guarda el token.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

GRAPHQL_URL = os.getenv("SKUSAVVY_GRAPHQL", "https://app.skusavvy.com/graphql")
TOKEN = os.getenv("SKUSAVVY_TOKEN", "").strip()
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "100"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "200"))
PAGE_DELAY_SECONDS = float(os.getenv("PAGE_DELAY_SECONDS", "1.2"))
DEFAULT_WAREHOUSE_ID = "019b6b44-4eea-7613-9f82-9af97d2255d"

WAREHOUSES = [
    {"id": DEFAULT_WAREHOUSE_ID, "name": "Wellington Warehouse", "location": "Wellington, FL"},
    {"id": "drop-ship", "name": "Drop Ship", "location": "Wellington, FL"},
    {"id": "corro-trailer-1", "name": "Corro Trailer 1", "location": "Saugerties, NY"},
]

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

# Estos queries son candidatos. SKUSavvy puede tener nombres distintos por cuenta/version.
# Si fallan, el script igual publica dashboard.json con warning y schema-debug.json.
WAREHOUSE_CANDIDATE_QUERIES = [
    ("warehouse_inventory", """
    query WarehouseInventory($id: ID!) {
      warehouse(id: $id) {
        id
        name
        inventory {
          sku
          quantity
          qty
          totalQuantity
          availableQuantity
          unitCost
          variant { id sku }
          inventoryItem { id sku totalQuantity }
          product { id name }
        }
      }
    }
    """),
    ("inventory_by_warehouse", """
    query InventoryByWarehouse($warehouseId: ID!, $limit: Int, $offset: Int) {
      inventory(warehouseId: $warehouseId, limit: $limit, offset: $offset) {
        sku
        quantity
        qty
        totalQuantity
        availableQuantity
        unitCost
        variant { id sku }
        inventoryItem { id sku totalQuantity }
        product { id name }
      }
    }
    """),
    ("inventory_items_by_warehouse", """
    query InventoryItemsByWarehouse($warehouseId: ID!, $limit: Int, $offset: Int) {
      inventoryItems(warehouseId: $warehouseId, limit: $limit, offset: $offset) {
        sku
        quantity
        qty
        totalQuantity
        availableQuantity
        unitCost
        variant { id sku }
        product { id name }
      }
    }
    """),
]

SCHEMA_DEBUG_QUERY = """
query QueryArgsDebug {
  __schema {
    queryType {
      fields {
        name
        args { name type { name kind ofType { name kind ofType { name kind } } } }
        type { name kind ofType { name kind ofType { name kind } } }
      }
    }
  }
}
"""


def ensure_dirs() -> None:
    os.makedirs("site/data", exist_ok=True)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def gql(query: str, variables: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not TOKEN:
        raise RuntimeError("Falta SKUSAVVY_TOKEN. Agrégalo en GitHub → Settings → Secrets and variables → Actions.")
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "x-token": TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            payload = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="ignore")[:500]
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


def cents(value: Any) -> float:
    n = to_num(value, 0)
    # SKUSavvy normalmente devuelve price en centavos en el proyecto original.
    return round(n / 100, 2)


def clean_status(status: Any) -> str:
    return str(status or "active").lower()


def fetch_variants() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen = set()
    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        data = gql(VARIANTS_QUERY, {"limit": PAGE_SIZE, "offset": offset})
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


def extract_sku(obj: Dict[str, Any]) -> str | None:
    for key in ("sku", "SKU"):
        if obj.get(key):
            return str(obj[key])
    for nested_key in ("variant", "inventoryItem", "productVariant"):
        nested = obj.get(nested_key)
        if isinstance(nested, dict) and nested.get("sku"):
            return str(nested["sku"])
    return None


def extract_qty(obj: Dict[str, Any]) -> float | None:
    for key in ("quantity", "qty", "totalQuantity", "availableQuantity", "onHand", "onHandQuantity", "stock", "stockAvailable"):
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


def fetch_warehouse_inventory(warehouse_id: str) -> Tuple[Dict[str, float], str | None]:
    last_error = None
    for name, query in WAREHOUSE_CANDIDATE_QUERIES:
        try:
            variables = {"id": warehouse_id, "warehouseId": warehouse_id, "limit": PAGE_SIZE, "offset": 0}
            data = gql(query, variables)
            stock_by_sku: Dict[str, float] = {}
            walk_inventory(data, stock_by_sku)
            if stock_by_sku:
                print(f"warehouse inventory OK via {name}: {len(stock_by_sku)} SKUs")
                return stock_by_sku, None
            last_error = f"{name}: query respondió pero no encontré SKU/QTY en el resultado"
        except Exception as exc:  # noqa: BLE001 - queremos probar candidatos
            last_error = f"{name}: {exc}"
            print(f"warehouse candidate failed: {last_error}")
    return {}, last_error


def write_schema_debug() -> None:
    try:
        data = gql(SCHEMA_DEBUG_QUERY)
        fields = data.get("__schema", {}).get("queryType", {}).get("fields", [])
        wanted = [f for f in fields if any(term in f.get("name", "").lower() for term in ["warehouse", "inventory", "location", "bin", "stock"])]
        write_json("site/data/schema-debug.json", {"generatedAt": now_iso(), "fields": wanted})
    except Exception as exc:  # noqa: BLE001
        write_json("site/data/schema-debug.json", {"generatedAt": now_iso(), "error": str(exc)})


def normalize_rows(variants: List[Dict[str, Any]], stock_maps: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    days = 30
    normalized: List[Dict[str, Any]] = []
    for idx, v in enumerate(variants):
        sku = v.get("sku") or (v.get("inventoryItem") or {}).get("sku") or "—"
        total_stock = to_num(v.get("totalQuantity"), to_num((v.get("inventoryItem") or {}).get("totalQuantity"), 0))
        price = cents(v.get("price"))
        avg_daily = to_num(v.get("averageSales"), 0)
        units_sold = round(avg_daily * days, 2)
        product = v.get("product") or {}
        status = clean_status(product.get("status") or ("archived" if product.get("deletedAt") else "active"))
        stock_by_wh = {wid: stock_map.get(str(sku), 0) for wid, stock_map in stock_maps.items()}
        normalized.append({
            "rank": idx + 1,
            "id": v.get("id"),
            "sku": sku,
            "productName": product.get("name") or sku or "Untitled product",
            "category": product.get("type") or "—",
            "productStatus": status,
            "shopifyId": v.get("shopifyId") or product.get("shopifyId") or "—",
            "backorderable": bool(v.get("backorderable")),
            "totalStock": total_stock,
            "stockByWarehouse": stock_by_wh,
            "price": price,
            "unitCost": price,
            "avgDailySales": avg_daily,
            "unitsSold": units_sold,
            "revenueGenerated": round(units_sold * price, 2),
            "marginBySku": None,
        })
    return normalized


def main() -> None:
    ensure_dirs()
    if not TOKEN:
        payload = {
            "generatedAt": now_iso(),
            "error": "Falta SKUSAVVY_TOKEN. Agrégalo como GitHub Secret y corre el workflow otra vez.",
            "warehouses": WAREHOUSES,
            "defaultWarehouseId": DEFAULT_WAREHOUSE_ID,
            "rows": [],
        }
        write_json("site/data/dashboard.json", payload)
        return

    warehouse_errors: Dict[str, str] = {}
    stock_maps: Dict[str, Dict[str, float]] = {}

    write_schema_debug()
    variants = fetch_variants()

    for wh in WAREHOUSES:
        # Solo ponemos stock real cuando el query de warehouse funciona.
        stock, err = fetch_warehouse_inventory(wh["id"])
        if stock:
            stock_maps[wh["id"]] = stock
        elif err:
            warehouse_errors[wh["id"]] = err

    warehouse_status = "ok" if stock_maps else "needs_mapping"
    warning = None
    if not stock_maps:
        warning = (
            "No se pudo leer inventario por warehouse con los queries candidatos. "
            "El dashboard queda publicado, pero el filtro por warehouse mostrará 0 hasta mapear el campo correcto. "
            "Revisa site/data/schema-debug.json generado por GitHub Actions."
        )

    payload = {
        "generatedAt": now_iso(),
        "source": "SKUSavvy GraphQL via GitHub Actions Python",
        "warehouses": WAREHOUSES,
        "defaultWarehouseId": DEFAULT_WAREHOUSE_ID,
        "warehouseDataStatus": warehouse_status,
        "warehouseWarning": warning,
        "warehouseErrors": warehouse_errors,
        "rows": normalize_rows(variants, stock_maps),
    }
    write_json("site/data/dashboard.json", payload)
    print(f"Wrote site/data/dashboard.json rows={len(payload['rows'])} warehouse_status={warehouse_status}")


if __name__ == "__main__":
    main()
