#!/usr/bin/env python3
"""Interfaz web para descargar un MP3 directamente al dispositivo."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import secrets
import subprocess
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from descargar_musica import construir_comando, normalizar_url


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = BASE_DIR / "templates" / "index.html"
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def is_youtube_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in YOUTUBE_HOSTS
    except ValueError:
        return False


class MusicHandler(BaseHTTPRequestHandler):
    server_version = "PulsoLocal/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def is_authorized(self) -> bool:
        username = os.environ.get("MUSICA_USERNAME")
        password = os.environ.get("MUSICA_PASSWORD")
        if not username or not password:
            return True
        try:
            scheme, encoded = self.headers.get("Authorization", "").split(" ", 1)
            supplied = base64.b64decode(encoded).decode("utf-8")
            supplied_username, supplied_password = supplied.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return False
        return (
            scheme.lower() == "basic"
            and secrets.compare_digest(supplied_username, username)
            and secrets.compare_digest(supplied_password, password)
        )

    def require_authorization(self) -> bool:
        if self.is_authorized():
            return True
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="Pulso", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if not self.require_authorization():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_file(INDEX_FILE, "text/html; charset=utf-8")
        elif parsed.path.startswith("/static/"):
            filename = Path(unquote(parsed.path.removeprefix("/static/"))).name
            self.send_file(STATIC_DIR / filename)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if not self.require_authorization():
            return
        if urlparse(self.path).path != "/api/download":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 16_384)
            payload = json.loads(self.rfile.read(length) or b"{}")
            url = str(payload.get("url", "")).strip()
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "Solicitud inválida."}, HTTPStatus.BAD_REQUEST)
            return
        if not is_youtube_url(url):
            self.send_json({"error": "Ingresa un enlace válido de YouTube."}, HTTPStatus.BAD_REQUEST)
            return
        try:
            with tempfile.TemporaryDirectory(prefix="pulso-") as temp_dir:
                command = construir_comando(normalizar_url(url), temp_dir)
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=240,
                )
                if result.returncode != 0:
                    detail = (result.stderr or result.stdout).strip().splitlines()
                    message = detail[-1] if detail else "No se pudo descargar el audio."
                    self.send_json({"error": message[:300]}, HTTPStatus.BAD_GATEWAY)
                    return
                files = list(Path(temp_dir).glob("*.mp3"))
                if not files:
                    self.send_json({"error": "No se generó el archivo MP3."}, HTTPStatus.BAD_GATEWAY)
                    return
                audio_file = files[0]
                size = audio_file.stat().st_size
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(size))
                self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(audio_file.name)}")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                with audio_file.open("rb") as source:
                    while chunk := source.read(64 * 1024):
                        self.wfile.write(chunk)
        except FileNotFoundError:
            self.send_json({"error": "No se encontró yt-dlp o ffmpeg."}, HTTPStatus.INTERNAL_SERVER_ERROR)
        except subprocess.TimeoutExpired:
            self.send_json({"error": "La descarga tardó demasiado y fue cancelada."}, HTTPStatus.GATEWAY_TIMEOUT)


def main() -> None:
    host = os.environ.get("MUSICA_HOST", "127.0.0.1")
    port = int(os.environ.get("MUSICA_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), MusicHandler)
    print(f"Pulso listo en http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
