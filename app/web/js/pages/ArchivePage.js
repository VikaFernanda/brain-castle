// Archive area. Markup copied from the design's showArchive block.
import { Fragment } from 'preact';
import { html } from '../html.js';
import { CastleEmpty } from '../components/Icon.js';
import { Button } from '../components/Button.js';
import { buildArchiveView } from '../archive/view.js';

const SEL_ON = 'background:var(--strong);border-color:var(--strong)';
const SEL_OFF = 'background:var(--surface);border-color:var(--muted)';
const CHECK = '<path d="M5 12.5l4.5 4.5L19 7.5"></path>';

function Row({ r, s, A }) {
  const on = !!s.sel[r.id];
  return html`<div class="card" style=${'display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:8px 10px 8px 14px;' + (on ? 'outline:3px solid var(--strong)' : '')}>
    <button type="button" class="sq" aria-label="Select item" aria-pressed=${on} onClick=${() => A.toggleSel(r.id)} style=${on ? SEL_ON : SEL_OFF}><svg class="i" viewBox="0 0 24 24" aria-hidden="true" style=${'width:14px;height:14px;opacity:' + (on ? 1 : 0)} dangerouslySetInnerHTML=${{ __html: CHECK }}></svg></button>
    <div style="flex:1 1 220px;min-width:0;display:flex;flex-direction:column">
      <span style="font-weight:700;font-size:16px">${r.title}</span>
      <span style="font-size:13px;color:var(--muted);font-weight:600">${r.meta}</span>
    </div>
    <${Button} icon="restore" onClick=${() => A.restoreOne(r.id)} style="min-height:40px;background:var(--accent2)">Restore<//>
    <${Button} variant="danger" icon="trash" onClick=${() => A.askDeleteOne(r.id)} style="min-height:40px">Delete forever<//>
  </div>`;
}

export function ArchivePage({ s, A }) {
  const v = buildArchiveView(s);
  const selCount = Object.keys(s.sel).length;
  const allSel = v.ids.length > 0 && v.ids.every((i) => s.sel[i]);
  return html`<${Fragment}>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:12px 12px">
      <div style="flex:1 1 240px">
        <h1 style="font-size:34px">Archive</h1>
        <div style="color:var(--muted);font-weight:600">${v.sub}</div>
      </div>
      <${Button} disabled=${v.empty} onClick=${() => A.selectAll(v.ids)}>${allSel ? 'Clear selection' : 'Select all'}<//>
      <${Button} variant="yellow" icon="restore" disabled=${selCount === 0} onClick=${A.restoreSel}>Restore selected<//>
      <${Button} variant="danger" icon="trash" disabled=${selCount === 0} onClick=${A.askDeleteSel}>Delete selected<//>
      <${Button} variant="primary" disabled=${v.empty} onClick=${() => A.restoreAll(v.ids)}>Restore all<//>
      <${Button} variant="danger" disabled=${v.empty} onClick=${() => A.askDeleteAll(v.ids)}>Delete all<//>
    </div>
    ${v.sections.map((x) => html`<section key=${x.key} aria-label=${x.title} style="display:flex;flex-direction:column;gap:10px">
      <h2 style="font-size:20px">${x.title} <span style="color:var(--muted);font-size:16px">${x.count}</span></h2>
      ${x.rows.map((r) => html`<${Row} key=${r.id} r=${r} s=${s} A=${A} />`)}
    </section>`)}
    ${v.empty ? html`<div class="card" style="padding:40px 24px;text-align:center;display:flex;flex-direction:column;align-items:center;gap:8px">
      <${CastleEmpty} />
      <h2 style="font-size:22px">The archive is empty</h2>
      <span style="color:var(--muted);font-weight:600">Archived tasks, notes and books wait here until you restore or delete them.</span>
    </div>` : null}
  </${Fragment}>`;
}
