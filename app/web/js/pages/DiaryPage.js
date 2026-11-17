// Diary area: header, period row, list of books, board of book covers, and one open book.
// Markup copied from the design's showDiary block.
import { Fragment } from 'preact';
import { html } from '../html.js';
import { Icon } from '../components/Icon.js';
import { Button } from '../components/Button.js';
import { IconButton } from '../components/IconButton.js';
import { Segmented } from '../components/Segmented.js';
import { fmt } from '../lib/dates.js';
import { buildDiaryView, DSORT_OPTIONS, countLabel, excerpt, firstImg } from '../diary/view.js';

const SEL_ON = 'background:var(--strong);border-color:var(--strong)';
const SEL_OFF = 'background:var(--surface);border-color:var(--muted)';
const CHECK = '<path d="M5 12.5l4.5 4.5L19 7.5"></path>';
const INSERT = 'box-shadow:0 -5px 0 0 var(--strong),0 3px 0 var(--line);';

const Sq = ({ id, label, s, A, style }) => html`<button type="button" class="sq" aria-label=${label} aria-pressed=${!!s.sel[id]} onClick=${() => A.toggleSel(id)} style=${(style || '') + (s.sel[id] ? SEL_ON : SEL_OFF)}><svg class="i" viewBox="0 0 24 24" aria-hidden="true" style=${'width:14px;height:14px;opacity:' + (s.sel[id] ? 1 : 0)} dangerouslySetInnerHTML=${{ __html: CHECK }}></svg></button>`;

const NoteChips = ({ n, s }) => (n.tags || []).map((id) => s.tags.find((g) => g.id === id)).filter(Boolean).map((g) => html`<span key=${g.id} class="chip" style=${'background:' + g.color}>${g.name}</span>`);

function noteStyle(n, s) {
  return (s.sel[n.id] ? 'outline:3px solid var(--strong);' : '') + (s.dragId === n.id ? 'opacity:.45;' : '') + (s.overKey === 'c' + n.id && s.dragId && s.dragId !== n.id ? INSERT : '');
}
const noteDrag = (n, A) => ({ draggable: 'true', onDragStart: A.dragStart(n.id), onDragEnd: A.dragEnd, onDragOver: A.over('c' + n.id), onDragLeave: A.leave('c' + n.id), onDrop: A.dropOnNote(n) });

function NoteActions({ n, A, style }) {
  return html`<div class="acts" style=${style}>
    <${IconButton} icon="edit" label="Edit note" onClick=${() => A.openNote(n.id)} />
    <${IconButton} icon="archive" label="Archive note" onClick=${() => A.archive(n.id)} />
    <${IconButton} icon="trash" label="Delete note" onClick=${() => A.askDeleteNote(n.id)} />
  </div>`;
}
function BookActions({ b, A, withAdd }) {
  return html`<${Fragment}>
    ${withAdd ? html`<${IconButton} icon="plus" label="Add note to this book" onClick=${() => A.openNote(null, b.id)} />` : null}
    <${IconButton} icon="edit" label="Edit book" onClick=${() => A.openBookModal(b.id)} />
    <${IconButton} icon="archive" label="Archive book" onClick=${() => A.archive(b.id)} />
    <${IconButton} icon="trash" label="Delete book" onClick=${() => A.askDeleteBook(b.id)} />
  </${Fragment}>`;
}

// ---- list view ----
function ListNote({ n, s, A }) {
  return html`<div ...${noteDrag(n, A)} style=${'display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:8px 8px 8px 14px;border-radius:14px;background:var(--bg);border:1.5px solid var(--line);cursor:grab;' + noteStyle(n, s)}>
    ${s.selMode ? html`<${Sq} id=${n.id} label="Select note" s=${s} A=${A} />` : null}
    <div class="acts" style="opacity:1;color:var(--muted)"><${Icon} name="grip" /></div>
    <div style="flex:1 1 220px;min-width:0;display:flex;flex-direction:column;gap:2px">
      <button type="button" class="link" onClick=${() => A.openNote(n.id)}>${n.title}</button>
      <span class="clamp" style="font-size:13px;color:var(--muted);-webkit-line-clamp:1">${excerpt(n.body)}</span>
    </div>
    <${NoteChips} n=${n} s=${s} />
    ${n.date ? html`<span style="font-size:13px;font-weight:700;color:var(--muted)">${fmt(n.date)}</span>` : null}
    <${NoteActions} n=${n} A=${A} style="opacity:1" />
  </div>`;
}

