"""Container startup: seed the persistent volume before starting the UI."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.engine_setup import seed
from signalstory.prom.engine import start_local_engine

seed(export=False)
if not start_local_engine():
    raise SystemExit("The fixture engine could not start")
os.execv(
    sys.executable,
    [sys.executable, "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8530"],
)
