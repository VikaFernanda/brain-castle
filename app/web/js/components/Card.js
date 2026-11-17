import { html } from '../html.js';

export function Card({ children, style, tag = 'div', class: cls, ...rest }) {
  const T = tag;
  return html`<${T} class=${'card' + (cls ? ' ' + cls : '')} style=${style} ...${rest}>${children}</${T}>`;
}
