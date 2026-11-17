import { html } from '../html.js';
import { Icon } from './Icon.js';

// variant: '' | 'primary' | 'yellow' | 'danger'. min-height 44px comes from .btn.
export function Button({ variant = '', icon, children, style, class: cls, ...rest }) {
  const c = ['btn', variant && 'btn-' + variant, cls].filter(Boolean).join(' ');
  return html`<button type="button" class=${c} style=${style} ...${rest}>${icon ? html`<${Icon} name=${icon} />` : null}${children}</button>`;
}
