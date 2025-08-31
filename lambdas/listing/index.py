from __future__ import annotations
import os, json, base64, boto3
from boto3.dynamodb.conditions import Attr
from decimal import Decimal
from typing import Optional, Dict, Any, List
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

def _enc(d: Optional[Dict[str, Any]]) -> Optional[str]:
    if not d: return None
    return base64.urlsafe_b64encode(json.dumps(d).encode()).decode()

def _dec(s: Optional[str]) -> Optional[Dict[str, Any]]:
    if not s: return None
    try:
        return json.loads(base64.urlsafe_b64decode(s.encode()).decode())
    except Exception:
        return None

def _first_active_listing_for_product(pid: str, want_stage: str | None):
    fe = Attr("product_id").eq(pid) & Attr("status").eq("active")
    if want_stage:
        fe = fe & Attr("metadata.stage").eq(want_stage)
    resp = tbl_listings.scan(Limit=1, FilterExpression=fe)
    items = resp.get("Items") or []
    return items[0] if items else None

def _infer_type(key: str) -> str:
    k = (key or "").lower()
    if k.endswith((".png",".jpg",".jpeg",".webp",".svg")): return "image"
    if k.endswith(".pdf"):   return "pdf"
    if k.endswith(".docx"):  return "docx"
    if k.endswith(".rtf"):   return "rtf"
    if k.endswith(".txt"):   return "txt"
    if k.endswith((".mp4",".mov",".webm",".gif")): return "video"
    if k.endswith((".obj",".glb",".gltf",".fbx")): return "3d"
    return "file"

def _presign_media(keys: List[str]) -> List[Dict[str, Any]]:
    out = []
    for mk in keys or []:
        try:
            url = presign_get(settings.s3_bucket_assets, mk)
        except Exception:
            url = None
        out.append({"key": mk, "url": url, "type": _infer_type(mk)})
    return out

def handler(event, _ctx):
    qs: Dict[str, str] = event.get("queryStringParameters") or {}
    owner  = qs.get("owner") or qs.get("user_id")  # acepta owner o user_id
    status = qs.get("status")
    limit  = int(qs.get("limit") or "20")
    stage  = qs.get("stage") or os.environ.get("STAGE")
    page_token = qs.get("page_token")
    cursor = _dec(page_token)

    if not owner:
        return _ok({"error": "missing owner/user_id"}, 400)

    fe = Attr("media_keys").size().gt(0) & Attr("owner_id").eq(owner)
    if status:
        fe = fe & Attr("status").eq(status)

    scan_kwargs = {
        "Limit": limit,
        "FilterExpression": fe,
    }
    if cursor:
        scan_kwargs["ExclusiveStartKey"] = cursor

    resp = tbl_products.scan(**scan_kwargs)
    products = resp.get("Items", [])
    last_key = resp.get("LastEvaluatedKey")

    out = []
    for p in products:
        pid = p.get("product_id")
        if not pid:
            continue
        media = _presign_media(p.get("media_keys") or [])
        listing = _first_active_listing_for_product(pid, stage)
        out.append({
            "product": {**p, "media": media},
            "listing": listing
        })

    has_more = bool(last_key)
    next_page_token = _enc(last_key) if has_more else None

    return _ok({
        "items": out,
        "count": len(out),
        "has_more": has_more,
        "next_page_token": next_page_token,
        "applied_filters": {"owner": owner, "status": status, "limit": limit}
    })
