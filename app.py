import os
import subprocess
from urllib.parse import urlparse
from flask import Flask, request, jsonify

app = Flask(__name__)

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/media/youtube_downloads")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "url is required"}), 400

    url = data["url"]
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return jsonify({"error": "invalid url"}), 400

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    try:
        result = subprocess.run(
            ["yt-dlp", "-o", f"{DOWNLOAD_DIR}/%(title)s.%(ext)s", url],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return jsonify({"status": "success", "output": result.stdout})
        return jsonify({"error": result.stderr}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"error": "download timed out"}), 504
    except FileNotFoundError:
        return jsonify({"error": "yt-dlp not found"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
