import { html } from '../html.js';
import { Button } from './Button.js';

// UI only for now: it shows the bar and calls the handlers it gets. Real actions come with the pages.
// moveOptions: [{ value, label }] with a first empty "Move to..." option; null hides the select.
export function BulkBar({ count, moveOptions, moveLabel, onMove, onArchive, onDelete, onClear, onSelectAll, selectAllLabel = 'Select all' }) {
  if (!count) return null;
  return html`<div role="region" aria-label="Bulk actions" style="position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:30;max-width:calc(100% - 24px);display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:10px;padding:10px 14px;background:var(--ink);color:#fff;border-radius:24px;box-shadow:0 10px 30px rgba(40,20,30,.3)">
    <span style="font-weight:800;padding:0 6px">${count} selected</span>
    ${moveOptions ? html`<select class="field" aria-label=${moveLabel} value="" onChange=${onMove} style="width:180px;border-radius:999px">${moveOptions.map((o) => html`<option key=${o.value} value=${o.value}>${o.label}</option>`)}</select>` : null}
    <${Button} variant="yellow" icon="archive" onClick=${onArchive}>Archive<//>
    <${Button} variant="danger" icon="trash" onClick=${onDelete}>Delete<//>
    <${Button} onClick=${onClear}>Clear<//>
    ${onSelectAll ? html`<${Button} onClick=${onSelectAll}>${selectAllLabel}<//>` : null}
  </div>`;
}
