from contextvars import ContextVar

# Holds the Bearer token for the current async request context.
# Set by the proxy router before invoking NeMo Guardrails; read by CustomProxyLLM.
REQUEST_TOKEN: ContextVar[str] = ContextVar("request_token", default="")

# Holds the active endpoint config for the current request.
REQUEST_ENDPOINT: ContextVar[dict] = ContextVar("request_endpoint", default={})
