"""
Custom LangChain LLM (BaseLLM) that injects the per-request Bearer token dynamically.

NeMo Guardrails 0.21+ requires register_llm_provider classes to implement _acall
(the BaseLLM async interface), not BaseChatModel._agenerate.

The token and target endpoint are read from contextvars set by the proxy router.

How NeMo calls this LLM for self-check tasks (self_check_input / self_check_output):
  - The action calls llm_call(llm, prompt, llm_params={"temperature": 0.001, "max_tokens": 3})
  - llm_call does:  llm.bind(**llm_params).ainvoke(prompt)
  - LangChain passes those bound params as **kwargs all the way through _agenerate → _acall
  - We MUST read temperature/max_tokens from kwargs so NeMo's constraints are honored.

Why think-tag stripping matters:
  - With max_tokens=1024 (ignored kwargs), a reasoning model emits <think>...</think> blocks.
  - NeMo's is_content_safe() only inspects the first 2 tokens of the response.
  - "think" is not in {"yes","no","safe","unsafe"} → default [False] = BLOCKED.
  - We strip tags here because BaseLLM.ainvoke() returns a plain str, so NeMo's own
    _extract_and_remove_think_tags (which mutates response.content) never fires for us.
"""
import re
from typing import Any, List, Optional

import httpx
from langchain_core.language_models.llms import BaseLLM
from langchain_core.outputs import Generation, LLMResult

from backend.token_context import REQUEST_ENDPOINT, REQUEST_TOKEN

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> reasoning blocks emitted by reasoning models."""
    return _THINK_RE.sub("", text).strip()


def _is_classification_prompt(prompt: str) -> bool:
    """Detect NeMo self-check prompts that expect a single Yes/No answer."""
    p = prompt.lower()
    return "answer [yes/no]" in p or "answer [yes/no]:" in p


def _build_messages(prompt: str) -> list[dict]:
    """
    Build the messages list for the chat completions API.

    For Yes/No classification prompts we add a terse system message so the
    model is primed to respond concisely even before the token limit kicks in.
    """
    if _is_classification_prompt(prompt):
        return [
            {
                "role": "system",
                "content": (
                    "You are a strict content safety classifier. "
                    "Respond with exactly one word: 'Yes' or 'No'. "
                    "No explanation. No punctuation."
                ),
            },
            {"role": "user", "content": prompt},
        ]
    return [{"role": "user", "content": prompt}]


class CustomProxyLLM(BaseLLM):
    """Routes LLM calls through the configured endpoint using the per-request Bearer token."""

    model_name: str = "default"
    temperature: float = 0.7
    max_tokens: int = 1024
    request_timeout: int = 120

    @property
    def _llm_type(self) -> str:
        return "custom_proxy"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        token = REQUEST_TOKEN.get()
        endpoint = REQUEST_ENDPOINT.get()
        base_url = endpoint.get("base_url", "").rstrip("/")
        model_id = endpoint.get("model_id", self.model_name)

        if not base_url:
            raise ValueError("No target endpoint configured. Add one in the Endpoints page.")

        # NeMo passes temperature=0.001 and max_tokens=3 for self-check tasks via llm.bind().
        # LangChain propagates those through _generate → _call via **kwargs.
        # Using self.temperature/self.max_tokens here would ignore those constraints.
        temperature = float(kwargs.get("temperature", self.temperature))
        max_tokens = int(kwargs.get("max_tokens", self.max_tokens))

        headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
        payload: dict = {
            "model": model_id,
            "messages": _build_messages(prompt),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            payload["stop"] = stop

        with httpx.Client(timeout=self.request_timeout) as client:
            resp = client.post(base_url + "/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return _strip_think_tags(data["choices"][0]["message"]["content"])

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        token = REQUEST_TOKEN.get()
        endpoint = REQUEST_ENDPOINT.get()
        base_url = endpoint.get("base_url", "").rstrip("/")
        model_id = endpoint.get("model_id", self.model_name)

        if not base_url:
            raise ValueError("No target endpoint configured. Add one in the Endpoints page.")

        # NeMo passes temperature=0.001 and max_tokens=3 for self-check tasks via llm.bind().
        # LangChain propagates those through _agenerate → _acall via **kwargs.
        # Using self.temperature/self.max_tokens here would ignore those constraints.
        temperature = float(kwargs.get("temperature", self.temperature))
        max_tokens = int(kwargs.get("max_tokens", self.max_tokens))

        headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
        payload: dict = {
            "model": model_id,
            "messages": _build_messages(prompt),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            payload["stop"] = stop

        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            resp = await client.post(base_url + "/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return _strip_think_tags(data["choices"][0]["message"]["content"])

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> LLMResult:
        generations = []
        for prompt in prompts:
            text = self._call(prompt, stop=stop, **kwargs)
            generations.append([Generation(text=text)])
        return LLMResult(generations=generations)

    async def _agenerate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> LLMResult:
        generations = []
        for prompt in prompts:
            text = await self._acall(prompt, stop=stop, **kwargs)
            generations.append([Generation(text=text)])
        return LLMResult(generations=generations)
