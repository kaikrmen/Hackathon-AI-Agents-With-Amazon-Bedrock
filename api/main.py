from __future__ import annotations
import base64
import os, uuid, json
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Query, UploadFile, File, Form, Depends, HTTPException
from pydantic import BaseModel
from shared.config import settings
from shared.dynamo import ensure_conversation, list_products_by_owner, put_message
from shared.s3 import put_object, presign_get
from agents.dream_interpret import interpret_dream
from agents.design_generate import generate_assets
from agents.listing_publish import create_product_and_listing

app = FastAPI(title="KaiKashi Dream API", version="1.0.0")

# Auth mínima local: para prod reemplazar por verificación de Cognito
def get_user_id(auth_bypass: bool = getattr(settings, "auth_bypass", True)) -> str:
    return "user_dev_001" if auth_bypass else "user_unknown"


def _enc(d: Optional[Dict[str, Any]]) -> Optional[str]:
    if not d: return None
    return base64.urlsafe_b64encode(json.dumps(d).encode()).decode()

def _dec(s: Optional[str]) -> Optional[Dict[str, Any]]:
    if not s: return None
    try:
        return json.loads(base64.urlsafe_b64decode(s.encode()).decode())
    except Exception:
        return None

@app.get("/products")
def products_feed(
    owner: Optional[str] = Query(None, description="Por defecto: usuario actual"),
    limit: int = Query(20, ge=1, le=100),
    page_token: Optional[str] = Query(None, description="Cursor base64"),
    status: Optional[str] = Query(None, description="Filtra por status del producto (ej: draft)"),
    user_id: str = Depends(get_user_id),
):
    """
    Devuelve productos del owner (por defecto, el usuario autenticado) con media y URLs presignadas.
    Estructura por item:
      {
        product_id, title, description, status, owner_id,
        media: [{key, url, type}],  # type inferido por extensión
      }
    """
    owner_id = owner or user_id
    cursor = _dec(page_token)
    items, last_key = list_products_by_owner(
        owner_id=owner_id, limit=limit, cursor=cursor, status=status, require_media=True
    )

    def infer_type(key: str) -> str:
        k = key.lower()
        if k.endswith(".png") or k.endswith(".jpg") or k.endswith(".jpeg") or k.endswith(".svg"): return "image"
        if k.endswith(".pdf"): return "pdf"
        if k.endswith(".docx"): return "docx"
        if k.endswith(".txt"): return "txt"
        if k.endswith(".gif"): return "video"
        if k.endswith(".obj") or k.endswith(".glb") or k.endswith(".gltf") or k.endswith(".fbx"): return "3d"
        return "file"

    out: List[Dict[str, Any]] = []
    for p in items:
        media_keys = p.get("media_keys") or []
        media = []
        for mk in media_keys:
            try:
                url = presign_get(settings.s3_bucket_assets, mk)
            except Exception:
                url = None
            media.append({"key": mk, "url": url, "type": infer_type(mk)})
        out.append({
            "product_id": p["product_id"],
            "title": p.get("title",""),
            "description": p.get("description",""),
            "status": p.get("status","draft"),
            "owner_id": p.get("owner_id"),
            "media": media,
        })

    return {
        "items": out,
        "count": len(out),
        "next_page_token": _enc(last_key),
        "applied_filters": {"owner": owner_id, "status": status, "limit": limit},
    }

@app.get("/ping")
def ping():
    return {
        "ok": True,
        "region": settings.aws_region,
        "model": settings.bedrock_text_model_id,
        "stage": getattr(settings, "stage", "dev"),
    }

@app.post("/create")
async def create_from_idea(
    q: str = Form(..., description="Idea/Sueño del usuario en texto"),
    price_cents: int = Form(1500, description="Precio en centavos"),
    file: Optional[UploadFile] = File(
        None, description="Archivo opcional (imagen/pdf/audio/etc.)"
    ),
    conversation_title: Optional[str] = Form(
        None, description="Título opcional para la conversación"
    ),
    user_id: str = Depends(get_user_id),
):
    """
    Pipeline end-to-end:
      1) (opcional) sube archivo a S3.
      2) crea conversación y guarda mensaje del usuario.
      3) interpreta sueño/idea -> brief (Bedrock vía Strands Agents).
      4) genera assets (intenta imagen con Bedrock Image) y sube a S3.
      5) crea producto + listing en DynamoDB.
      6) registra todos los pasos en la conversación.
      7) responde con todo el paquete (ids, urls, brief, etc).
    """
  
    uploaded_key: Optional[str] = None
    uploaded_ct: Optional[str] = None
    if file:
        uploaded_ct = file.content_type or "application/octet-stream"
        safe_name = file.filename or "upload.bin"
        key = f"uploads/{user_id}/{uuid.uuid4().hex}_{safe_name}"
        content = await file.read()
        try:
            put_object(settings.s3_bucket_uploads, key, content, uploaded_ct)
            uploaded_key = key
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error subiendo archivo: {e}")

  
    conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
    try:
        ensure_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            model_id=settings.bedrock_text_model_id,
            title=conversation_title or (q[:64] + ("…" if len(q) > 64 else "")),
        )
        put_message(
            conversation_id,
            role="user",
            content=q,
            media_keys=[uploaded_key] if uploaded_key else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando conversación: {e}")


    try:
        brief = interpret_dream(q)
        put_message(conversation_id, role="assistant", content=json.dumps(brief, ensure_ascii=False))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interpretando idea: {e}")

  
    try:
        design = generate_assets(
            design_prompt=brief.get("design_prompt", q),
            brief=brief,
            user_id=user_id,
        )
        image_key = design.get("image_key")
        if image_key:
            put_message(
                conversation_id,
                role="assistant",
                content=json.dumps({"design": {**design, "image_url": None}}, ensure_ascii=False),
                media_keys=[image_key],
            )
        else:
            put_message(
                conversation_id,
                role="assistant",
                content=json.dumps({"design": design}, ensure_ascii=False),
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando assets: {e}")

    image_key = design.get("image_key")
    try:
        all_keys = []
        for k in ["image_key","pdf_key","docx_key","text_key","video_key","model3d_key"]:
            if design.get(k):
                all_keys.append(design[k])
        
        ids = create_product_and_listing(
            user_id=user_id,
            package=design["package"],
            media_keys=all_keys,   
            price_cents=price_cents,
        )
        put_message(conversation_id, role="assistant", content=json.dumps({"ids": ids}, ensure_ascii=False))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando producto/listing: {e}")

    image_url: Optional[str] = None
    try:
        if image_key:
            image_url = presign_get(settings.s3_bucket_assets, image_key)
    except Exception:
        image_url = None


    return {
        "conversation_id": conversation_id,
        "uploaded": {
            "key": uploaded_key,
            "content_type": uploaded_ct,
        },
        "brief": brief,
        "design": {
            "image_key": image_key,
            "image_url": image_url,
            "errors": design.get("image_error"),
            "package": design.get("package"),
        },
        "ids": ids, 
        "price_cents": price_cents,
        "currency": "USD",
    }
