from __future__ import annotations
import uuid, time
from typing import Dict, Any, List, Optional, Tuple
from boto3.dynamodb.conditions import Attr
from .aws import dynamodb_resource
from .config import settings

ddb = dynamodb_resource()
tbl_products = ddb.Table(settings.ddb_products)
tbl_listings = ddb.Table(settings.ddb_listings)
tbl_convs    = ddb.Table(settings.ddb_conversations)
tbl_msgs     = ddb.Table(settings.ddb_messages)

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def put_product(item: Dict[str, Any]): tbl_products.put_item(Item=item)
def get_product(product_id: str) -> Dict[str, Any] | None:
    r = tbl_products.get_item(Key={"product_id": product_id}); return r.get("Item")

def put_listing(item: Dict[str, Any]): tbl_listings.put_item(Item=item)

def _now_ms_str() -> str: return f"{int(time.time() * 1000):013d}"

def ensure_conversation(conversation_id: str, user_id: str, model_id: str, title: str="Nueva conversación"):
    now_str = _now_ms_str()
    item = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "started_at": now_str,
        "last_message_at": now_str,
        "title": title,
        "status": "active",
        "model_id": model_id,
        "meta": {},
    }
    try:
        tbl_convs.put_item(Item=item, ConditionExpression="attribute_not_exists(conversation_id)")
    except Exception:
        pass
    return item

def touch_conversation(conversation_id: str):
    now_str = _now_ms_str()
    tbl_convs.update_item(
        Key={"conversation_id": conversation_id},
        UpdateExpression="SET last_message_at = :t",
        ExpressionAttributeValues={":t": now_str},
    )

def put_message(conversation_id: str, role: str, content: str, media_keys=None, tool_calls=None, message_id=None):
    message_id = message_id or new_id("msg")
    created_at = _now_ms_str()
    item = {
        "conversation_id": conversation_id,
        "created_at": created_at,
        "message_id": message_id,
        "role": role,
        "content": (content or "")[:4000],
        "media_keys": media_keys or [],
        "tool_calls": tool_calls or [],
    }
    tbl_msgs.put_item(Item=item)
    touch_conversation(conversation_id)
    return item

def list_products_by_owner(
    owner_id: str,
    *,
    limit: int = 20,
    cursor: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
    require_media: bool = True,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Escanea products del owner con paginación.
    - Si require_media=True, filtra productos con media_keys no vacía (lado servidor).
    - Si status viene (e.g. 'draft' | 'active'), también filtra por status.
    Devuelve (items, LastEvaluatedKey).
    """
    scan_kwargs: Dict[str, Any] = {"Limit": limit}
    fe = Attr("owner_id").eq(owner_id)
    if status:
        fe = fe & Attr("status").eq(status)
    if require_media:
        fe = fe & Attr("media_keys").size().gt(0)  # media_keys con al menos 1 elemento
    scan_kwargs["FilterExpression"] = fe
    if cursor:
        scan_kwargs["ExclusiveStartKey"] = cursor

    resp = tbl_products.scan(**scan_kwargs)
    return resp.get("Items", []), resp.get("LastEvaluatedKey")
