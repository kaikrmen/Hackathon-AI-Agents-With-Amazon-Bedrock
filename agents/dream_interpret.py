from __future__ import annotations
from typing import Dict, Any, List
from .factory import make_agent

SYSTEM_PROMPT = r"""
ROLE
You are KaiKashi, an ultra-focused brief generator that converts short user ideas/dreams into a compact production brief. You DO NOT chit-chat. You ONLY output a single, valid JSON object.

LANGUAGE
- Detect the user language (Spanish or English) and produce values (style, notes, design_prompt) in that language.
- If mixed, prefer the majority language. Default to Spanish if unclear.

SCOPE
- Extract EXACTLY these keys: intent, style, product_type, tags, design_prompt, notes.
- No marketing copy, no greetings, no explanations outside JSON. No markdown/backticks.
- If missing data: infer minimal, reasonable defaults.

OUTPUT FORMAT (STRICT)
Return ONE JSON object with EXACT keys:
{
  "intent": "<string>",
  "style": "<string>",
  "product_type": "<string>",
  "tags": ["<string>", "..."],
  "design_prompt": "<string>",
  "notes": "<string>"
}

CONSTRAINTS
- product_type: one of (poster|tshirt|mug|book|ebook|audiobook|3d_model|3d_printable|nft|sticker|mockup|bundle|other|clarify)
- style: short, comma-separated (3–8 descriptors), not a paragraph.
- tags: 3–8 generic tokens, lowercase where possible, no brands/IP.
- design_prompt: concise but specific (~40–120 words), directly usable by generative models; include composition cues (subject/scene/mood/palette/camera-or-art hints). No references to “the user said”.
- notes: 1–3 brief sentences (e.g., audience, CMYK/POD constraints, negative prompts).
- Avoid copyrighted brands/characters.

FILES
- If the user likely references files: do NOT mention paths. Instead put a short hint in notes:
  - ES: "Usar referencia si está disponible; no copiar logotipos ni marcas."
  - EN: "Use reference if available; do not copy logos or brands."

SAFETY
- If unsafe (hate/sexual/illegal/self-harm), return a CLARIFICATION JSON:
  { "intent":"clarify","style":"","product_type":"","tags":[],"design_prompt":"","notes":"<brief request for a safer idea in the user's language>" }

BEHAVIOR: CLARIFICATION
If greeting or non-actionable input:
Return:
{ "intent":"clarify","style":"","product_type":"","tags":[],"design_prompt":"","notes":"<short clarification in user's language with 1–2 concrete examples>" }

LENGTH DISCIPLINE
- style: 3–8 tokens, tags: 3–8 tokens, design_prompt: ~40–120 words, notes: 1–3 sentences.

JSON ONLY
- Output MUST be a single valid JSON object. No extra text.
"""

_agent = make_agent(SYSTEM_PROMPT)

_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "style": {"type": "string"},
        "product_type": {
            "type": "string",
            "enum": [
                "poster","tshirt","mug","book","ebook","audiobook",
                "3d_model","3d_printable","nft","sticker","mockup",
                "bundle","other","clarify"
            ]
        },
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 12},
        "design_prompt": {"type": "string"},
        "notes": {"type": "string"}
    },
    "required": ["intent","style","product_type","tags","design_prompt","notes"]
}


_CANON_PT = {
    "poster":"poster","tshirt":"tshirt","tee":"tshirt","polera":"tshirt","playera":"tshirt",
    "mug":"mug","cup":"mug",
    "book":"book","libro":"book","ebook":"ebook","e-book":"ebook",
    "audiobook":"audiobook","audio book":"audiobook",
    "3d_model":"3d_model","3d-model":"3d_model","model3d":"3d_model","3d":"3d_model",
    "3d_printable":"3d_printable","printable":"3d_printable",
    "sticker":"sticker","stickers":"sticker",
    "mockup":"mockup","bundle":"bundle",
    "cover":"mockup","book_cover":"mockup","children_book_cover":"mockup",
    "other":"other","clarify":"clarify",
}

def _detect_lang(text: str) -> str:
    t = (text or "").lower()
    en_hits = sum(w in t for w in [" the "," and "," with "," poster","book","cover","make","create","hi","hello"])
    es_hits = sum(w in t for w in [" el "," la "," y "," con "," póster","poster","libro","portada","crear","hola","buenas"])
    if en_hits > es_hits: return "EN"
    if es_hits > en_hits: return "ES"
    return "ES"

