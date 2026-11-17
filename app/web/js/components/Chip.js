import { html } from '../html.js';

export function Chip({ bg, children, style }) {
  return html`<span class="chip" style=${'background:' + bg + ';' + (style || '')}>${children}</span>`;
}
