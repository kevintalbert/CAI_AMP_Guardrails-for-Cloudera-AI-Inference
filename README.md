# NeMo Guardrails Proxy

A proxy application for Cloudera AI that sits in front of any OpenAI-compatible model endpoint,
applying [NVIDIA NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails) to all traffic.

## Features

- **Proxy**: Drop-in replacement for OpenAI-compatible `/chat/completions` endpoints
- **Auth passthrough**: Your Bearer token is forwarded transparently to the downstream model  
- **Streaming**: Supports both `stream: true` and non-streaming responses
- **Web UI**: Configure guardrails and endpoints through a Cloudera-styled interface
- **Rail Builder**: Toggle-based form for all built-in NeMo Guardrails rails
- **Code Editor**: Full YAML and Colang editors with Monaco (VS Code engine)
- **Hot-reload**: Rail changes apply instantly without restarting the server

## Supported Guardrails

| Category | Rails |
|---|---|
| LLM Self-Checking | Input check, Output check, Fact checking, Hallucination detection |
| Community Models | LlamaGuard, AlignScore, Presidio PII |
| Third-Party APIs | ActiveFence, GCP Text Moderation, Prompt Security, Pangea AI Guard |
| Other | Jailbreak detection, Prompt injection detection |

## Local Development

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8100

# Frontend (separate terminal)
cd frontend
npm install
npm run dev  # proxies /api/* to localhost:8100
```

Open http://localhost:3000

## Cloudera AI Deployment

This app ships as a Cloudera AI AMP. After cloning into a project, the `.project-metadata.yaml`
drives automatic setup:

1. Installs Python dependencies (`requirements.txt`)
2. Builds the Next.js frontend (`frontend/out/`)
3. Starts the FastAPI server on `$CDSW_APP_PORT`

## Usage as a Proxy

```bash
curl -X POST <APP_URL>/api/chat/completions \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"model":"your-model-id","messages":[{"role":"user","content":"Hello!"}]}'
```

Compatible with any OpenAI SDK by setting `base_url=<APP_URL>/api` and `api_key=<YOUR_TOKEN>`.
