"""Central configuration. Override with environment variables (see .env.example)."""
from __future__ import annotations
import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Optional sample snapshot preloaded at startup. The data folder is git-ignored (business data).
DEFAULT_SNAPSHOT = Path(os.getenv("SPI_DEFAULT_FILE", BACKEND_ROOT / "data" / "SUP_15505_1_52_202637.xls"))
PORT = int(os.getenv("PORT", "8080"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5174,http://127.0.0.1:5174").split(",")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "25"))
