import { html } from '../html.js';
import { Icon } from './Icon.js';

// Fixed 40x40 (.ib). size 32 makes a 32px button with a 16px icon, like the compact cards in the design.
export function IconButton({ icon, label, size, style, ...rest }) {
  const st = (size ? 'width:' + size + 'px;height:' + size + 'px;' : '') + (style || '');
  return html`<button type="button" class="ib" aria-label=${label} style=${st || undefined} ...${rest}><${Icon} name=${icon} size=${size ? size / 2 : undefined} /></button>`;
}
