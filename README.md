# Pulso

Interfaz web privada para descargar audio desde YouTube y reproducir los MP3 guardados en `musica/`.

## Despliegue en Vercel

La versión web genera cada MP3 dentro del directorio temporal de una función, lo transmite al navegador y lo elimina. No incluye biblioteca ni reproductor y no conserva canciones en Vercel.

1. Sube el proyecto a un repositorio Git sin incluir `.venv`, `.env` ni `musica/`.
2. Importa el repositorio desde el panel de Vercel.
3. Mantén las opciones de compilación detectadas y despliega.

La función está configurada con un máximo de cinco minutos. YouTube puede bloquear solicitudes procedentes de centros de datos; si sucede, el despliegue necesitará un servicio de descarga externo.

Los navegadores guardan el archivo en su carpeta de descargas predeterminada o muestran el selector configurado por el usuario.

## Ejecución alternativa con Docker

### 1. Configurar credenciales

```bash
cp .env.example .env
```

Edita `.env` y usa una contraseña larga y única. El navegador solicitará estas credenciales al abrir Pulso.

### 2. Iniciar con Docker Compose

```bash
docker compose up -d --build
```

Abre `http://IP_DEL_SERVIDOR:8000`. El MP3 se genera temporalmente y se entrega al navegador.

Para ver el estado y los registros:

```bash
docker compose ps
docker compose logs -f pulso
```

### 3. Publicarlo con HTTPS

En un servidor público, coloca Caddy, Nginx o un proxy administrado delante del puerto 8000 y habilita HTTPS. No publiques Pulso sin definir `MUSICA_USERNAME` y `MUSICA_PASSWORD`.

## Ejecución local sin Docker

Necesitas Python 3, `yt-dlp` y `ffmpeg`:

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

Abre `http://127.0.0.1:8000`. En local, la autenticación queda desactivada si no defines las dos variables de credenciales.
