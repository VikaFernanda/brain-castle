// Note modal and Book modal. Markup copied from the design's edit modal.
import { html } from '../html.js';
import { Modal } from '../components/Modal.js';
import { Button } from '../components/Button.js';
import { RichEditor } from '../components/RichEditor.js';
import { PAL, PALN } from '../mock-data.js';

function Footer({ md, A, onSave }) {
  const isEdit = !!md.id;
  return html`<div style="display:flex;flex-direction:column;gap:16px">
    ${md.err ? html`<div role="alert" style="color:var(--strong);font-weight:800">${md.err}</div>` : null}
    <div style="display:flex;flex-wrap:wrap;justify-content:flex-end;gap:10px">
      ${isEdit ? html`<${Button} onClick=${A.archiveFromModal}>Archive<//><${Button} variant="danger" onClick=${A.deleteFromModal}>Delete<//><span style="flex:1"></span>` : null}
      <${Button} onClick=${A.closeModal}>Cancel<//>
      <${Button} variant="primary" onClick=${onSave}>${isEdit ? 'Save changes' : 'Create'}<//>
    </div>
  </div>`;
}

export function NoteModal({ s, A }) {
  const md = s.modal;
  const books = s.books.filter((b) => !b.archived);
  return html`<${Modal} heading=${md.id ? 'Edit note' : 'New note'} onClose=${A.closeModal}>
    <label class="lbl">Note title
      <input class="field" type="text" value=${md.title} placeholder="Give this note a title" onInput=${(e) => A.setModal({ title: e.target.value, err: '' })} />
    </label>
    <div style="display:flex;flex-wrap:wrap;gap:12px">
      <label class="lbl" style="flex:1 1 200px">Book
        <select class="field" value=${md.bookId} onChange=${(e) => A.setModal({ bookId: e.target.value, err: '' })}>
          ${books.length ? books.map((b) => html`<option key=${b.id} value=${b.id}>${b.name}</option>`) : html`<option value="">No books yet</option>`}
        </select>
      </label>
      <label class="lbl" style="flex:1 1 160px">Date (optional)
        <input class="field" type="date" value=${md.date} onInput=${(e) => A.setModal({ date: e.target.value })} />
      </label>
    </div>
    <${RichEditor} md=${md} A=${A} label="Your note" />
    <div style="display:flex;flex-direction:column;gap:8px">
      <span style="font-weight:700;font-size:14px">Tags</span>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        ${s.tags.map((g) => { const on = md.tags.includes(g.id); return html`<button type="button" key=${g.id} class="tagbtn" aria-pressed=${on} onClick=${() => A.setModal({ tags: on ? md.tags.filter((x) => x !== g.id) : [...md.tags, g.id] })} style=${'background:' + g.color + ';' + (on ? 'outline:3px solid var(--strong);outline-offset:1px' : 'opacity:.6')}>${g.name}</button>`; })}
        ${s.tags.length === 0 ? html`<span style="color:var(--muted);font-size:14px;font-weight:600">No tags yet. Make your first one below.</span>` : null}
      </div>
      <div style="display:flex;gap:8px">
        <input class="field" type="text" aria-label="New tag name" placeholder="New tag name" value=${md.newTag} onInput=${(e) => A.setModal({ newTag: e.target.value })} />
        <${Button} onClick=${A.addTagToModal}>Add tag<//>
      </div>
    </div>
    <${Footer} md=${md} A=${A} onSave=${A.saveNote} />
  <//>`;
}

export function BookModal({ s, A }) {
  const md = s.modal;
  return html`<${Modal} heading=${md.id ? 'Edit book' : 'New book'} onClose=${A.closeModal}>
    <label class="lbl">Book name
      <input class="field" type="text" value=${md.title} placeholder="For example, Travel Diary" onInput=${(e) => A.setModal({ title: e.target.value, err: '' })} />
    </label>
    <label class="lbl">Date (optional)
      <input class="field" type="date" value=${md.date} onInput=${(e) => A.setModal({ date: e.target.value })} />
    </label>
    <div style="display:flex;flex-direction:column;gap:8px">
      <span style="font-weight:700;font-size:14px">Color</span>
      <div style="display:flex;flex-wrap:wrap;gap:10px">
        ${PAL.map((c, i) => html`<button type="button" key=${c} aria-label=${PALN[i]} aria-pressed=${md.color === c} onClick=${() => A.setModal({ color: c })} style=${'width:40px;height:40px;border-radius:50%;border:2px solid var(--ink);cursor:pointer;background:' + c + ';' + (md.color === c ? 'outline:3px solid var(--strong);outline-offset:2px' : '')}></button>`)}
      </div>
    </div>
    <${Footer} md=${md} A=${A} onSave=${A.saveBook} />
  <//>`;
}
