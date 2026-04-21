"""
Singleton that owns the NeMo Guardrails LLMRails instance.

CustomProxyLLM is registered as a LangChain provider before the config is loaded
so NeMo Guardrails can resolve engine: custom -> CustomProxyLLM.
"""
import asyncio
import logging
from pathlib import Path

from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.llm.providers import register_llm_provider

from backend.custom_llm import CustomProxyLLM
from backend.settings import settings

logger = logging.getLogger(__name__)

_rails: LLMRails | None = None
_lock = asyncio.Lock()


def _ensure_default_config() -> None:
    """Write starter config files if the guardrails dir is empty."""
    gdir = settings.guardrails_dir
    gdir.mkdir(parents=True, exist_ok=True)

    config_file = gdir / "config.yml"
    if not config_file.exists():
        config_file.write_text(
            """models:
  - type: main
    engine: custom
    model: default

rails:
  input:
    flows: []
  output:
    flows: []
"""
        )
        logger.info("Wrote default config.yml")

    main_co = gdir / "main.co"
    if not main_co.exists():
        main_co.write_text(
            """# Define guardrail flows here using Colang syntax.
# Example:
# define user express greeting
#   "Hello"
#
# define flow
#   user express greeting
#   bot express greeting
"""
        )
        logger.info("Wrote default main.co")

    endpoints_file = settings.endpoints_file
    settings.config_dir.mkdir(parents=True, exist_ok=True)
    if not endpoints_file.exists():
        import json
        endpoints_file.write_text(json.dumps([], indent=2))
        logger.info("Wrote empty endpoints.json")


def _load() -> LLMRails:
    register_llm_provider("custom", CustomProxyLLM)
    _ensure_default_config()
    config = RailsConfig.from_path(str(settings.guardrails_dir))
    return LLMRails(config)


async def get_rails() -> LLMRails:
    global _rails
    if _rails is None:
        async with _lock:
            if _rails is None:
                _rails = _load()
    return _rails


async def reload_rails() -> None:
    global _rails
    async with _lock:
        _rails = _load()
    logger.info("NeMo Guardrails reloaded")


def get_rails_sync() -> LLMRails:
    """Blocking version for startup."""
    global _rails
    if _rails is None:
        _rails = _load()
    return _rails
