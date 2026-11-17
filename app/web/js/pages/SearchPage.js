// Search results page. Markup copied from the design's isSearch block.
import { Fragment } from 'preact';
import { html } from '../html.js';
import { Icon } from '../components/Icon.js';
import { buildSearchView } from '../search/view.js';

export function SearchPage({ s, onOpen }) {
  const v = buildSearchView(s);
  return html`<${Fragment}>
    <div>
      <h1 style="font-size:34px">Search results</h1>
      <div style="color:var(--muted);font-weight:600">${v.sub}</div>
    </div>
    ${v.sections.map((x) => html`<section key=${x.key} aria-label=${x.title} style="display:flex;flex-direction:column;gap:10px">
      <h2 style="font-size:20px">${x.title} <span style="color:var(--muted);font-size:16px">${x.count}</span></h2>
      ${x.rows.map((r) => html`<button type="button" key=${r.id} class="card" onClick=${() => onOpen(r)} style="display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:12px 16px;text-align:left;cursor:pointer;color:var(--ink);width:100%;font-family:inherit">
        <span style="flex:1 1 220px;min-width:0;display:flex;flex-direction:column">
          <span style="font-weight:700;font-size:16px">${r.title}</span>
          <span style="font-size:13px;color:var(--muted);font-weight:600">${r.meta}</span>
        </span>
        ${r.tags.map((g) => html`<span key=${g.id} class="chip" style=${'background:' + g.color}>${g.name}</span>`)}
        <${Icon} name="chevronRight" style="color:var(--muted)" />
      </button>`)}
    </section>`)}
    ${v.empty ? html`<div class="card" style="padding:40px 24px;text-align:center;color:var(--muted);font-weight:700">Nothing found. Try another word or tag.</div>` : null}
  </${Fragment}>`;
}
