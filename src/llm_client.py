"""Universal Multi-Provider LLM Client for MoneyLens AI (Gemini / OpenAI / Groq / OpenRouter / Zero-Key Live AI).

Powers both the Floating Circular AI Assistant and the AI Financial Advisor so users can ask
ANY open-domain question (just like ChatGPT / Gemini) with full conversation memory while staying
grounded in their live MoneyLens AI data and product manual.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

from src.data_processing import get_app_setting

load_dotenv()

GEMINI_MODEL_CANDIDATES = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
    "gemini-4-hydrogen",
    "gemini-2.5-flash",
)


def _iter_gemini_clients(api_key: str):
    """Yield Google GenAI client(s) accepting ANY non-empty key (AQ., AIza, etc.) with fast failover."""
    from google import genai
    from google.genai import types

    clean_key = str(api_key or "").strip()
    if not clean_key:
        return
    try:
        fast_http = types.HttpOptions(
            timeout=18_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        )
    except Exception:
        fast_http = None

    # Standard Developer API works for both AIza and AQ. keys
    yield (
        genai.Client(api_key=clean_key, http_options=fast_http)
        if fast_http is not None
        else genai.Client(api_key=clean_key)
    ), "Google"
    # Vertex AI Express Mode fallback when project has aiplatform.googleapis.com enabled
    try:
        yield (
            genai.Client(vertexai=True, api_key=clean_key, http_options=fast_http)
            if fast_http is not None
            else genai.Client(vertexai=True, api_key=clean_key)
        ), "Google Vertex"
    except Exception:
        pass


def resolve_saved_api_key(explicit_key: str = "") -> str:
    """Resolve user API key from explicit arg, env vars, or SQLite app_settings."""
    for cand in (
        explicit_key,
        os.getenv("GEMINI_API_KEY", ""),
        os.getenv("OPENAI_API_KEY", ""),
        os.getenv("GROQ_API_KEY", ""),
        os.getenv("OPENROUTER_API_KEY", ""),
        get_app_setting("ai_api_key", ""),
    ):
        val = str(cand or "").strip()
        if val:
            return val
    return ""


def _normalize_history(history: list[dict[str, Any]] | None, max_turns: int = 10) -> list[dict[str, str]]:
    """Convert session chat history into clean OpenAI-style role/content turns."""
    out: list[dict[str, str]] = []
    if not history:
        return out
    for msg in history[-max_turns:]:
        role = str(msg.get("role", "")).strip().lower()
        content = str(msg.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            out.append({"role": role, "content": content[:2500]})
    return out


def _call_gemini(
    messages: list[dict[str, str]],
    system_instruction: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
) -> tuple[str | None, str]:
    try:
        from google.genai import types

        contents = [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part.from_text(text=m["content"])],
            )
            for m in messages
        ]
        for client, vendor in _iter_gemini_clients(api_key):
            saw_non_auth_error = False
            for model_name in GEMINI_MODEL_CANDIDATES:
                try:
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=temperature,
                        ),
                    )
                    txt = (getattr(resp, "text", None) or "").strip()
                    if txt:
                        return txt, f"{vendor} {model_name}"
                except Exception as exc:
                    err_s = str(exc)
                    if "API_KEY_INVALID" not in err_s and "401" not in err_s and "403" not in err_s:
                        saw_non_auth_error = True
                    continue
            if saw_non_auth_error:
                break
    except Exception:
        pass
    return None, ""


def generate_gemini_vision(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    api_key: str = "",
    max_tokens: int = 800,
    temperature: float = 0.1,
) -> tuple[str | None, str, str]:
    """Run multimodal Vision OCR (printed bills, bank screenshots, handwriting) with any saved API key.

    Accepts ANY non-empty key after `.strip()` (AQ., AIza, OpenAI sk-, OpenRouter sk-or-, etc.).
    Returns `(response_text, provider_label, last_error)`.
    """
    import base64

    key = resolve_saved_api_key(api_key)
    if not key:
        return None, "", "Chưa nhập API Key."

    last_err = ""
    # OpenAI / OpenRouter vision support if user supplied sk- / sk-or- key
    if key.startswith("sk-or-") or key.startswith("sk-"):
        url = (
            "https://openrouter.ai/api/v1/chat/completions"
            if key.startswith("sk-or-")
            else "https://api.openai.com/v1/chat/completions"
        )
        model = "google/gemini-2.5-flash" if key.startswith("sk-or-") else "gpt-4o-mini"
        b64 = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                    ],
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                timeout=30.0,
            )
            if resp.status_code == 200:
                txt = str((resp.json().get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()
                if txt:
                    return txt, model, ""
            last_err = f"HTTP {resp.status_code}: {resp.text[:160]}"
        except Exception as exc:
            last_err = str(exc)
        return None, "", last_err

    # Any Google key (AQ., AIza, or other non-empty Google key — no rigid prefix check!)
    try:
        from google.genai import types

        img_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        for client, vendor in _iter_gemini_clients(key):
            saw_non_auth_error = False
            for model_name in GEMINI_MODEL_CANDIDATES:
                try:
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=[img_part, prompt],
                        config=types.GenerateContentConfig(temperature=temperature),
                    )
                    txt = (getattr(resp, "text", None) or "").strip()
                    if txt:
                        return txt, f"{vendor} {model_name}", ""
                except Exception as exc:
                    err_msg = str(exc)[:220]
                    if not last_err or vendor == "Google":
                        last_err = err_msg
                    if "API_KEY_INVALID" not in err_msg and "401" not in err_msg and "403" not in err_msg:
                        saw_non_auth_error = True
                    continue
            if saw_non_auth_error:
                break
    except Exception as exc:
        last_err = str(exc)[:220]

    return None, "", last_err


def _call_openai_compatible(
    url: str,
    model: str,
    messages: list[dict[str, str]],
    system_instruction: str,
    api_key: str = "",
    max_tokens: int = 900,
    temperature: float = 0.55,
    timeout: float = 22.0,
    label: str = "AI Assistant",
    minimal_payload: bool = False,
) -> tuple[str | None, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system_instruction}, *messages],
    }
    if not minimal_payload:
        payload["temperature"] = temperature
        payload["max_tokens"] = max_tokens
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if resp.status_code == 402:
            return None, "RATE_LIMIT_402"
        if resp.status_code != 200:
            return None, ""
        data = resp.json()
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            txt = str(msg.get("content") or "").strip()
            if txt:
                return txt, label
    except Exception:
        pass
    return None, ""


def generate_universal_reply(
    user_message: str,
    system_instruction: str,
    history: list[dict[str, Any]] | None = None,
    api_key: str = "",
    max_tokens: int = 900,
    temperature: float = 0.55,
) -> tuple[str | None, str]:
    """Generate an unrestricted, ChatGPT/Gemini-class response using the best available LLM."""
    q = str(user_message).strip()
    if not q:
        return None, ""

    msgs = _normalize_history(history, max_turns=10)
    if not msgs or msgs[-1]["role"] != "user" or msgs[-1]["content"] != q:
        msgs.append({"role": "user", "content": q})

    key = resolve_saved_api_key(api_key)
    if key:
        if key.startswith("gsk_"):
            txt, src = _call_openai_compatible(
                url="https://api.groq.com/openai/v1/chat/completions",
                model="llama-3.3-70b-versatile",
                messages=msgs,
                system_instruction=system_instruction,
                api_key=key,
                max_tokens=max_tokens,
                temperature=temperature,
                label="Groq Llama 3.3 70B",
            )
            if txt:
                return txt, src
        elif key.startswith("sk-or-"):
            txt, src = _call_openai_compatible(
                url="https://openrouter.ai/api/v1/chat/completions",
                model="google/gemini-2.0-flash-001",
                messages=msgs,
                system_instruction=system_instruction,
                api_key=key,
                max_tokens=max_tokens,
                temperature=temperature,
                label="OpenRouter AI",
            )
            if txt:
                return txt, src
        elif key.startswith("sk-"):
            txt, src = _call_openai_compatible(
                url="https://api.openai.com/v1/chat/completions",
                model="gpt-4o-mini",
                messages=msgs,
                system_instruction=system_instruction,
                api_key=key,
                max_tokens=max_tokens,
                temperature=temperature,
                label="OpenAI GPT-4o mini",
            )
            if txt:
                return txt, src
        else:
            txt, src = _call_gemini(msgs, system_instruction, key, max_tokens, temperature)
            if txt:
                return txt, src

    # Zero-key live universal LLM fallback (answers any open-ended question immediately!)
    saw_rate_limit = False
    for pub_model in ("openai", "openai-fast"):
        txt, src = _call_openai_compatible(
            url="https://text.pollinations.ai/openai",
            model=pub_model,
            messages=msgs,
            system_instruction=system_instruction,
            api_key="",
            timeout=25.0,
            label="MoneyLens Universal AI",
            minimal_payload=True,
        )
        if txt:
            return txt, src
        if src == "RATE_LIMIT_402":
            saw_rate_limit = True
            break

    if saw_rate_limit:
        return None, "RATE_LIMIT_402"
    return None, ""