function ListBook({ row, s, A }) {
  const b = row.book;
  const over = s.overKey === 'b' + b.id;
  return html`<section class="card" aria-label=${b.name} onDragOver=${A.over('b' + b.id)} onDragLeave=${A.leave('b' + b.id)} onDrop=${A.dropOnBook(b.id)} style=${'overflow:hidden;' + (over ? 'border:2px dashed var(--strong);background:var(--accent2-soft);' : '') + (s.sel[b.id] ? 'outline:3px solid var(--strong);' : '')}>
    <div draggable="true" onDragStart=${A.dragStart(b.id)} onDragEnd=${A.dragEnd} style="display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:8px 10px 8px 14px;cursor:grab">
      ${s.selMode ? html`<${Sq} id=${b.id} label="Select book" s=${s} A=${A} />` : null}
      <button type="button" class="ib" aria-label="Show or hide notes" aria-expanded=${row.open} onClick=${() => A.toggleOpen(b.id)}><svg class="i" viewBox="0 0 24 24" aria-hidden="true" style=${'transform:rotate(' + (row.open ? 90 : 0) + 'deg);transition:transform .15s'}><path d="M9 6l6 6-6 6"></path></svg></button>
      <span style=${'width:14px;height:26px;border-radius:5px;border:1.5px solid var(--ink);background:' + b.color}></span>
      <button type="button" class="link" onClick=${() => A.toggleOpen(b.id)} style="font-family:Fredoka,system-ui,sans-serif;font-size:20px;font-weight:600">${b.name}</button>
      <span style="color:var(--muted);font-size:14px;font-weight:600">${countLabel(row.all.length)}</span>
      ${b.date ? html`<span class="chip" style="background:var(--accent2-soft)">${fmt(b.date)}</span>` : null}
      <span style="flex:1"></span>
      <div style="display:flex;align-items:center"><${BookActions} b=${b} A=${A} withAdd=${true} /></div>
    </div>
    ${row.open ? html`<div style="padding:2px 14px 14px 52px;display:flex;flex-direction:column;gap:8px">
      ${row.shown.map((n) => html`<${ListNote} key=${n.id} n=${n} s=${s} A=${A} />`)}
      ${row.shown.length === 0 ? html`<div style="color:var(--muted);font-weight:600;font-size:14px;padding:6px 0">No notes in this book yet. Drag one here or press the plus.</div>` : null}
    </div>` : null}
  </section>`;
}

// ---- board of book covers ----
function Cover({ row, s, A }) {
  const b = row.book;
  const over = s.overKey === 'b' + b.id;
  return html`<div class="card" draggable="true" onDragStart=${A.dragStart(b.id)} onDragEnd=${A.dragEnd} onDragOver=${A.over('b' + b.id)} onDragLeave=${A.leave('b' + b.id)} onDrop=${A.dropOnBook(b.id)} style=${'position:relative;overflow:hidden;' + (s.sel[b.id] ? 'outline:3px solid var(--strong);' : '') + (over ? 'border:2px dashed var(--strong);' : '') + (s.dragId === b.id ? 'opacity:.45;' : '')}>
    <button type="button" onClick=${() => A.openBookView(b.id)} aria-label=${'Open book ' + b.name} style="display:flex;width:100%;border:0;background:transparent;padding:0;text-align:left;cursor:pointer;color:var(--ink);min-height:190px">
      <span style=${'width:22px;flex:none;background:' + b.color + ';border-right:2px solid var(--ink)'}></span>
      <span style="display:flex;flex-direction:column;gap:8px;padding:18px 16px;flex:1;min-width:0">
        <span style="font-family:Fredoka,system-ui,sans-serif;font-size:22px;font-weight:600;line-height:1.15;padding-right:20px">${b.name}</span>
        <span style="color:var(--muted);font-size:14px;font-weight:700">${countLabel(row.all.length)}</span>
        ${b.date ? html`<span class="chip" style="background:var(--accent2-soft);align-self:flex-start">${fmt(b.date)}</span>` : null}
        <span style="display:flex;flex-direction:column;gap:4px;margin-top:auto;font-size:13px;color:var(--muted)">
          ${row.all.slice(0, 3).map((n) => html`<span key=${n.id} style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${n.title}</span>`)}
        </span>
      </span>
    </button>
    ${s.selMode ? html`<${Sq} id=${b.id} label="Select book" s=${s} A=${A} style="position:absolute;top:12px;right:12px;" />` : null}
    <div class="acts" style="position:absolute;bottom:6px;right:6px;background:var(--surface);border-radius:12px"><${BookActions} b=${b} A=${A} /></div>
  </div>`;
}

