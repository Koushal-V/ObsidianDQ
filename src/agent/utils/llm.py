"""Provider-neutral LLM helpers for the ObsidianDQ agents."""

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

DEFAULT_TEMPERATURE = 0.1


def llm_model_name(provider: str | None = None) -> str:
    """Return the configured model name without exposing credentials."""
    return os.getenv("GROQ_MODEL", "openai/gpt-oss-20b") if provider == "groq" else "gemini-2.5-flash"


def llm_call_event(stage: str, provider: str | None, *, success: bool, started_at: float, error: str | None = None) -> dict[str, Any]:
    """Create safe, structured metadata for an LLM boundary call."""
    return {
        "stage": stage,
        "provider": provider,
        "model": llm_model_name(provider),
        "temperature": DEFAULT_TEMPERATURE,
        "success": success,
        "error": (str(error)[:500] if error else None),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency_ms": round((time.perf_counter() - started_at) * 1000, 2),
    }


def get_gemini_client():
    """
    Get initialized google-genai Client if API key is present.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as exc:
        print(f"[Gemini Client Init Warning] {exc}")
        return None


def get_groq_client():
    """Return a Groq client when GROQ_API_KEY is configured."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except Exception as exc:
        print(f"[Groq Client Init Warning] {exc}")
        return None


def get_llm_provider() -> str | None:
    """Prefer Groq, then Gemini, based on configured credentials."""
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    return None


def llm_available() -> bool:
    return get_llm_provider() is not None


def generate_text(prompt: str, model: str | None = None) -> Optional[str]:
    """Generate text through the configured provider with graceful fallback."""
    provider = get_llm_provider()
    if provider == "groq":
        client = get_groq_client()
        if not client:
            return None
        try:
            response = client.chat.completions.create(
                model=model or llm_model_name("groq"),
                messages=[{"role": "user", "content": prompt}],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=500,
            )
            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception as exc:
            print(f"[Groq Generate Warning] {exc}")
            return None

    client = get_gemini_client()
    if client:
        try:
            response = client.models.generate_content(
                model=model or "gemini-2.5-flash",
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()
        except Exception as exc:
            print(f"[Gemini Generate Warning] {exc}")

    return None


def generate_text_with_audit(prompt: str, *, stage: str, model: str | None = None) -> tuple[Optional[str], dict[str, Any]]:
    """Generate text and return a safe audit event even when the call fails."""
    provider = get_llm_provider()
    started_at = time.perf_counter()
    if provider == "groq":
        last_error = None
        for attempt in range(3):
            try:
                client = get_groq_client()
                if not client:
                    raise RuntimeError("Groq client initialization failed")
                response = client.chat.completions.create(
                    model=model or llm_model_name("groq"),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=DEFAULT_TEMPERATURE,
                    max_tokens=500,
                )
                content = response.choices[0].message.content
                if not content:
                    raise RuntimeError("Groq returned an empty response")
                return content.strip(), llm_call_event(stage, provider, success=True, started_at=started_at)
            except Exception as exc:
                last_error = exc
                if "rate_limit" in str(exc).lower() or "429" in str(exc):
                    time.sleep(2 * (attempt + 1))
                    continue
                break
        return None, llm_call_event(stage, provider, success=False, started_at=started_at, error=last_error)
    if provider == "gemini":
        try:
            client = get_gemini_client()
            if not client:
                raise RuntimeError("Gemini client initialization failed")
            response = client.models.generate_content(model=model or llm_model_name("gemini"), contents=prompt)
            if not response or not response.text:
                raise RuntimeError("Gemini returned an empty response")
            return response.text.strip(), llm_call_event(stage, provider, success=True, started_at=started_at)
        except Exception as exc:
            return None, llm_call_event(stage, provider, success=False, started_at=started_at, error=exc)
    return None, llm_call_event(stage, provider, success=False, started_at=started_at, error="No LLM provider configured")
