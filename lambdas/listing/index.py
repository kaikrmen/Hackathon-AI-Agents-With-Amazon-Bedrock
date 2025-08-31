from __future__ import annotations
import os, json, boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb")
tbl_products = dynamodb.Table(os.environ["DDB_PRODUCTS"])
tbl_listings = dynamodb.Table(os.environ["DDB_LISTINGS"])

def _ok(b, c=200):
    return {"statusCode": c, "headers":{"Content-Type":"application/json"},
            "body": json.dumps(b, ensure_ascii=False)}

def handler(event, _ctx):
    qs = event.get("queryStringParameters") or {}
    owner = qs.get("owner")
    status = qs.get("status")
    limit = int(qs.get("limit") or "20")

    scan_kwargs = {"Limit": limit*2}
    if status:
        try:
            scan_kwargs["FilterExpression"] = Attr("status").eq(status)
        except AttributeError:
            scan_kwargs["FilterExpression"] = Attr("status") == status

    resp = tbl_listings.scan(**scan_kwargs)
    items = resp.get("Items", [])

    product_ids = [it["product_id"] for it in items if "product_id" in it]
    if not product_ids:
        return _ok({"items": [], "count": 0})

    client = dynamodb.meta.client
    resp2 = client.batch_get_item(RequestItems={
        os.environ["DDB_PRODUCTS"]: {"Keys":[{"product_id": pid} for pid in product_ids]}
    })
    prods = {p["product_id"]: p for p in resp2["Responses"].get(os.environ["DDB_PRODUCTS"], [])}

    out = []
    for li in items:
        p = prods.get(li["product_id"])
        if not p: continue
        if owner and p.get("owner_id") != owner: continue
        media = p.get("media_keys") or []
        if not media: continue
        out.append({"listing": li, "product": p})

        if len(out) >= limit: break

    return _ok({"items": out, "count": len(out)})
