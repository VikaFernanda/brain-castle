import { html } from '../html.js';
import { useEffect, useRef } from 'preact/hooks';
import { IconButton } from './IconButton.js';
import { useDialogFocus } from '../lib/focus.js';

// Overlay + card dialog, like the design's edit modal. Click outside or Escape closes it.
export function Modal({ heading, onClose, children, maxWidth = 720 }) {
  const box = useRef(null);
  useDialogFocus(box);
  useEffect(() => {
    const k = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', k);
    return () => document.removeEventListener('keydown', k);
  }, [onClose]);
  return html`<div onClick=${onClose} style="position:fixed;inset:0;background:rgba(60,30,45,.4);z-index:50;display:flex;align-items:flex-start;justify-content:center;padding:32px 16px;overflow-y:auto">
    <div class="card" ref=${box} tabindex="-1" role="dialog" aria-modal="true" aria-label=${heading} onClick=${(e) => e.stopPropagation()} style=${'width:100%;max-width:' + maxWidth + 'px;padding:24px;display:flex;flex-direction:column;gap:16px'}>
      <div style="display:flex;align-items:center;gap:12px">
        <h2 style="font-size:26px;flex:1">${heading}</h2>
        <${IconButton} icon="close" label="Close" onClick=${onClose} />
      </div>
      ${children}
    </div>
  </div>`;
}
