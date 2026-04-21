"""Launch the FastAPI backend on the Cloudera AI application port."""
import subprocess
import sys
import os

app_dir = os.getenv("APP_DIR", os.getcwd())
os.chdir(app_dir)

# Cloudera AI exposes the app port via CDSW_APP_PORT (default 8100)
port = os.getenv("CDSW_APP_PORT", os.getenv("GUARDRAILS_PORT", "8100"))
host = "127.0.0.1"

print(f"Starting NeMo Guardrails Proxy on {host}:{port}")
print(f"App directory: {app_dir}")

subprocess.run(
    [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", host,
        "--port", port,
        "--workers", "1",
        "--log-level", "info",
    ],
    check=True,
)
