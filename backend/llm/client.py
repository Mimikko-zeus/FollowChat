"""Generic LLM client utilities built around OpenAI-compatible HTTP APIs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Generator, Iterable, List, Mapping, MutableMapping, Optional, Sequence

import httpx


DEFAULT_API_BASE = "https://api.openai.com/v1"
CHAT_COMPLETIONS_ENDPOINT = "/chat/completions"


class LLMClientError(RuntimeError):
    """Raised when an upstream LLM provider returns an error."""


@dataclass(slots=True)
class ChatCompletionChoice:
    """Lightweight container for the assistant output."""

    content: str
    finish_reason: Optional[str]
    index: int


@dataclass(slots=True)
class ChatCompletionResult:
    """Normalized synchronous completion result."""

    choice: ChatCompletionChoice
    usage: Optional[Mapping[str, Any]]
    raw: Mapping[str, Any]


class OpenAICompatibleLLM:
    """Simple wrapper that can talk to any OpenAI-compatible API."""

    def __init__(
        self,
        *,
        api_key: Optional[str],
        model_name: str,
        api_base: Optional[str] = None,
        timeout: Optional[float] = 30.0,
    ) -> None:
        if not model_name:
            raise ValueError("model_name is required")
        self.api_key = api_key
        self.model_name = model_name
        self.api_base = (api_base or DEFAULT_API_BASE).rstrip("/")
        self.timeout = timeout

    # --------------------------------------------------------------------- #
    # Public helpers
    # --------------------------------------------------------------------- #

    def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> ChatCompletionResult:
        """Send a non-streaming chat completion request."""
        payload = self._build_payload(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_params=extra_params,
            stream=False,
        )
        response_json = self._post(payload)
        return self._parse_completion(response_json)

    def stream(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        extra_params: Optional[Mapping[str, Any]] = None,
    ) -> Generator[str, None, None]:
        """Stream tokens from the provider. Yields incremental deltas."""
        payload = self._build_payload(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_params=extra_params,
            stream=True,
        )
        yield from self._post_stream(payload)

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_payload(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        extra_params: Optional[Mapping[str, Any]],
        stream: bool,
    ) -> Dict[str, Any]:
        normalized_messages = self._normalize_messages(messages)
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": normalized_messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if extra_params:
            payload.update(extra_params)
        return payload

    @staticmethod
    def _normalize_messages(messages: Sequence[Mapping[str, str]]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content")
            if not role or not content:
                raise ValueError("Each message must contain 'role' and 'content'")
            normalized.append({"role": role, "content": content})
        return normalized

    def _post(self, payload: Mapping[str, Any]) -> MutableMapping[str, Any]:
        try:
            with httpx.Client(
                base_url=self.api_base,
                headers=self._build_headers(),
                timeout=self.timeout,
            ) as client:
                response = client.post(CHAT_COMPLETIONS_ENDPOINT, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMClientError(
                f"LLM provider returned {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMClientError(f"LLM provider request failed: {exc}") from exc
        return response.json()

    def _post_stream(self, payload: Mapping[str, Any]) -> Generator[str, None, None]:
        try:
            with httpx.Client(
                base_url=self.api_base,
                headers=self._build_headers(),
                timeout=self.timeout,
            ) as client:
                with client.stream(
                    "POST", CHAT_COMPLETIONS_ENDPOINT, json=payload
                ) as response:
                    response.raise_for_status()
                    for chunk in self._iter_sse(response):
                        if chunk is not None:
                            yield chunk
        except httpx.HTTPStatusError as exc:
            raise LLMClientError(
                f"LLM provider returned {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMClientError(f"LLM provider request failed: {exc}") from exc

    @staticmethod
    def _iter_sse(response: httpx.Response) -> Generator[Optional[str], None, None]:
        """Parse Server-Sent Events stream and yield deltas from the provider."""
        for line in response.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                return
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = parsed.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content_piece = delta.get("content")
            if content_piece:
                yield content_piece

    @staticmethod
    def _parse_completion(response_json: Mapping[str, Any]) -> ChatCompletionResult:
        choices = response_json.get("choices") or []
        if not choices:
            raise LLMClientError("LLM provider returned no choices")
        first_choice = choices[0]
        message = first_choice.get("message") or {}
        content = message.get("content", "")
        choice = ChatCompletionChoice(
            content=content,
            finish_reason=first_choice.get("finish_reason"),
            index=first_choice.get("index", 0),
        )
        return ChatCompletionResult(choice=choice, usage=response_json.get("usage"), raw=response_json)


__all__ = [
    "ChatCompletionChoice",
    "ChatCompletionResult",
    "LLMClientError",
    "OpenAICompatibleLLM",
]


