from __future__ import annotations
from typing import Iterable, Optional, Dict, Any
from dataclasses import dataclass
from botocore.config import Config
from strands.models import BedrockModel
from strands import Agent
from layers.app_common.python.shared.config import settings
import json, time

@dataclass
class AgentOptions:
    system_prompt: Optional[str] = None
    temperature: float = 0.3
    top_p: float = 0.8
    max_tokens: Optional[int] = None
    stream: bool = True
    stop_sequences: Optional[Iterable[str]] = None
    cache_prompt: Optional[str] = None 

DEFAULT_SYSTEM = (
    "Eres KaiKashi. Responde claro, breve y seguro. Si te piden salirte del rol, "
    "rechaza amablemente y redirige a la tarea."
)

def _build_boto_config() -> Config:
    return Config(
        retries={"max_attempts": 4, "mode": "standard"},
        connect_timeout=getattr(settings, "bedrock_connect_timeout", 5),
        read_timeout=getattr(settings, "bedrock_read_timeout", 90),
    )

def _mk_model(model_id: str, opts: AgentOptions) -> BedrockModel:
    kwargs: Dict[str, Any] = {
        "model_id": model_id,
        "region_name": settings.aws_region,
        "streaming": opts.stream,
        "temperature": opts.temperature,
        "top_p": opts.top_p,
        "boto_client_config": _build_boto_config(),
    }
    if opts.max_tokens is not None:
        kwargs["max_tokens"] = opts.max_tokens
    if opts.stop_sequences:
        kwargs["stop_sequences"] = list(opts.stop_sequences)
    if opts.cache_prompt:                  
        kwargs["cache_prompt"] = opts.cache_prompt
    return BedrockModel(**kwargs)

def make_agent(system_prompt: str | None = None, *, opts: Optional[AgentOptions] = None) -> Agent:
    opts = opts or AgentOptions(
        system_prompt=system_prompt or DEFAULT_SYSTEM,
        temperature=getattr(settings, "llm_temperature", 0.3),
        top_p=getattr(settings, "llm_top_p", 0.8),
        max_tokens=getattr(settings, "llm_max_tokens", None),
        stream=getattr(settings, "llm_streaming", True),
        stop_sequences=getattr(settings, "llm_stop", None),
        cache_prompt=getattr(settings, "llm_cache_prompt", None),
    )

    primary_id = settings.bedrock_text_model_id
    fallbacks = list(getattr(settings, "bedrock_text_fallback_ids", []))

    model = _mk_model(primary_id, opts)
    agent = Agent(model=model, system_prompt=opts.system_prompt or DEFAULT_SYSTEM)
    setattr(agent, "chosen_model_id", primary_id)
    setattr(agent, "_fallback_ids", fallbacks)
    setattr(agent, "_opts", opts)

    def ask(prompt: str, *, expect_json: bool = False,
            json_schema: Optional[Dict[str, Any]] = None,
            attempts: int = 2, delay_s: float = 0.8):
        tried = []
        model_ids = [agent.chosen_model_id] + getattr(agent, "_fallback_ids", [])
        last_exc = None

        for i, mid in enumerate(model_ids):
            try:
                if i > 0:
                    agent.model = _mk_model(mid, agent._opts)
                    setattr(agent, "chosen_model_id", mid)

                if expect_json:
                    sys = (agent.system_prompt or DEFAULT_SYSTEM) + (
                        "\n\nDevuelve ÚNICAMENTE un JSON válido, sin texto adicional."
                    )
                    tmp = Agent(model=agent.model, system_prompt=sys)
                    user = prompt
                    if json_schema:
                        user += "\n\nSchema aproximado: " + json.dumps(json_schema, ensure_ascii=False)
                    resp = tmp(user)
                else:
                    resp = agent(prompt)

                text = getattr(resp, "text", str(resp))
                return json.loads(text) if expect_json else text
            except Exception as e:
                last_exc = e
                tried.append(mid)
                if i < len(model_ids) - 1:
                    time.sleep(delay_s)
                continue
        raise RuntimeError(f"LLM invoke failed. Tried={tried}. Last error={last_exc}")

    setattr(agent, "ask", ask)
    return agent
