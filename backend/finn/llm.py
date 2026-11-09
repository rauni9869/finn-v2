import json
import logging
import re
import time
from typing import Callable, Dict, List, Tuple, Type, TypeVar

from pydantic import BaseModel

from finn.config import GEMINI_API_KEY

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
