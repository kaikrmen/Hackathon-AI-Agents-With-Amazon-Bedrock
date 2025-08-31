from __future__ import annotations
import os, json, boto3
from boto3.dynamodb.conditions import Attr
from decimal import Decimal
from shared.config import settings
from shared.s3 import presign_get

ddb = boto3.resource("dynamodb")
tbl_products = ddb.Table(settings.ddb_products)
tbl_listings = ddb.Table(settings.ddb_listings)

def _to_jsonable(x):
    if isinstance(x, list):  return [_to_jsonable(v) for v in x]
    if isinstance(x, dict):  return {k: _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, Decimal):
        return int(x) if x == x.to_integral_value() else float(x)
    return x

def _ok(b, c=200):
    return {"statusCode": c, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(_to_jsonable(b), ensure_ascii=False)}

def _first_active_listing_for_product(pid: str, want_stage: str | None):
    fe = Attr("product_id").eq(pid) & Attr("status").eq("active")
    if want_stage:
        fe = fe & Attr("metadata.stage").eq(want_stage)
    resp = tbl_listings.scan(Limit=1, FilterExpression=fe)
    items = resp.get("Items") or []
    return items[0] if items else None

def _infer_type(key: str) -> str:
    k = (key or "").lower()
    if k.endswith((".png", ".jpg", ".jpeg", ".webp", ".svg")): return "image"
    if k.endswith(".pdf"):   return "pdf"
    if k.endswith(".docx"):  return "docx"
    if k.endswith(".rtf"):   return "rtf"
    if k.endswith(".txt"):   return "txt"
    if k.endswith((".mp4", ".mov", ".webm", ".gif")): return "video"
    if k.endswith((".obj", ".glb", ".gltf", ".fbx")): return "3d"
    return "file"

def _presign_media(keys: list[str]) -> list[dict]:
    out = []
    for mk in keys or []:
        try:
            url = presign_get(settings.s3_bucket_assets, mk)
        except Exception:
            url = None
        out.append({"key": mk, "url": url, "type": _infer_type(mk)})
    return out

def handler(event, _ctx):
    qs     = event.get("queryStringParameters") or {}
    owner  = qs.get("owner")
    status = qs.get("status")
    limit  = int(qs.get("limit") or "20")
    stage  = qs.get("stage") or os.environ.get("STAGE")

    fe = Attr("media_keys").size().gt(0)
    if owner:  fe = fe & Attr("owner_id").eq(owner)
    if status: fe = fe & Attr("status").eq(status)

    resp = tbl_products.scan(Limit=max(50, limit*3), FilterExpression=fe)
    products = resp.get("Items", [])

    out = []
    for p in products:
        pid = p.get("product_id")
        if not pid: 
            continue

        # presign media del producto
        media_keys = p.get("media_keys") or []
        media = _presign_media(media_keys)

        listing = _first_active_listing_for_product(pid, stage)

        out.append({
            "product": {
                **p,
                "media": media, 
            },
            "listing": listing
        })

        if len(out) >= limit:
            break

    return _ok({"items": out, "count": len(out)})
