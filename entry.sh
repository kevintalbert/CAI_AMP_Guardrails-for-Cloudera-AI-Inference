#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# NeMo Guardrails Proxy — Cloudera AI Inference Service entry point
# ─────────────────────────────────────────────────────────────────────────────
# NOTE: written for /bin/sh compatibility — no bashisms so the shebang
# is purely a preference; the platform may invoke this with sh directly.
# ─────────────────────────────────────────────────────────────────────────────
set -e

# ── Resolve app root ──────────────────────────────────────────────────────────
# Use $0 (sh-compatible) instead of BASH_SOURCE, which is bash-only.
# The platform runs ./entry.sh from the repo root, so dirname $0 is the repo.
APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")" && pwd)}"
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

# ── Step 0: Install Python dependencies (idempotent) ─────────────────────────
# The platform may or may not auto-install requirements.txt before calling
# this script. We do it ourselves to be safe; pip skips already-installed pkgs.
if [ -f "$APP_DIR/requirements.txt" ]; then
    echo "[0/3] Installing Python dependencies..."
    pip install --quiet -r "$APP_DIR/requirements.txt" || {
        echo "      WARNING: pip install had errors — continuing anyway"
    }
    echo "      done"
    echo ""
fi

# ── Step 1: spacy model for Presidio PII rail (one-time ~560 MB download) ─────
echo "[1/3] spacy en_core_web_lg model..."
if python3 -c "import spacy; exit(0 if spacy.util.is_package('en_core_web_lg') else 1)" 2>/dev/null; then
    echo "      already installed — skipping"
else
    echo "      downloading (first run only, ~560 MB)..."
    python3 -m spacy download en_core_web_lg || echo "      WARNING: spacy model download failed — Presidio PII rail will be unavailable"
    echo "      done"
fi

# ── Step 2: Next.js frontend build (one-time, reused on restart) ──────────────
echo ""
echo "[2/3] Next.js frontend build..."
FRONTEND_OUT="$APP_DIR/frontend/out"
if [ -d "$FRONTEND_OUT" ] && [ -f "$FRONTEND_OUT/index.html" ]; then
    echo "      already built — skipping"
else
    echo "      building (first run only)..."
    python3 "$APP_DIR/startup_scripts/build_frontend.py" || {
        echo "      ERROR: frontend build failed — UI will be unavailable but API will still work"
    }
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
