#!/usr/bin/env python3
"""
Script para descargar música de YouTube solo con el link.
Usa yt-dlp para extraer el audio en MP3 de la mejor calidad posible.
"""

import sys
import subprocess
from pathlib import Path


def normalizar_url(url: str) -> str:
    """Convierte URLs de YouTube Music a la URL principal de YouTube."""
    if "music.youtube.com" in url:
        return url.replace("music.youtube.com", "www.youtube.com", 1)
    return url


def construir_comando(url: str, carpeta_salida: str = ".", progress: bool = False) -> list[str]:
    """Construye el comando de yt-dlp usado tanto por la CLI como por la web."""
    cmd = [
        "yt-dlp",
        "--newline" if progress else "--no-warnings",
        "--extractor-args", "youtube:player_client=web,android",
        "--retries", "10",
        "--fragment-retries", "10",
        "--no-playlist",
        "--sleep-requests", "1",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--embed-thumbnail",
        "--embed-metadata",
        "-o", f"{carpeta_salida}/%(title)s.%(ext)s",
        url,
    ]
    return cmd


def descargar_audio(url: str, carpeta_salida: str = ".") -> None:
    """
    Descarga el audio de un video/playlist de YouTube y lo guarda como MP3.
    """
    Path(carpeta_salida).mkdir(parents=True, exist_ok=True)

    url_limpia = normalizar_url(url)

    cmd = construir_comando(url_limpia, carpeta_salida)

    print(f"Descargando audio de: {url_limpia}")
    try:
        subprocess.run(cmd, check=True)
        print("Descarga completada.")
    except subprocess.CalledProcessError as exc:
        print(
            "La descarga falló por bloqueo de YouTube. Intenta con una URL del sitio principal, "
            "actualiza yt-dlp y, si hace falta, usa cookies del navegador.",
            file=sys.stderr,
        )
        raise exc


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python descargar_musica.py <URL_de_Youtube> [carpeta_salida]")
        print("Ejemplo: python descargar_musica.py https://www.youtube.com/watch?v=XXXXX musica")
        sys.exit(1)

    url = sys.argv[1]
    carpeta = sys.argv[2] if len(sys.argv) > 2 else "."

    try:
        descargar_audio(url, carpeta)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar yt-dlp: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error inesperado: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
