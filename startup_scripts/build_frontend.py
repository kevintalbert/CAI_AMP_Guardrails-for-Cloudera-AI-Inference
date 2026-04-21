"""
Bootstrap Node.js via nodeenv (pip-installed) and build the Next.js frontend.

nodeenv is a Python package that downloads and configures a self-contained
Node.js environment — no system npm or node required.
"""
import subprocess
import sys
import os
import shutil
from pathlib import Path

NODE_VERSION = "20.19.1"   # LTS


def find_nodeenv_bin() -> str | None:
    """Look for nodeenv in PATH and common pip user-install locations."""
    found = shutil.which("nodeenv")
    if found:
        return found
    candidates = [
        Path(sys.executable).parent / "nodeenv",
        Path.home() / ".local" / "bin" / "nodeenv",
        Path("/home/cdsw/.local/bin/nodeenv"),
        Path("/usr/local/bin/nodeenv"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def ensure_nodeenv() -> str:
    """Return path to nodeenv binary, installing if needed."""
    path = find_nodeenv_bin()
    if path:
        print(f"Found nodeenv at: {path}")
        return path
    print("nodeenv not found — installing via pip...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "nodeenv"],
        check=True,
    )
    path = find_nodeenv_bin()
    return path or "PYTHON_MODULE"


def is_nodeenv_complete(node_env_dir: Path) -> bool:
    """Return True only if the env exists and contains a working npm."""
    npm = node_env_dir / "bin" / "npm"
    return npm.exists()


def create_nodeenv(nodeenv_path: str, node_env_dir: Path) -> None:
    """Create a fresh Node.js environment, deleting any incomplete one first."""
    if node_env_dir.exists() and not is_nodeenv_complete(node_env_dir):
        print(f"Incomplete Node.js env detected at {node_env_dir} — removing and recreating...")
        shutil.rmtree(node_env_dir)

    if node_env_dir.exists():
        print(f"Re-using existing Node.js environment at {node_env_dir}")
        return

    cmd_base = (
        [nodeenv_path, str(node_env_dir)]
        if nodeenv_path != "PYTHON_MODULE"
        else [sys.executable, "-m", "nodeenv", str(node_env_dir)]
    )

    # Try prebuilt first (fast download), fall back to source build
    try:
        print(f"Creating Node.js {NODE_VERSION} environment (prebuilt binary)...")
        subprocess.run(
            cmd_base + [f"--node={NODE_VERSION}", "--prebuilt"],
            check=True,
        )
    except subprocess.CalledProcessError:
        print("Prebuilt unavailable — building from source (may take several minutes)...")
        subprocess.run(cmd_base + [f"--node={NODE_VERSION}"], check=True)


def activate_nodeenv(node_env_dir: Path) -> str:
    """Prepend nodeenv bin to PATH and return absolute path to npm."""
    node_bin = node_env_dir / "bin"
    if not node_bin.exists():
        raise RuntimeError(f"nodeenv bin not found at {node_bin}")

    os.environ["PATH"] = str(node_bin) + os.pathsep + os.environ.get("PATH", "")
    os.environ["NODE_VIRTUAL_ENV"] = str(node_env_dir)

    npm_path = node_bin / "npm"
    if not npm_path.exists():
        # Node 20+ ships with corepack — use it to enable npm
        corepack = node_bin / "corepack"
        if corepack.exists():
            print("npm binary missing but corepack found — running 'corepack enable npm'...")
            subprocess.run([str(corepack), "enable", "npm"], check=True,
                           env=os.environ)
        if not npm_path.exists():
            contents = list(node_bin.iterdir())
            raise RuntimeError(
                f"npm not found in {node_bin} even after corepack enable.\n"
                f"Contents: {contents}"
            )

    return str(npm_path)


def main():
    app_dir = os.getenv("APP_DIR", os.getcwd())
    os.chdir(app_dir)
    frontend_dir = Path(app_dir) / "frontend"
    node_env_dir = Path(app_dir) / ".nodeenv"

    print(f"App directory:      {app_dir}")
    print(f"Frontend directory: {frontend_dir}")
    print(f"Node.js env dir:    {node_env_dir}")

    if not frontend_dir.exists():
        print("ERROR: frontend/ directory not found.")
        sys.exit(1)

    npm_cmd = shutil.which("npm")

    if npm_cmd:
        print(f"Found system npm: {npm_cmd}")
    else:
        print("System npm not found — using nodeenv...")
        nodeenv_bin = ensure_nodeenv()
        create_nodeenv(nodeenv_bin, node_env_dir)
        npm_cmd = activate_nodeenv(node_env_dir)

    node_ver = subprocess.check_output(["node", "--version"],
                                       env=os.environ).decode().strip()
    npm_ver = subprocess.check_output([npm_cmd, "--version"],
                                      env=os.environ).decode().strip()
    print(f"Node: {node_ver}  |  npm: {npm_ver}\n")

    print("Installing packages...")
    subprocess.run([npm_cmd, "install"], check=True, cwd=str(frontend_dir),
                   env=os.environ)

    print("\nBuilding frontend...")
    subprocess.run([npm_cmd, "run", "build"], check=True, cwd=str(frontend_dir),
                   env=os.environ)

    out_dir = frontend_dir / "out"
    if out_dir.exists():
        print(f"\nFrontend build complete. Static files at: {out_dir}")
    else:
        print("WARNING: frontend/out/ not found — check build output above.")


if __name__ == "__main__":
    main()
