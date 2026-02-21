import os
import shlex
import subprocess
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/media/youtube_downloads")
YT_DLP_EXTRA_ARGS = os.environ.get("YT_DLP_EXTRA_ARGS", "")
DOWNLOAD_TIMEOUT = int(os.environ.get("DOWNLOAD_TIMEOUT", "3600"))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/download_video", methods=["POST"])
def download_video():
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' in request body"}), 400

    url = data["url"]
    if not isinstance(url, str) or not url.strip():
        return jsonify({"error": "Invalid 'url' value"}), 400

    output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    cmd = ["yt-dlp", "--no-playlist", "-o", output_template]

    if YT_DLP_EXTRA_ARGS:
        cmd += shlex.split(YT_DLP_EXTRA_ARGS)

    cmd.append(url)

    logger.info("Running: %s", " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=DOWNLOAD_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Download timed out"}), 504
    except Exception as exc:
        logger.exception("Unexpected error during download")
        return jsonify({"error": str(exc)}), 500

    if result.returncode != 0:
        logger.error("yt-dlp stderr: %s", result.stderr)
        return jsonify({"error": result.stderr.strip()}), 500

    return jsonify({"status": "downloaded", "output": result.stdout.strip()}), 200


if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