function BookGrid({ view, s, A }) {
  return html`<${Fragment}>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:18px">
      ${view.flow.map((f) => f.kind === 'month' ? html`<h2 key=${f.key} style="grid-column:1 / -1;font-size:26px;margin-top:8px">${f.label}</h2>`
        : f.kind === 'week' ? html`<div key=${f.key} style="grid-column:1 / -1;font-weight:800;color:var(--muted);font-size:14px">${f.label}</div>`
        : html`<${Cover} key=${f.key} row=${f.row} s=${s} A=${A} />`)}
    </div>
    ${view.rows.length === 0 ? html`<div class="card" style="padding:32px;text-align:center;color:var(--muted);font-weight:700">${view.emptyText}</div>` : null}
  </${Fragment}>`;
}

// ---- one open book ----
function NoteCard({ n, color, s, A }) {
  const thumb = firstImg(n.images, n.body);
  return html`<article class="card" ...${noteDrag(n, A)} style=${'overflow:hidden;display:flex;flex-direction:column;cursor:grab;' + noteStyle(n, s)}>
    <div style=${'height:10px;background:' + color}></div>
    ${thumb ? html`<img src=${thumb} alt="" style="width:100%;height:120px;object-fit:cover;display:block" />` : null}
    <div style="padding:14px 14px 8px 16px;display:flex;flex-direction:column;gap:8px;flex:1">
      <div style="display:flex;align-items:flex-start;gap:8px">
        <button type="button" class="link" onClick=${() => A.openNote(n.id)} style="flex:1;font-family:Fredoka,system-ui,sans-serif;font-size:19px;font-weight:600">${n.title}</button>
        ${s.selMode ? html`<${Sq} id=${n.id} label="Select note" s=${s} A=${A} />` : null}
      </div>
      <span class="clamp" style="font-size:14px;color:var(--muted);line-height:1.45">${excerpt(n.body)}</span>
      <div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:auto">
        <${NoteChips} n=${n} s=${s} />
        ${n.date ? html`<span style="font-size:13px;font-weight:700;color:var(--muted)">${fmt(n.date)}</span>` : null}
      </div>
    </div>
    <${NoteActions} n=${n} A=${A} style="justify-content:flex-end;padding:0 6px 6px" />
  </article>`;
}

function OpenBook({ view, s, A }) {
  const b = view.openB;
  return html`<div style="display:flex;flex-direction:column;gap:18px">
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:12px">
      <${Button} icon="chevronLeft" onClick=${A.closeBook}>All books<//>
      <span style=${'width:14px;height:30px;border-radius:5px;border:1.5px solid var(--ink);background:' + b.color}></span>
      <span style="color:var(--muted);font-weight:700">${countLabel(view.openAll.length)}</span>
      <span style="flex:1"></span>
      <${Button} variant="primary" icon="plus" onClick=${() => A.openNote(null, b.id)}>Note in this book<//>
    </div>
    ${view.otherBooks.length ? html`<div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px">
      <span style="font-size:13px;font-weight:700;color:var(--muted)">Drag a note onto a book to move it:</span>
      ${view.otherBooks.map((o) => html`<div key=${o.id} onDragOver=${A.over('o' + o.id)} onDragLeave=${A.leave('o' + o.id)} onDrop=${A.dropOnChip(o.id)} style=${'display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border-radius:999px;border:2px dashed var(--line);font-weight:700;font-size:14px;' + (s.overKey === 'o' + o.id ? 'border-color:var(--strong);background:var(--accent2-soft)' : '')}>
        <span style=${'width:10px;height:18px;border-radius:4px;background:' + o.color + ';border:1.5px solid var(--ink)'}></span>${o.name}
      </div>`)}
    </div>` : null}
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px">
      ${view.openShown.map((n) => html`<${NoteCard} key=${n.id} n=${n} color=${b.color} s=${s} A=${A} />`)}
    </div>
    ${view.openShown.length === 0 ? html`<div class="card" style="padding:32px;text-align:center;color:var(--muted);font-weight:700">This book is empty. Write the first page with the button above.</div>` : null}
  </div>`;
}

