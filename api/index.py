"""Función Python de Vercel para generar y transmitir un MP3 temporal."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote, urlparse

import imageio_ffmpeg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


app = FastAPI()
PROJECT_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=PROJECT_DIR / "static"), name="static")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


class DownloadRequest(BaseModel):
    url: str


@app.get("/", response_class=FileResponse)
def home() -> FileResponse:
    return FileResponse(PROJECT_DIR / "templates" / "index.html", media_type="text/html")


def is_youtube_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and (parsed.hostname or "").lower() in YOUTUBE_HOSTS
    except ValueError:
        return False


@app.post("/api/download")
def download_audio(payload: DownloadRequest) -> StreamingResponse:
    url = payload.url.strip().replace("music.youtube.com", "www.youtube.com", 1)
    if not is_youtube_url(url):
        raise HTTPException(status_code=400, detail="Ingresa un enlace válido de YouTube.")

    temp_dir = tempfile.mkdtemp(prefix="pulso-", dir="/tmp")
    command = [
        "yt-dlp",
        "--no-warnings",
        "--no-playlist",
        "--extractor-args", "youtube:player_client=web,android",
        "--retries", "10",
        "--fragment-retries", "10",
        "--ffmpeg-location", imageio_ffmpeg.get_ffmpeg_exe(),
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--embed-metadata",
        "-o", f"{temp_dir}/%(title)s.%(ext)s",
        url,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=240)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip().splitlines()
            raise HTTPException(status_code=502, detail=(detail[-1] if detail else "No se pudo descargar el audio.")[:300])
        files = list(Path(temp_dir).glob("*.mp3"))
        if not files:
            raise HTTPException(status_code=502, detail="No se generó el archivo MP3.")
        audio_file = files[0]
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=504, detail="La descarga tardó demasiado y fue cancelada.") from exc
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    def stream_file():
        try:
            with audio_file.open("rb") as source:
                while chunk := source.read(64 * 1024):
                    yield chunk
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return StreamingResponse(
        stream_file(),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(audio_file.name)}",
            "Cache-Control": "no-store",
        },
    )
