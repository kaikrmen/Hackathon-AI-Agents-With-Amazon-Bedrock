from __future__ import annotations
import base64, json, datetime, io
from typing import Dict, Any, Optional, List, Tuple
from shared.aws import bedrock_runtime
from shared.s3 import put_object
from shared.config import settings

def _vendor_from_model_id(model_id: str) -> str:
    mid = (model_id or "").lower()
    if mid.startswith("amazon.titan-image"):
        return "titan"
    if mid.startswith("stability.stable-diffusion"):
        return "sdxl"
    if "anthropic" in mid or "claude" in mid:
        return "anthropic" 
    return "unknown"

def _payload_titan(prompt: str) -> Dict[str, Any]:
    return {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {"text": prompt},
        "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "standard",
                "height": 1024,
                "width": 1024,
                "cfgScale": 8,
                "seed": 0,
        },
    }

def _payload_sdxl(prompt: str) -> Dict[str, Any]:
    return {
        "text_prompts": [{"text": prompt}],
        "cfg_scale": 8,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30,
    }


def _placeholder_svg_bytes(title: str, subtitle: str) -> bytes:
    t = (title or "KaiKashi DreamForge").replace("&", "&amp;")
    s = (subtitle or "").replace("&", "&amp;")
    svg = f"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#00e5ff"/>
      <stop offset="100%" stop-color="#7c4dff"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#g)"/>
  <g fill="white" font-family="Readex Pro, Inter, system-ui" text-anchor="middle">
    <text x="512" y="480" font-size="64" font-weight="700">{t}</text>
    <text x="512" y="540" font-size="28" opacity="0.85">{s}</text>
  </g>
</svg>"""
    return svg.encode("utf-8")

def _placeholder_obj_bytes(title: str) -> bytes:
    safe_title = (title or "kaikashi").replace("\n", " ")
    obj = f"""# KaiKashi placeholder
# title: {safe_title}
o plane
v -0.5 0.0 -0.5
v  0.5 0.0 -0.5
v  0.5 0.0  0.5
v -0.5 0.0  0.5
vt 0.0 0.0
vt 1.0 0.0
vt 1.0 1.0
vt 0.0 1.0
vn 0.0 1.0 0.0
usemtl default
s off
f 1/1/1 2/2/1 3/3/1
f 1/1/1 3/3/1 4/4/1
"""
    return obj.encode("utf-8")


def _static_min_pdf(text: str) -> bytes:
    pdf = f"""%PDF-1.4
