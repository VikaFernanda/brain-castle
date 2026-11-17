import { html } from '../html.js';
import { Button } from './Button.js';

export function ConfirmDialog({ text, onYes, onCancel, yesLabel = 'Yes, delete', noLabel = 'Keep it' }) {
  return html`<div onClick=${onCancel} style="position:fixed;inset:0;background:rgba(60,30,45,.4);z-index:60;display:flex;align-items:center;justify-content:center;padding:16px">
    <div class="card" role="alertdialog" aria-modal="true" aria-label="Confirm" onClick=${(e) => e.stopPropagation()} style="width:100%;max-width:400px;padding:24px;display:flex;flex-direction:column;gap:16px">
      <h2 style="font-size:22px">Are you sure?</h2>
      <div style="color:var(--muted);font-weight:600;line-height:1.45">${text}</div>
      <div style="display:flex;justify-content:flex-end;gap:10px">
        <${Button} onClick=${onCancel}>${noLabel}<//>
        <${Button} variant="primary" onClick=${onYes}>${yesLabel}<//>
      </div>
    </div>
  </div>`;
}
