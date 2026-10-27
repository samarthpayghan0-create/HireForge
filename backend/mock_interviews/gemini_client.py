"""Small wrapper around the Gemini API shared by question generation and
answer evaluation."""

import json
import re

from django.conf import settings
from google import genai
from google.genai import types

REQUEST_TIMEOUT_MS = 60_000


class GeminiNotConfigured(RuntimeError):
    """Raised when GEMINI_API_KEY is not set."""


def _parse_json(text):
    text = (text or "").strip()

    # Be tolerant of models that wrap JSON in a markdown fence.
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)

    return json.loads(text)


def generate_json(prompt, max_output_tokens=4096):
    """Send `prompt` to Gemini and return the parsed JSON response."""

    if not settings.GEMINI_API_KEY:
        raise GeminiNotConfigured("Gemini API key is not configured.")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=max_output_tokens,
            # Thinking models spend part of this budget on reasoning, so keep it
            # generous: a truncated JSON answer is useless.
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        ),
    )

    if not getattr(response, "text", None):
        raise ValueError("Gemini returned an empty response.")

    return _parse_json(response.text)
