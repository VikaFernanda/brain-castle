import { html } from '../html.js';

export function Toast({ message }) {
  if (!message) return null;
  return html`<div role="status" style="position:fixed;left:24px;bottom:24px;z-index:40;background:var(--surface);border:1.5px solid var(--strong);border-radius:16px;padding:10px 16px;font-weight:700;box-shadow:0 6px 20px rgba(60,30,45,.18)">${message}</div>`;
}