def _clip_words(s: str, mn: int, mx: int) -> str:
    ws = s.split()
    if len(ws) < mn: return s
    if len(ws) > mx: ws = ws[:mx]
    return " ".join(ws)

def _norm_product_type(pt: str, intent: str) -> str:
    c = _CANON_PT.get((pt or "").lower())
    if c: return c
    it = (intent or "").lower()
    if any(k in it for k in ["poster","póster"]): return "poster"
    if any(k in it for k in ["book","libro","ebook"]): return "book"
    if "sticker" in it: return "sticker"
    if "video" in it or "clip" in it or "gif" in it: return "mockup"
    if "3d" in it: return "3d_model"
    return "other"

def _ensure_lists(x) -> List[str]:
    return [str(t) for t in (x or [])]

def _postprocess(d: Dict[str, Any], lang: str) -> Dict[str, Any]:
    out = {
        "intent": str(d.get("intent","")).strip() or "other",
        "style": str(d.get("style","")).strip(),
        "product_type": str(d.get("product_type","")).strip(),
        "tags": _ensure_lists(d.get("tags")),
        "design_prompt": str(d.get("design_prompt","")).strip(),
        "notes": str(d.get("notes","")).strip(),
    }

    out["product_type"] = _norm_product_type(out["product_type"], out["intent"])

    if out["style"]:
        toks = [t.strip() for t in out["style"].replace(";", ",").split(",") if t.strip()]
        toks = toks[:8]
        while len(toks) < 3:
            toks.append("minimal")
        out["style"] = ", ".join(toks)
    else:
        out["style"] = "minimal, clean, high-contrast"

    tags = [t.strip().lower() for t in out["tags"] if t and isinstance(t, str)]
    tags = [t for t in tags if t][:8]
    while len(tags) < 3:
        tags.append("creative")
    out["tags"] = tags

    if not out["design_prompt"]:
        out["design_prompt"] = " ".join(tags) 
    out["design_prompt"] = _clip_words(out["design_prompt"], 1, 120)
    if len(out["design_prompt"].split()) < 40:
        filler = "Add clear composition and print-safe palette." if lang == "EN" else "Añade composición clara y paleta segura para impresión."
        out["design_prompt"] = f"{out['design_prompt']} {filler}"

    if not out["notes"]:
        out["notes"] = "Use reference if available; do not copy logos or brands." if lang=="EN" else "Usar referencia si está disponible; no copiar logotipos ni marcas."
    out["notes"] = " ".join(out["notes"].split(".")[:3]).strip()
    if out["notes"] and not out["notes"].endswith("."):
        out["notes"] += "."

    return out

def interpret_dream(user_text: str) -> Dict[str, Any]:
    lang = _detect_lang(user_text)

    try:
        result = _agent.ask(
            user_text,
            expect_json=True,
            json_schema=_JSON_SCHEMA,
            attempts=2,
            delay_s=0.8
        )
        if isinstance(result, dict) and result.get("intent") == "clarify":
            if not result.get("notes"):
                result["notes"] = (
                    "What would you like to create? e.g., 'a vaporwave poster of a cosmic fox', 'a retro children’s book cover with origami dragons'."
                    if lang == "EN" else
                    "¿Qué te gustaría crear? Ej.: 'un póster vaporwave de un zorro cósmico', 'una portada de libro infantil con dragones de origami'."
                )
            return result

        return _postprocess(result, lang)

    except Exception:
        if lang == "EN":
            return {
                "intent": "clarify",
                "style": "",
                "product_type": "",
                "tags": [],
                "design_prompt": "",
                "notes": "What would you like to create? e.g., 'a vaporwave poster of a cosmic fox', 'a retro children’s book cover with origami dragons'."
            }
        else:
            return {
                "intent": "clarify",
                "style": "",
                "product_type": "",
                "tags": [],
                "design_prompt": "",
                "notes": "¿Qué te gustaría crear? Ej.: 'un póster vaporwave de un zorro cósmico', 'una portada de libro infantil con dragones de origami'."
            }
