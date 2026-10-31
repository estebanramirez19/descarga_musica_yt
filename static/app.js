const form = document.querySelector('#download-form');
const urlInput = document.querySelector('#url');
const statusEl = document.querySelector('#form-status');

form.addEventListener('submit', async event => {
  event.preventDefault(); statusEl.textContent = 'Preparando el MP3… Esto puede tardar un momento.';
  const button = form.querySelector('button'); button.disabled = true;
  try {
    const response = await fetch('/api/download', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url:urlInput.value})});
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || data.detail || 'No se pudo descargar el audio.');
    }
    const disposition = response.headers.get('Content-Disposition') || '';
    const match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    const filename = match ? decodeURIComponent(match[1]) : 'audio.mp3';
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl; link.download = filename; document.body.appendChild(link); link.click(); link.remove();
    URL.revokeObjectURL(objectUrl);
    urlInput.value = '';
    statusEl.textContent = 'Descarga lista.';
  } catch (error) { statusEl.textContent = error.message; }
  finally { button.disabled = false; }
});
