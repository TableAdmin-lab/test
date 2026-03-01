from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

app = FastAPI(title="Restaurant Margin Intelligence V1")

# In-memory V1 store (replace with DB in next step)
POS_ITEMS: Dict[str, str] = {}
POS_SALES: List[dict] = []
INGREDIENTS: Dict[str, dict] = {}
INVOICE_LINES: List[dict] = []
RECIPES: Dict[str, List[dict]] = {}
MARGIN_SNAPSHOTS: List[dict] = []


class RecipeIngredient(BaseModel):
    ingredient_name: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    uom: str = Field(min_length=1)


class RecipeLiteRequest(BaseModel):
    menu_item_name: str = Field(min_length=1)
    ingredients: List[RecipeIngredient] = Field(min_length=1)


class MarginRow(BaseModel):
    menu_item_name: str
    quantity_sold: float
    avg_selling_price_zar: float
    cogs_per_item_zar: float
    margin_per_item_zar: float
    margin_pct: float


def _parse_csv(content: bytes) -> List[dict]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = [r for r in reader]
    if not rows:
        raise HTTPException(status_code=400, detail="CSV contains no rows")
    return rows


def _latest_ingredient_unit_costs() -> Dict[str, float]:
    latest: Dict[str, tuple[date, float]] = {}
    for line in INVOICE_LINES:
        ing = line["ingredient_name"].strip().lower()
        dt = line["invoice_date"]
        cost = line["unit_cost_zar"]
        if ing not in latest or dt >= latest[ing][0]:
            latest[ing] = (dt, cost)
    return {k: v[1] for k, v in latest.items()}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest/pos-sales/csv")
async def ingest_pos_sales_csv(file: UploadFile = File(...), location: str = Form("default")) -> dict:
    rows = _parse_csv(await file.read())
    required = {"date", "pos_item_id", "pos_item_name", "quantity_sold", "gross_sales_zar"}
    missing = required - set(rows[0].keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {sorted(missing)}")

    inserted = 0
    for row in rows:
        try:
            sale_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            qty = float(row["quantity_sold"])
            gross = float(row["gross_sales_zar"])
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid row values: {row}") from exc

        pos_item_id = row["pos_item_id"].strip()
        pos_name = row["pos_item_name"].strip()
        POS_ITEMS[pos_item_id] = pos_name
        POS_SALES.append(
            {
                "date": sale_date,
                "location": location,
                "pos_item_id": pos_item_id,
                "pos_item_name": pos_name,
                "quantity_sold": qty,
                "gross_sales_zar": gross,
            }
        )
        inserted += 1

    return {"inserted": inserted, "location": location}


@app.post("/ingest/invoices/csv")
async def ingest_invoice_csv(file: UploadFile = File(...), supplier_name: str = Form(...)) -> dict:
    rows = _parse_csv(await file.read())
    required = {"invoice_date", "ingredient_name", "quantity", "uom", "line_total_zar"}
    missing = required - set(rows[0].keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {sorted(missing)}")

    inserted = 0
    for row in rows:
        try:
            invoice_date = datetime.strptime(row["invoice_date"], "%Y-%m-%d").date()
            qty = float(row["quantity"])
            line_total = float(row["line_total_zar"])
            if qty <= 0:
                raise ValueError("quantity must be > 0")
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid row values: {row}") from exc

        ing_name = row["ingredient_name"].strip()
        unit_cost = line_total / qty
        INGREDIENTS.setdefault(ing_name.lower(), {"name": ing_name, "uom": row["uom"].strip()})
        INVOICE_LINES.append(
            {
                "supplier_name": supplier_name,
                "invoice_date": invoice_date,
                "ingredient_name": ing_name,
                "quantity": qty,
                "uom": row["uom"].strip(),
                "line_total_zar": line_total,
                "unit_cost_zar": unit_cost,
            }
        )
        inserted += 1

    return {"inserted": inserted, "supplier_name": supplier_name}


@app.post("/menu-items/recipe-lite")
def create_recipe_lite(payload: RecipeLiteRequest) -> dict:
    RECIPES[payload.menu_item_name.strip().lower()] = [ing.model_dump() for ing in payload.ingredients]
    return {"menu_item_name": payload.menu_item_name, "ingredient_count": len(payload.ingredients)}


@app.post("/metrics/margins/recompute")
def recompute_margins() -> dict:
    if not POS_SALES:
        raise HTTPException(status_code=400, detail="No POS sales data found")
    if not INVOICE_LINES:
        raise HTTPException(status_code=400, detail="No invoice cost data found")

    latest_cost = _latest_ingredient_unit_costs()
    sales_by_item = defaultdict(lambda: {"qty": 0.0, "gross": 0.0, "name": ""})
    for sale in POS_SALES:
        key = sale["pos_item_name"].strip().lower()
        sales_by_item[key]["qty"] += sale["quantity_sold"]
        sales_by_item[key]["gross"] += sale["gross_sales_zar"]
        sales_by_item[key]["name"] = sale["pos_item_name"]

    snapshot_time = datetime.utcnow().isoformat()
    rows = []
    for key, aggregate in sales_by_item.items():
        if key not in RECIPES:
            continue

        cogs = 0.0
        missing_ingredients = []
        for ing in RECIPES[key]:
            ing_key = ing["ingredient_name"].strip().lower()
            if ing_key not in latest_cost:
                missing_ingredients.append(ing["ingredient_name"])
                continue
            cogs += float(ing["quantity"]) * latest_cost[ing_key]

        if missing_ingredients:
            continue

        avg_price = aggregate["gross"] / aggregate["qty"] if aggregate["qty"] else 0.0
        margin = avg_price - cogs
        margin_pct = (margin / avg_price) if avg_price else 0.0
        row = {
            "snapshot_at": snapshot_time,
            "menu_item_name": aggregate["name"],
            "quantity_sold": round(aggregate["qty"], 2),
            "avg_selling_price_zar": round(avg_price, 2),
            "cogs_per_item_zar": round(cogs, 2),
            "margin_per_item_zar": round(margin, 2),
            "margin_pct": round(margin_pct, 4),
        }
        rows.append(row)

    MARGIN_SNAPSHOTS.clear()
    MARGIN_SNAPSHOTS.extend(rows)
    return {"snapshot_at": snapshot_time, "items_computed": len(rows)}


@app.get("/metrics/margins", response_model=List[MarginRow])
def get_margins() -> List[MarginRow]:
    return [
        MarginRow(
            menu_item_name=row["menu_item_name"],
            quantity_sold=row["quantity_sold"],
            avg_selling_price_zar=row["avg_selling_price_zar"],
            cogs_per_item_zar=row["cogs_per_item_zar"],
            margin_per_item_zar=row["margin_per_item_zar"],
            margin_pct=row["margin_pct"],
        )
        for row in MARGIN_SNAPSHOTS
    ]
