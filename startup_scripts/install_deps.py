"""Install Python dependencies from requirements.txt."""
import subprocess
import sys
import os
from pathlib import Path

app_dir = os.getenv("APP_DIR", os.getcwd())
print(f"App directory: {app_dir}")
os.chdir(app_dir)

req_file = os.path.join(app_dir, "requirements.txt")
print(f"Installing from {req_file}")

subprocess.run(
    [sys.executable, "-m", "pip", "install", "--user", "-r", req_file],
    check=True,
)

# Ensure ~/.local/bin is on PATH so nodeenv CLI is findable in subsequent tasks
local_bin = str(Path.home() / ".local" / "bin")
path_now = os.environ.get("PATH", "")
if local_bin not in path_now:
    print(f"Adding {local_bin} to PATH")
    os.environ["PATH"] = local_bin + os.pathsep + path_now

print(f"\nPython dependencies installed successfully.")
print(f"nodeenv location: {subprocess.check_output(['which', 'nodeenv'], env=os.environ).decode().strip() if __import__('shutil').which('nodeenv') else 'will be found by build script'}")
