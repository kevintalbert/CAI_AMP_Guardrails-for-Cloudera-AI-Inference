#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NeMo Guardrails Proxy — Cloudera AI Inference Service entry point
#
# The platform (serving apps):
#   1. Clones the repo from GitHub
#   2. Installs requirements.txt via pip automatically
#   3. Runs this script
#
# This script handles the remaining one-time setup steps that pip can't do
# (spacy model download, Next.js build) and then starts the server.
# Each step is idempotent — subsequent restarts skip work already done.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Resolve app root (works regardless of cwd the platform sets) ──────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-$SCRIPT_DIR}"
cd "$APP_DIR"

PORT="${CDSW_APP_PORT:-8080}"

echo "=================================================="
echo " NeMo Guardrails Proxy"
echo "=================================================="
echo " App dir : $APP_DIR"
echo " Python  : $(python3 --version 2>&1)"
echo " Port    : $PORT"
echo "=================================================="
echo ""

# ── Step 1: spacy model for Presidio PII rail (one-time ~560 MB download) ─────
echo "[1/3] spacy en_core_web_lg model..."
if python3 -c "import spacy; exit(0 if spacy.util.is_package('en_core_web_lg') else 1)" 2>/dev/null; then
    echo "      already installed — skipping"
else
    echo "      downloading (first run only, ~560 MB)..."
    python3 -m spacy download en_core_web_lg
    echo "      done"
fi

# ── Step 2: Next.js frontend build (one-time, reused on restart) ──────────────
echo ""
echo "[2/3] Next.js frontend build..."
FRONTEND_OUT="$APP_DIR/frontend/out"
if [ -d "$FRONTEND_OUT" ] && [ -f "$FRONTEND_OUT/index.html" ]; then
    echo "      already built at $FRONTEND_OUT — skipping"
else
    echo "      building (first run only)..."
    python3 "$APP_DIR/startup_scripts/build_frontend.py"
    echo "      done"
fi

# ── Step 3: Launch FastAPI via uvicorn ────────────────────────────────────────
echo ""
echo "[3/3] Starting server on 0.0.0.0:$PORT"
echo ""
PYTHONPATH="$APP_DIR" exec python3 -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 1 \
    --log-level info
