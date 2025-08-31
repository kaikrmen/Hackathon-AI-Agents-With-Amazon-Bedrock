from __future__ import annotations
import os, json, boto3
from boto3.dynamodb.conditions import Attr
from shared.config import settings

ddb = boto3.resource("dynamodb")
tbl_products = ddb.Table(settings.ddb_products)
tbl_listings = ddb.Table(settings.ddb_listings)

def _ok(b, c=200):
    return {
        "statusCode": c,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(b, ensure_ascii=False),
    }

def _first_active_listing_for_product(pid: str, want_stage: str | None):
    fe = Attr("product_id").eq(pid) & Attr("status").eq("active")
    if want_stage:
        fe = fe & Attr("metadata.stage").eq(want_stage)

    resp = tbl_listings.scan(
        Limit=1,
        FilterExpression=fe,
    )
    items = resp.get("Items") or []
    return items[0] if items else None

def handler(event, _ctx):
    qs = event.get("queryStringParameters") or {}
    owner = qs.get("owner")
    status = qs.get("status")
    limit = int(qs.get("limit") or "20")
    stage = qs.get("stage") or os.environ.get("STAGE")

    fe = Attr("media_keys").size().gt(0)  
    if owner:
        fe = fe & Attr("owner_id").eq(owner)
    if status:
        fe = fe & Attr("status").eq(status)

    resp = tbl_products.scan(
        Limit=max(50, limit * 3),
        FilterExpression=fe,
    )
    products = resp.get("Items", [])

    out = []
    for p in products:
        pid = p.get("product_id")
        if not pid:
            continue
        listing = _first_active_listing_for_product(pid, stage)
        out.append({"product": p, "listing": listing})
        if len(out) >= limit:
            break

    return _ok({"items": out, "count": len(out)})