export function DiaryPage({ s, A }) {
  const view = buildDiaryView(s);
  const scopes = [{ value: 'all', label: 'All time' }, { value: 'month', label: 'Month' }, { value: 'week', label: 'Week' }];
  const noteTarget = view.openB ? view.openB.id : null;
  return html`<${Fragment}>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:12px 16px">
      <div style="flex:1 1 240px">
        <h1 style="font-size:34px">${view.title}</h1>
        <div style="color:var(--muted);font-weight:600">${view.sub}</div>
      </div>
      <${Segmented} label="Diary view" value=${s.dview} onChange=${A.setView} options=${[{ value: 'list', label: 'List', icon: 'list' }, { value: 'board', label: 'Board', icon: 'grid' }]} />
      <${Button} aria-pressed=${s.selMode} onClick=${A.toggleSelMode} style=${s.selMode ? 'background:var(--accent2)' : ''}>${s.selMode ? 'Done selecting' : 'Select'}<//>
      <${Button} icon="diary" onClick=${() => A.openBookModal(null)}>New book<//>
      <${Button} variant="primary" icon="plus" onClick=${() => A.openNote(null, noteTarget)}>New note<//>
      <div role="group" aria-label="Filter by tag" style="display:flex;flex-wrap:wrap;align-items:center;gap:8px">
        <button type="button" class="tagbtn" aria-pressed=${!s.tagF} onClick=${() => A.setTag(null)} style=${'background:var(--accent-soft);' + (!s.tagF ? 'outline:3px solid var(--strong);outline-offset:1px' : '')}>All</button>
        ${s.tags.map((g) => html`<button type="button" key=${g.id} class="tagbtn" aria-pressed=${s.tagF === g.id} onClick=${() => A.setTag(s.tagF === g.id ? null : g.id)} style=${'background:' + g.color + ';' + (s.tagF === g.id ? 'outline:3px solid var(--strong);outline-offset:1px' : '')}>${g.name}</button>`)}
        <button type="button" class="tagbtn" onClick=${A.openTags} style="background:transparent;border:1.5px dashed var(--muted);color:var(--ink)">Manage tags</button>
      </div>
    </div>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px">
      <${Segmented} label="Period" value=${s.bscope} onChange=${A.setScope} options=${scopes} />
      <div style="display:inline-flex;align-items:center;gap:2px">
        <${IconButton} icon="chevronLeft" label="Previous" onClick=${() => A.step(-1)} />
        <span style="min-width:150px;text-align:center;font-weight:800">${view.periodLabel}</span>
        <${IconButton} icon="chevronRight" label="Next" onClick=${() => A.step(1)} />
      </div>
      <${Button} onClick=${A.today} style="min-height:40px">Today<//>
      <label class="mini"><span>Books</span>
        <select class="field" aria-label="Sort books" value=${s.bsort} onChange=${(e) => A.setBSort(e.target.value)}>
          ${DSORT_OPTIONS.map((o) => html`<option key=${o.value} value=${o.value}>${o.label}</option>`)}
        </select>
      </label>
      <label class="mini">Notes
        <select class="field" aria-label="Sort notes inside books" value=${s.nsort} onChange=${(e) => A.setNSort(e.target.value)}>
          ${DSORT_OPTIONS.map((o) => html`<option key=${o.value} value=${o.value}>${o.label}</option>`)}
        </select>
      </label>
    </div>
    ${view.openB ? html`<${OpenBook} view=${view} s=${s} A=${A} />`
      : s.dview === 'board' ? html`<${BookGrid} view=${view} s=${s} A=${A} />`
      : html`<div style="display:flex;flex-direction:column;gap:14px">
        ${view.flow.map((f) => f.kind === 'month' ? html`<h2 key=${f.key} style="font-size:26px;margin-top:8px">${f.label}</h2>`
          : f.kind === 'week' ? html`<div key=${f.key} style="font-weight:800;color:var(--muted);font-size:14px">${f.label}</div>`
          : html`<${ListBook} key=${f.key} row=${f.row} s=${s} A=${A} />`)}
        ${view.rows.length === 0 ? html`<div class="card" style="padding:32px;text-align:center;color:var(--muted);font-weight:700">${view.emptyText}</div>` : null}
      </div>`}
  </${Fragment}>`;
}

export { buildDiaryView };