% KaiKashi PDF placeholder
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count 1 /Kids [3 0 R] >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Resources << >>
/Contents 4 0 R >>
endobj
4 0 obj
<< /Length 56 >>
stream
BT
/F1 24 Tf
72 720 Td
({text[:60].replace('(', '[').replace(')', ']')}) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000061 00000 n 
0000000112 00000 n 
0000000250 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
360
%%EOF
"""
    return pdf.encode("latin-1")

def _build_pdf_bytes(title: str, notes: str) -> bytes:
    txt = f"KaiKashi DreamForge — {title} — {datetime.datetime.utcnow().isoformat()}Z — {notes}"
    return _static_min_pdf(txt)

def _build_docx_or_rtf_bytes(brief: Dict[str, Any], design_prompt: str) -> Tuple[bytes, str, str]:
    try:
        from docx import Document 
        doc = Document()
        doc.add_heading('KaiKashi DreamForge - Brief', level=1)
        p = doc.add_paragraph(); p.add_run("Intent: ").bold = True; p.add_run(brief.get("intent",""))
        p = doc.add_paragraph(); p.add_run("Product: ").bold = True; p.add_run(brief.get("product_type",""))
        p = doc.add_paragraph(); p.add_run("Style: ").bold = True; p.add_run(brief.get("style",""))
        p = doc.add_paragraph(); p.add_run("Tags: ").bold = True; p.add_run(", ".join(brief.get("tags", [])))
        doc.add_heading("Design prompt", level=2); doc.add_paragraph(design_prompt)
        doc.add_heading("Notes", level=2); doc.add_paragraph(brief.get("notes",""))
        buf = io.BytesIO(); doc.save(buf)
        return buf.getvalue(), ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    except Exception:
        def esc(s: str) -> str:
            return s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        rtf = (
            r"{\rtf1\ansi"
            r"\b KaiKashi DreamForge - Brief \b0\par "
            r"\b Intent:\b0 " + esc(brief.get("intent","")) + r"\par "
            r"\b Product:\b0 " + esc(brief.get("product_type","")) + r"\par "
            r"\b Style:\b0 " + esc(brief.get("style","")) + r"\par "
            r"\b Tags:\b0 " + esc(", ".join(brief.get("tags", []))) + r"\par "
            r"\b Design prompt:\b0\par " + esc(design_prompt) + r"\par "
            r"\b Notes:\b0\par " + esc(brief.get("notes","")) + r"\par "
            r"}"
        )
        return rtf.encode("utf-8"), ".rtf", "application/rtf"

def _build_txt_bytes(brief: Dict[str, Any], design_prompt: str) -> bytes:
    lines = [
        "KaiKashi DreamForge - Production Brief",
        f"Intent: {brief.get('intent','')}",
        f"Product: {brief.get('product_type','')}",
        f"Style: {brief.get('style','')}",
        f"Tags: {', '.join(brief.get('tags', []))}",
        "",
        "Design Prompt:",
        design_prompt,
        "",
        "Notes:",
        brief.get("notes",""),
    ]
    return ("\n".join(lines)).encode("utf-8")

def _build_gif_bytes_placeholder() -> Optional[bytes]:
    """Genera un GIF simple si Pillow está instalado; de lo contrario, None."""
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    imgs: List[Any] = []
    for i in range(12):
        img = Image.new("RGB", (1024, 1024))
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, 1024, 1024), fill=(10, 10, 20))
        d.ellipse((112+i*2, 112, 912, 912), fill=(10, 150, 230))
        d.ellipse((212, 212, 812-i*2, 812), fill=(120, 80, 255))
        imgs.append(img)
    buf = io.BytesIO()
    imgs[0].save(buf, format="GIF", save_all=True, append_images=imgs[1:], duration=80, loop=0)
    return buf.getvalue()


def _decide_kinds(brief: Dict[str, Any]) -> List[str]:
    """
    Decide los tipos a generar según product_type/intent.
    Retorna una lista con elementos en {"image","pdf","docx","txt","video","3d"}.
    """
    pt = (brief.get("product_type") or "").lower()
    intent = (brief.get("intent") or "").lower()

    img_only = {"poster", "tshirt", "sticker", "children_book_cover",
                "book_cover", "cover", "ebook_cover", "mockup", "image"}
    doc_only = {"book", "ebook", "educational_content", "story",
                "children_book", "novel", "document", "libro"}
    vid_only = {"video", "clip", "animation"}
    model_only = {"3d_model", "3d_printable", "model3d", "3d"}

    if pt in img_only or "image" in intent:
        return ["image"]
    if pt in doc_only or ("book" in intent and pt == "") or ("libro" in intent and pt == ""):
        return ["pdf", "docx", "txt"]
    if pt in vid_only or "video" in pt or "video" in intent or "gif" in intent:
        return ["video"]
    if pt in model_only or "3d" in pt or "3d" in intent:
        return ["3d"]

    return ["image"] 


def generate_assets(design_prompt: str, brief: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    outputs: Dict[str, Any] = {}
    model_id = getattr(settings, "bedrock_image_model_id", "")
    vendor = _vendor_from_model_id(model_id)
    base = f"assets/{user_id}/generated/{brief.get('product_type','generic')}_{brief.get('intent','idea')}"
    errors: Dict[str, str] = {}
    media_keys: List[str] = []
    kinds = _decide_kinds(brief)

    # ---------- Image ----------
    if "image" in kinds:
        image_key: Optional[str] = None
        try:
            if vendor in ("titan", "sdxl"):
                rt = bedrock_runtime()
                body = _payload_titan(design_prompt) if vendor == "titan" else _payload_sdxl(design_prompt)
                res = rt.invoke_model(modelId=model_id, body=json.dumps(body))
                payload = json.loads(res["body"].read())
                if vendor == "titan":
                    img_b64 = (payload.get("images") or [None])[0] or payload.get("image_base64")
                else:
                    artifacts = payload.get("artifacts", [])
                    img_b64 = artifacts[0].get("base64") if artifacts else None
                if img_b64:
                    raw = base64.b64decode(img_b64)
                    image_key = f"{base}.png"
                    put_object(settings.s3_bucket_assets, image_key, raw, "image/png")
                else:
                    errors["image"] = "Modelo de imagen no devolvió salida base64."
            elif vendor == "anthropic":
                errors["image"] = "El modelo configurado es Anthropic/Claude (no genera imágenes)."
            else:
                errors["image"] = f"Modelo '{model_id}' no reconocido como generador de imagen."
        except Exception as e:
            errors["image"] = f"{type(e).__name__}: {e}"

        if not image_key:
            title = brief.get("intent") or "Diseño generado"
            subtitle = (brief.get("style") or "")[:80]
            svg_bytes = _placeholder_svg_bytes(title, subtitle)
            ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            image_key = f"{base}_placeholder_{ts}.svg"
            put_object(settings.s3_bucket_assets, image_key, svg_bytes, "image/svg+xml")

        outputs["image_key"] = image_key
        media_keys.append(image_key)

    # ---------- DOC ----------
    if "pdf" in kinds:
        try:
            pdf_bytes = _build_pdf_bytes(
                title=brief.get("intent", "Producto creativo"),
                notes=brief.get("notes", "")
            )
            pdf_key = f"{base}.pdf"
            put_object(settings.s3_bucket_assets, pdf_key, pdf_bytes, "application/pdf")
            outputs["pdf_key"] = pdf_key
            media_keys.append(pdf_key)
        except Exception as e:
            errors["pdf"] = f"{type(e).__name__}: {e}"

    if "docx" in kinds:
        try:
            doc_bytes, doc_suffix, doc_ct = _build_docx_or_rtf_bytes(brief, design_prompt)
            doc_key = f"{base}{doc_suffix}"
            put_object(settings.s3_bucket_assets, doc_key, doc_bytes, doc_ct)
            if doc_suffix == ".docx":
                outputs["docx_key"] = doc_key
            else:
                outputs["rtf_key"] = doc_key
            media_keys.append(doc_key)
        except Exception as e:
            errors["doc"] = f"{type(e).__name__}: {e}"

    if "txt" in kinds:
        try:
            txt_bytes = _build_txt_bytes(brief, design_prompt)
            txt_key = f"{base}.txt"
            put_object(settings.s3_bucket_assets, txt_key, txt_bytes, "text/plain; charset=utf-8")
            outputs["text_key"] = txt_key
            media_keys.append(txt_key)
        except Exception as e:
            errors["text"] = f"{type(e).__name__}: {e}"

    # ---------- Video (GIF placeholder) ----------
    if "video" in kinds:
        try:
            gif_bytes = _build_gif_bytes_placeholder()
            if gif_bytes:
                gif_key = f"{base}.gif"
                put_object(settings.s3_bucket_assets, gif_key, gif_bytes, "image/gif")
                outputs["video_key"] = gif_key
                media_keys.append(gif_key)
            else:
                errors["video"] = "No se generó GIF (falta Pillow)."
        except Exception as e:
            errors["video"] = f"{type(e).__name__}: {e}"

    # ---------- 3D ----------
    if "3d" in kinds:
        try:
            obj_bytes = _placeholder_obj_bytes(brief.get("intent",""))
            obj_key = f"{base}.obj"
            put_object(settings.s3_bucket_assets, obj_key, obj_bytes, "text/plain")
            outputs["model3d_key"] = obj_key
            media_keys.append(obj_key)
        except Exception as e:
            errors["3d"] = f"{type(e).__name__}: {e}"

    outputs["kinds"] = kinds
    outputs["media_keys"] = media_keys
    outputs["package"] = {
        "design_prompt": design_prompt,
        "brief": brief,
        "suggested_title": brief.get("intent", "Producto creativo"),
        "suggested_description": f"Generado automáticamente a partir de tu idea: {brief.get('notes','')}",
    }
    if errors:
        outputs["errors"] = errors
    return outputs
