import time
from google import genai
from google.genai import types
from config import (GEMINI_API_KEY, GEMINI_EMBED_MODEL, GEMINI_GEN_MODEL,
                    GEN_TEMPERATURE)

_client = genai.Client(api_key=GEMINI_API_KEY)


def _retry(fn, retries: int = 5, backoff: float = 10.0):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            retryable = ("503" in msg or "UNAVAILABLE" in msg or
                         "ConnectError" in msg or "nodename nor servname" in msg or
                         "Connection" in msg)
            if retryable and attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
                continue
            raise
    raise RuntimeError("Max retries exceeded")


def embed(text: str, dimensions: int = 768) -> list[float]:
    result = _retry(lambda: _client.models.embed_content(
        model=GEMINI_EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=dimensions),
    ))
    return result.embeddings[0].values


def generate(prompt: str, temperature: float = GEN_TEMPERATURE) -> str:
    """Temperature defaults to 0 so the audit is deterministic — see config."""
    response = _retry(lambda: _client.models.generate_content(
        model=GEMINI_GEN_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=temperature),
    ))
    return response.text
