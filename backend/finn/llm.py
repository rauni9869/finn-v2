import json
import logging
import re
import time

import requests
from typing import Callable, Dict, List, Tuple, Type, TypeVar

from pydantic import BaseModel

from finn.config import GEMINI_API_KEY, GROQ_API_KEY, GROQ_MODELS

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_client = None
if GEMINI_API_KEY:
    try:
        from google import genai
        # The "-latest" model aliases only exist on v1beta
        _client = genai.Client(api_key=GEMINI_API_KEY, http_options={"api_version": "v1beta", "timeout": 90000})
    except Exception as e:
        logger.warning(f"Could not start the Gemini client: {e}")


class LLMUnavailable(Exception):
    """The model could not be reached or returned something unusable."""


# Less hidden reasoning before answering: several times faster, and the quote checks still guard accuracy
QUICK_TIMEOUT_MS = 30000
_search_blocked_until = 0.0
_last_error_was_quota = False

LOW_THINKING = {}
if _client:
    from google.genai import types as _types
    LOW_THINKING = {"thinking_config": _types.ThinkingConfig(thinking_level="low")}


def is_available() -> bool:
    return _client is not None


def generate_json(models: List[str], system: str, prompt: str, schema: Type[T], quick: bool = False) -> T:
    """Asks for JSON matching schema, moving to the next model if one is busy. Raises LLMUnavailable."""
    if not _client:
        raise LLMUnavailable("AI is not configured on this server. Add GEMINI_API_KEY to enable it.")
    config = {
        "system_instruction": system,
        "response_mime_type": "application/json",
        "response_schema": schema,
        "temperature": 0,
    }
    return _try_models(models, prompt, config, lambda response: schema.model_validate_json(response.text or ""), quick)


def generate_grounded_json(models: List[str], system: str, prompt: str, schema: Type[T], quick: bool = False) -> Tuple[T, List[Dict[str, str]]]:
    """Like generate_json, but the model searches Google first. Returns the result and its web sources."""
    global _search_blocked_until
    if not _client:
        raise LLMUnavailable("AI is not configured on this server. Add GEMINI_API_KEY to enable it.")
    if time.time() < _search_blocked_until:
        raise LLMUnavailable("Web search is over its free limit for now.")
    from google.genai import types

    # Search grounding can't be combined with a response schema, so the schema goes in the prompt
    config = {
        "system_instruction": system + "\n\nReply with only a JSON object matching this schema:\n" + json.dumps(schema.model_json_schema()),
        "tools": [types.Tool(google_search=types.GoogleSearch())],
        "temperature": 0,
    }

    def parse(response):
        text = (response.text or "").strip()
        match = re.search(r"\{.*\}", text, re.S)
        result = schema.model_validate_json(match.group(0) if match else text)
        sources = []
        metadata = response.candidates[0].grounding_metadata if response.candidates else None
        for chunk in (metadata.grounding_chunks or []) if metadata else []:
            if chunk.web and chunk.web.uri and len(sources) < 5:
                sources.append({"title": chunk.web.title or chunk.web.uri, "url": chunk.web.uri})
        return result, sources

    try:
        return _try_models(models, prompt, config, parse, quick)
    except LLMUnavailable:
        # Search has its own small free quota; stop trying it for a while once it is refused
        if _last_error_was_quota:
            _search_blocked_until = time.time() + 3600
        raise


def _try_models(models: List[str], prompt: str, config: dict, parse: Callable, quick: bool = False):
    """Tries each model in turn. Quick mode is for requests a person is waiting on: one attempt each, 30-second limit."""
    global _last_error_was_quota
    _last_error_was_quota = False
    if quick:
        config = {**config, "http_options": {"timeout": QUICK_TIMEOUT_MS}}
        models = models[:1]
    unreadable = False
    for model in models:
        # One retry per model, since "high demand" errors are often brief
        for attempt in range(1 if quick else 2):
            try:
                try:
                    response = _client.models.generate_content(model=model, contents=prompt, config={**config, **LOW_THINKING})
                except Exception as e:
                    # Older models don't take a thinking level, so ask again without it
                    if "thinking" not in str(e).lower():
                        raise
                    response = _client.models.generate_content(model=model, contents=prompt, config=config)
                return parse(response)
            except ValueError as e:
                logger.warning(f"Unreadable {model} output: {e}")
                unreadable = True
                break
            except Exception as e:
                logger.warning(f"{model} call failed: {e}")
                # Any quota refusal counts, even if a later model fails differently
                _last_error_was_quota = _last_error_was_quota or "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e)
                busy = "503" in str(e) or "UNAVAILABLE" in str(e)
                if not busy or attempt == 1 or quick:
                    break
                time.sleep(4)
    if unreadable:
        raise LLMUnavailable("The AI returned an unreadable answer. Please try again.")
    raise LLMUnavailable("The AI service is busy or its free limit was reached. Please try again in a few minutes.")


