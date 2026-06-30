// Déclenche le téléchargement d'une réponse axios récupérée en `responseType: 'blob'`.
// Réutilise le nom de fichier renvoyé par le serveur (Content-Disposition) si présent.
export function downloadBlob(res, fallbackName = 'export.xlsx') {
  const cd = res.headers?.['content-disposition'] || '';
  const match = /filename="?([^"]+)"?/.exec(cd);
  const name = match ? match[1] : fallbackName;
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  window.URL.revokeObjectURL(url);
}
