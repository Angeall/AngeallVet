// Escape a value for safe interpolation into an HTML string. Used by the print
// helpers that build markup with `document.write` (client/clinic names, notes and
// templates are free-text set by staff, so they must never be injected raw).
const ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ENTITIES[c]);
}

export default escapeHtml;
