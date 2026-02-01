import sys
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent / "Backend"
sys.path.insert(0, str(backend_path))