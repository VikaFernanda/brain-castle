import { html } from '../html.js';
import { Icon } from './Icon.js';

const ON = 'background:var(--surface);box-shadow:0 2px 0 var(--line)';

// options: [{ value, label, icon? }]. tone 'soft2' uses the yellow track (the "Show tasks" group).
export function Segmented({ options, value, onChange, label, tone }) {
  const track = tone === 'soft2' ? 'var(--accent2-soft)' : 'var(--accent-soft)';
  return html`<div role="group" aria-label=${label} style=${'display:inline-flex;background:' + track + ';border-radius:999px;padding:4px'}>
    ${options.map((o) => html`<button type="button" key=${o.value} class="seg" aria-pressed=${o.value === value} onClick=${() => onChange(o.value)} style=${o.value === value ? ON : ''}>${o.icon ? html`<${Icon} name=${o.icon} />` : null}${o.label}</button>`)}
  </div>`;
}
