import os
import sys
import socket
import shutil
import subprocess
from pathlib import Path


def _verify_loopback_tcp() -> bool:
    """Fail fast if local loopback TCP sockets (required by pyzmq/ipykernel) are blocked."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        cli.settimeout(1.0)
        cli.connect(("127.0.0.1", port))
        return True
    except OSError as exc:
        print(
            f"ERROR: Localhost TCP loopback socket is blocked ({exc}). "
            "Jupyter/pyzmq kernel execution cannot run in an isolated socket environment.",
            file=sys.stderr,
        )
        return False
    finally:
        cli.close()
        srv.close()


book_dir = Path(__file__).resolve().parent
os.chdir(book_dir)

cache_dirs = {
    "MPLCONFIGDIR": book_dir / ".mplcache",
    "IPYTHONDIR": book_dir / ".ipython",
    "JUPYTER_CONFIG_DIR": book_dir / ".jupyter",
    "JUPYTER_DATA_DIR": book_dir / ".jupyter_data",
    "JUPYTER_RUNTIME_DIR": book_dir / ".jupyter_runtime",
}

for var, p in cache_dirs.items():
    p.mkdir(parents=True, exist_ok=True)
    os.environ[var] = str(p)

os.environ.setdefault("PYTHONUTF8", "1")

if not _verify_loopback_tcp():
    sys.exit(1)

venv_jb = Path(sys.executable).parent / "jupyter-book.exe"
jb_exe = str(venv_jb) if venv_jb.exists() else (shutil.which("jupyter-book") or "jupyter-book")
print(f"Starting Jupyter-Book ({jb_exe}) build with isolated cache config...")
cmd = [jb_exe, "build", "."]
result = subprocess.run(cmd)
sys.exit(result.returncode)
