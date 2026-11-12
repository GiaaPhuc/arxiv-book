import os
import sys
import shutil
import subprocess
from pathlib import Path

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

venv_jb = Path(sys.executable).parent / "jupyter-book.exe"
jb_exe = str(venv_jb) if venv_jb.exists() else (shutil.which("jupyter-book") or "jupyter-book")
print(f"Starting Jupyter-Book ({jb_exe}) build with isolated cache config...")
cmd = [jb_exe, "build", "."]
result = subprocess.run(cmd)
sys.exit(result.returncode)
