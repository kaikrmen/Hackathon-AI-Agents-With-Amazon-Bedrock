from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Product:
    product_id: str
    owner_id: str
    title: str
    description: str
    media_keys: List[str] = field(default_factory=list)
    status: str = "draft" 

@dataclass
class Listing:
    listing_id: str
    product_id: str
    price_cents: int
    currency: str = "USD"
    status: str = "active" 
    metadata: Dict[str, Any] = field(default_factory=dict)
