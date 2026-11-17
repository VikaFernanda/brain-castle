// Every SVG icon of the design lives here, copied as-is. Rule: an icon always has a fixed size
// (the .i class sets 18px) and flex:none, so it can never grow or leave its button.
import { html } from '../html.js';

const P = {
  chevronRight: '<path d="M9 6l6 6-6 6"></path>',
  chevronLeft: '<path d="M15 6l-6 6 6 6"></path>',
  search: '<circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path>',
  close: '<path d="M6 6l12 12M18 6L6 18"></path>',
  palette: '<path d="M12 3a9 9 0 100 18c1.4 0 2-1 1.6-2.1-.4-1.1.3-2.4 1.7-2.4H17a4 4 0 004-4c0-5-4-9.5-9-9.5z"></path><circle cx="7.5" cy="11" r="1"></circle><circle cx="10.5" cy="7" r="1"></circle><circle cx="15.5" cy="7.5" r="1"></circle>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"></path>',
  tasks: '<circle cx="12" cy="12" r="9"></circle><path d="M8 12.5l3 3 5-6"></path>',
  diary: '<path d="M5 4h11a3 3 0 013 3v13H8a3 3 0 01-3-3z"></path><path d="M5 17a3 3 0 013-3h11"></path>',
  archive: '<rect x="3" y="4" width="18" height="4" rx="1"></rect><path d="M5 8v11a1 1 0 001 1h12a1 1 0 001-1V8"></path><path d="M10 12h4"></path>',
  list: '<path d="M8 6h13M8 12h13M8 18h13"></path><circle cx="3.5" cy="6" r="1"></circle><circle cx="3.5" cy="12" r="1"></circle><circle cx="3.5" cy="18" r="1"></circle>',
  calendarBoard: '<rect x="3" y="4" width="5" height="16" rx="1.5"></rect><rect x="10" y="4" width="5" height="10" rx="1.5"></rect><rect x="17" y="4" width="4" height="13" rx="1.5"></rect>',
  grid: '<rect x="3" y="4" width="8" height="7" rx="1.5"></rect><rect x="13" y="4" width="8" height="7" rx="1.5"></rect><rect x="3" y="13" width="8" height="7" rx="1.5"></rect><rect x="13" y="13" width="8" height="7" rx="1.5"></rect>',
  tag: '<path d="M3 12V4h8l10 10-8 8z"></path><circle cx="7.5" cy="8.5" r="1"></circle>',
  plus: '<path d="M12 5v14M5 12h14"></path>',
  clock: '<circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"></rect><circle cx="9" cy="10" r="1.5"></circle><path d="M21 16l-5-5-8 8"></path>',
  edit: '<path d="M12 20h9"></path><path d="M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4z"></path>',
  trash: '<path d="M4 7h16"></path><path d="M9 7V4h6v3"></path><path d="M6 7l1 13h10l1-13"></path>',
  restore: '<path d="M3 12a9 9 0 109-9 9 9 0 00-6.4 2.7L3 8"></path><path d="M3 3v5h5"></path>',
  grip: '<path d="M4 5h16M4 10h16M4 15h10"></path>',
  up: '<path d="M6 15l6-6 6 6"></path>',
  down: '<path d="M6 9l6 6 6-6"></path>'
};

export const ICON_NAMES = Object.keys(P);

// size: optional px number. Sets width AND height inline (same as the design's inline styles).
export function Icon({ name, size, style }) {
  const s = (size ? 'width:' + size + 'px;height:' + size + 'px;' : '') + (style || '');
  return html`<svg class="i" viewBox="0 0 24 24" aria-hidden="true" style=${s || undefined} dangerouslySetInnerHTML=${{ __html: P[name] }}></svg>`;
}

// Castle logo (top bar, 38px) and the empty-archive castle (56px). Colors come from theme tokens.
export function CastleLogo({ size = 38 }) {
  return html`<svg width=${size} height=${size} viewBox="0 0 32 32" aria-hidden="true" style="flex:none"><path d="M16 7V2.5l4.5 1.6L16 5.8" fill="var(--accent2)" stroke="var(--ink)" stroke-width="1.6" stroke-linejoin="round"></path><path d="M4 29V12h4V8h2v4h4V6h4v6h4V8h2v4h4v17z" fill="var(--accent)" stroke="var(--ink)" stroke-width="2" stroke-linejoin="round"></path><path d="M13 29v-6a3 3 0 016 0v6" fill="var(--accent2)" stroke="var(--ink)" stroke-width="2" stroke-linejoin="round"></path></svg>`;
}
export function CastleEmpty({ size = 56 }) {
  return html`<svg width=${size} height=${size} viewBox="0 0 32 32" aria-hidden="true" style="flex:none"><path d="M4 29V12h4V8h2v4h4V6h4v6h4V8h2v4h4v17z" fill="var(--accent2)" stroke="var(--ink)" stroke-width="2" stroke-linejoin="round"></path><path d="M13 29v-6a3 3 0 016 0v6" fill="var(--accent)" stroke="var(--ink)" stroke-width="2" stroke-linejoin="round"></path></svg>`;
}
