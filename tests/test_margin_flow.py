from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_end_to_end_margin_flow():
    pos_csv = """date,pos_item_id,pos_item_name,quantity_sold,gross_sales_zar
2026-02-01,1,Chicken Burger,10,850
2026-02-01,2,Fries,20,500
"""
    r = client.post(
        "/ingest/pos-sales/csv",
        data={"location": "jhb-1"},
        files={"file": ("pos.csv", BytesIO(pos_csv.encode("utf-8")), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["inserted"] == 2

    invoice_csv = """invoice_date,ingredient_name,quantity,uom,line_total_zar
2026-02-01,chicken_patty,50,each,1500
2026-02-01,burger_bun,50,each,500
2026-02-01,fries_portion,100,each,1200
"""
    r = client.post(
        "/ingest/invoices/csv",
        data={"supplier_name": "Supplier A"},
        files={"file": ("invoice.csv", BytesIO(invoice_csv.encode("utf-8")), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["inserted"] == 3

    r = client.post(
        "/menu-items/recipe-lite",
        json={
            "menu_item_name": "Chicken Burger",
            "ingredients": [
                {"ingredient_name": "chicken_patty", "quantity": 1, "uom": "each"},
                {"ingredient_name": "burger_bun", "quantity": 1, "uom": "each"},
            ],
        },
    )
    assert r.status_code == 200

    r = client.post(
        "/menu-items/recipe-lite",
        json={
            "menu_item_name": "Fries",
            "ingredients": [
                {"ingredient_name": "fries_portion", "quantity": 1, "uom": "each"},
            ],
        },
    )
    assert r.status_code == 200

    r = client.post("/metrics/margins/recompute")
    assert r.status_code == 200
    assert r.json()["items_computed"] == 2

    r = client.get("/metrics/margins")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    burger = next(x for x in data if x["menu_item_name"] == "Chicken Burger")
    assert burger["avg_selling_price_zar"] == 85.0
    assert burger["cogs_per_item_zar"] == 40.0
    assert burger["margin_per_item_zar"] == 45.0
