"""Create a local environment and launch the complete teaching product."""

import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        raise SystemExit("Use Python 3.11, 3.12, or 3.13")
    folder = ROOT / ".venv"
    python = folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(folder)
    subprocess.run([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], check=True)
    subprocess.run([str(python), "-m", "scripts.engine_setup"], cwd=ROOT, check=True)
    subprocess.run(
        [str(python), "-m", "streamlit", "run", "app.py", "--server.address=127.0.0.1", "--server.port=8530"],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
