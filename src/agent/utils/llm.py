"""Provider-neutral LLM helpers for the ObsidianDQ agents."""

import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


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
                model=model or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
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
