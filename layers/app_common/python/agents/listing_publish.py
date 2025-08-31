from __future__ import annotations
from typing import Dict, Any, List, Optional
from shared.dynamo import put_product, put_listing, new_id
from shared.config import settings

def create_product_and_listing(
    user_id: str,
    package: Dict[str, Any],
    media_keys: Optional[List[str]] = None,
    price_cents: int = 1500
) -> Dict[str, str]:
    product_id = new_id("prd")
    item = {
        "product_id": product_id,
        "owner_id": user_id,
        "title": package.get("suggested_title", "Producto creativo"),
        "description": package.get("suggested_description", ""),
        "media_keys": media_keys or [],
        "status": "draft",
    }
    put_product(item)

    listing_id = new_id("lst")
    listing = {
        "listing_id": listing_id,
        "product_id": product_id,
        "price_cents": price_cents,
        "currency": "USD",
        "status": "active",
        "metadata": {"stage": settings.stage},
    }
    put_listing(listing)
    return {"product_id": product_id, "listing_id": listing_id}
