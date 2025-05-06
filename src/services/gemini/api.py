import json
import asyncio
import random
import logging
from typing import Any, Callable, Optional, Union
from dataclasses import dataclass

import httpx
from pydantic import BaseModel

from src.services.gemini.settings import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


# Exception definitions specific to Gemini.
class GeminiAPIError(Exception):
    """Raised when the Gemini API returns a non-retryable error."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"Gemini API Error {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class GeminiConnectionError(Exception):
    """Raised when the Gemini service cannot be reached."""


class GeminiProcessingError(Exception):
    """Raised when the Gemini response is syntactically valid but semantically unusable."""


class GeminiCompletionResponse(BaseModel):
    """Structured representation of the Gemini API response."""
    id: Optional[str] = None
    model: Optional[str] = None
    created: Optional[int] = None
    choices: Optional[list[Any]] = None
    json_message: Any = None

    class Config:
        extra = "allow"


@dataclass
class GeminiRequest:
    schema: dict[str, Any]
    messages: list[dict[str, Any]]
    gemini_model: str
    system_prompt: Optional[str] = None
    validators: Optional[list[tuple[Callable[[dict[str, Any]], Any], tuple[type[Exception], ...]]]] = None
    timeout: Union[int, float] = 120
    max_timeout: Union[int, float] = 300
    max_attempts: int = 5
    temperature: float = 0
    top_p: float = 0.95
    top_k: Optional[int] = None
    max_output_tokens: int = 2**17
    log_context: Optional[str] = None  # Optional logging prefix


def _build_gemini_request(request: GeminiRequest) -> dict[str, Any]:
    """
    Construct the request payload for a structured Gemini API completion.

    Args:
        request: GeminiRequest dataclass containing all relevant configuration.

    Returns:
        A dictionary suitable for sending as the JSON payload.
    """
    generation_config = {
        "temperature": request.temperature,
        "topP": request.top_p,
        "maxOutputTokens": request.max_output_tokens,
        "responseMimeType": "application/json",
        "responseSchema": request.schema,
    }

    if request.top_k is not None:
        generation_config["topK"] = request.top_k

    payload = {
        "contents": request.messages,
        "generationConfig": generation_config,
    }

    if request.system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}

    return payload


def _extract_json_from_gemini_response(response_data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract the structured JSON payload from a Gemini API response.

    Args:
        response_data: Raw response JSON from the Gemini API.

    Returns:
        The extracted JSON object.

    Raises:
        GeminiProcessingError: If extraction fails due to unexpected structure.
    """
    if "candidates" not in response_data:
        raise GeminiProcessingError(f"No candidates in response: {response_data}")

    candidate = response_data["candidates"][0]
    content = candidate.get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        if "text" in part:
            try:
                return json.loads(part["text"])
            except json.JSONDecodeError as e:
                raise GeminiProcessingError(f"Failed to decode JSON text: {e}")
        elif "functionResponse" in part:
            json_message = part["functionResponse"].get("response")
            if json_message:
                return json_message

    raise GeminiProcessingError(f"Could not extract JSON content from response: {response_data}")


def _validate_gemini_response(
    json_message: dict[str, Any],
    validators: list[tuple[Callable[[dict[str, Any]], Any], tuple[type[Exception], ...]]],
) -> None:
    """
    Validate the structured JSON response using user-provided validators.

    Args:
        json_message: The parsed JSON content from Gemini.
        validators: A list of tuples, each containing a validation function and the exceptions it may raise.

    Raises:
        GeminiProcessingError: If any validator fails.
    """
    for validator, exceptions in validators:
        try:
            validator(json_message)
        except exceptions as exc:
            raise GeminiProcessingError(f"Validation failed: {validator.__name__}: {exc}")


async def get_gemini_structured_response(request: GeminiRequest) -> GeminiCompletionResponse:
    """
    Request a structured JSON response from the Gemini API, with retries and validation.

    Args:
        request: GeminiRequest dataclass with all request parameters.

    Returns:
        A GeminiCompletionResponse containing the structured response.

    Raises:
        GeminiAPIError: If the API returns an irrecoverable status.
        GeminiConnectionError: If the request cannot be completed.
        GeminiProcessingError: If validation or parsing fails.
    """
    validators = request.validators or []
    attempts = 0
    delay: Union[int, float] = 5

    payload = _build_gemini_request(request)

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{request.gemini_model}:generateContent?key={settings.GEMINI_API_KEY}"
    )

    while attempts < request.max_attempts:
        attempts += 1
        try:
            async with httpx.AsyncClient(timeout=request.timeout) as client:
                headers = {"Content-Type": "application/json"}
                response = await client.post(url=url, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()

            json_message = _extract_json_from_gemini_response(response_data)
            _validate_gemini_response(json_message, validators)

            gemini_response = GeminiCompletionResponse.model_validate(response_data)
            gemini_response.json_message = json_message
            return gemini_response

        except httpx.TimeoutException:
            logger.warning(f"[{request.log_context or request.gemini_model}] Gemini request timed out (attempt {attempts}/{request.max_attempts})")
            request.timeout = min(request.max_timeout, request.timeout * 1.5)
            await asyncio.sleep(1)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                delay = min(60.0, delay * 2 * (1 + random.random()))
                logger.warning(f"[{request.log_context or request.gemini_model}] Rate limited by Gemini, backing off for {delay:.2f}s")
                await asyncio.sleep(delay)
                continue
            elif 500 <= e.response.status_code < 600:
                logger.warning(f"[{request.log_context or request.gemini_model}] Gemini API error: {e.response.status_code} - {e.response.text}")
                await asyncio.sleep(delay)
                continue
            else:
                raise GeminiAPIError(e.response.status_code, e.response.text) from e

        except httpx.RequestError as e:
            raise GeminiConnectionError("Could not complete the request") from e

        except Exception as e:
            raise GeminiProcessingError("Could not process the request") from e

    raise GeminiAPIError(500, f"Failed to get a valid response after {request.max_attempts} attempts")