# --- Groq: open models with built-in web search, used for people briefs -------------

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def groq_available() -> bool:
    return bool(GROQ_API_KEY)


def _groq_sources(message: dict) -> List[Dict[str, str]]:
    """Pages the model actually opened while searching, most useful first."""
    sources, seen = [], set()
    for tool in message.get("executed_tools") or []:
        if tool.get("type") != "browser.open":
            continue
        for result in (tool.get("search_results") or {}).get("results", []):
            url = result.get("url", "")
            if not url.startswith("http") or url in seen or "exa.ai/search" in url:
                continue
            seen.add(url)
            title = re.sub(r"\s+-\s+viewing lines.*$", "", result.get("title") or url)
            sources.append({"title": title[:80], "url": url})
    return sources[:5]


def groq_search_json(system: str, prompt: str, schema: Type[T], timeout_s: int = 60) -> Tuple[T, List[Dict[str, str]]]:
    """Asks a Groq open model to search the web and answer as JSON. Raises LLMUnavailable."""
    if not GROQ_API_KEY:
        raise LLMUnavailable("Groq is not configured.")
    # Each Groq model has its own daily token allowance, so the smaller one is the fallback
    for model in GROQ_MODELS:
        try:
            return _groq_search_once(model, system, prompt, schema, timeout_s)
        except LLMUnavailable as e:
            last = e
            if "unreadable" in str(e):
                raise
    raise last


def _strip_citations(value):
    """Removes the model's inline citation markers, e.g. 【1†L98-L100】."""
    if isinstance(value, str):
        return re.sub(r"\s*【[^】]*】", "", value).strip()
    if isinstance(value, list):
        return [_strip_citations(v) for v in value]
    if isinstance(value, dict):
        return {k: _strip_citations(v) for k, v in value.items()}
    return value


def _groq_search_once(model: str, system: str, prompt: str, schema: Type[T], timeout_s: int) -> Tuple[T, List[Dict[str, str]]]:
    body = {
        "model": model,
        "tools": [{"type": "browser_search"}],
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system + "\n\nReply with only a JSON object matching this schema:\n" + json.dumps(schema.model_json_schema())},
            {"role": "user", "content": prompt},
        ],
    }
    for attempt in range(2):
        try:
            resp = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=body, timeout=timeout_s)
        except requests.RequestException as e:
            logger.warning(f"Groq request failed: {e}")
            break
        if resp.status_code == 429 and "per day" in resp.text:
            logger.warning(f"Groq {model} daily token allowance is used up")
            break
        if resp.status_code == 429 and attempt == 0:
            # The free tier also counts tokens per minute; wait out that window once
            wait = min(float(resp.headers.get("retry-after", "20")), 30)
            logger.info(f"Groq per-minute limit reached, waiting {wait:.0f}s")
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            logger.warning(f"Groq {model} returned {resp.status_code}: {resp.text[:160]}")
            break
        message = resp.json()["choices"][0]["message"]
        text = (message.get("content") or "").strip()
        match = re.search(r"\{.*\}", text, re.S)
        try:
            parsed = json.loads(match.group(0) if match else text)
            return schema.model_validate(_strip_citations(parsed)), _groq_sources(message)
        except ValueError as e:
            logger.warning(f"Unreadable Groq output: {e}")
            raise LLMUnavailable("The AI returned an unreadable answer. Please try again.")
    raise LLMUnavailable("The AI service is busy or its free limit was reached. Please try again in a few minutes.")
