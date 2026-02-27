"""Dev entry: run Flask app from repo root (app lives in yt-dlp-api/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "yt-dlp-api"))

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
