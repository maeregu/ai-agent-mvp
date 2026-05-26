from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from app.config import OPENAI_TRANSLATION_MODEL, TRANSLATION_PROVIDER


LANGUAGE_NAMES = {
    "am": "Amharic",
    "en": "English",
}


def is_mostly_english(text: str) -> bool:
    if not text.strip():
        return False
    ascii_letters = sum(1 for char in text if char.isascii() and char.isalpha())
    non_space = sum(1 for char in text if not char.isspace())
    return non_space > 0 and ascii_letters / non_space > 0.65


def translate_text(text: str, target_language: str) -> str:
    """Translate transcript text using the configured provider."""
    if target_language == "none":
        return ""
    if target_language == "en" and is_mostly_english(text):
        return text

    provider = os.getenv("TRANSLATION_PROVIDER", TRANSLATION_PROVIDER).lower()
    if provider == "openai":
        return translate_with_openai(text, target_language)
    if provider == "demo":
        return demo_translation(text, target_language)
    raise RuntimeError(f"Unsupported translation provider: {provider}")


def translate_with_openai(text: str, target_language: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add your OpenAI API key, restart the backend, "
            "and upload again to enable real Amharic-English translation."
        )

    target_name = LANGUAGE_NAMES.get(target_language, target_language)
    model = os.getenv("OPENAI_TRANSLATION_MODEL", OPENAI_TRANSLATION_MODEL)
    body = {
        "model": model,
        "instructions": (
            "You are a professional translator for Ethiopian users. Translate the input "
            f"into {target_name}. Preserve names, numbers, paragraph breaks, and meaning. "
            "Return only the translation, with no explanation."
        ),
        "input": text,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(clean_openai_error(details)) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI translation network error: {exc.reason}") from exc

    translated = extract_response_text(payload)
    if not translated:
        raise RuntimeError("OpenAI translation returned no text.")
    return translated.strip()


def clean_openai_error(details: str) -> str:
    try:
        payload = json.loads(details)
    except json.JSONDecodeError:
        return "OpenAI translation failed. Check your API key and billing status."

    error = payload.get("error", {})
    code = error.get("code")
    message = error.get("message", "")
    if code == "invalid_api_key":
        return "OpenAI API key is invalid. Add a valid key, restart the backend, and try again."
    if code == "insufficient_quota":
        return "OpenAI account has insufficient quota or billing is not active."
    if message:
        return f"OpenAI translation failed: {message}"
    return "OpenAI translation failed. Check your API key and billing status."


def extract_response_text(payload: dict) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str):
        return direct

    parts: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "\n".join(parts)

def demo_translation(text: str, target_language: str) -> str:
    language_name = LANGUAGE_NAMES.get(target_language, target_language)
    return (
        f"[Translation target: {language_name}]\n\n"
        "Demo translation mode is active. Set TRANSLATION_PROVIDER=openai and "
        "OPENAI_API_KEY to enable real translation.\n\n"
        f"{text}"
    )

