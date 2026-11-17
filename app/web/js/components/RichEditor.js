// The design's rich text part of the task and note modals: "Write" and "Preview and arrange"
// modes, the Add image button, and Move up / Move down / Remove on every preview block.
// Reads and writes md.text, md.images and md.tab of the open modal through A.setModal.
import { html } from '../html.js';
import { useRef, useState } from 'preact/hooks';
import { Icon } from './Icon.js';
import { splitBlocks, renderBlock } from '../markdown.js';
import { shrinkImage, imageToken, insertTokens, moveBlockText, removeBlockText } from '../lib/images.js';

const ON = 'background:var(--surface);box-shadow:0 2px 0 var(--line)';
const SMALL = 'font-size:12px;font-weight:600;color:var(--muted)';

export function RichEditor({ md, A, label }) {
  const [over, setOver] = useState(-1);
  const caret = useRef(null);
  const preview = md.tab === 'preview';
  const raw = splitBlocks(md.text || '');

  const add = async (files, where) => {
    const list = Array.from(files || []).filter((f) => /^image\//.test(f.type));
    if (!list.length) { A.toast('Only image files can be added'); return; }
    const ok = (await Promise.all(list.map(shrinkImage))).filter(Boolean);
    if (!ok.length) { A.toast('Could not read that image'); return; }
    caret.current = null;
    // Functional update: the user may have kept typing while the images were read.
    A.setModal((m) => {
      const images = { ...(m.images || {}) }; ok.forEach((r) => { images[r.id] = r.src; });
      return { images, text: insertTokens(m.text, ok.map(imageToken), where) };
    });
    A.toast(ok.length + (ok.length === 1 ? ' image added' : ' images added'));
  };
  const keepCaret = (e) => { caret.current = e.target.selectionStart; };
  const allow = (e) => e.preventDefault();
  const files = (e) => (e.dataTransfer && e.dataTransfer.files) || [];
  const dropText = (e) => { e.preventDefault(); e.stopPropagation(); if (files(e).length) add(files(e), { caret: caret.current }); };
  const dropBlock = (i) => (e) => { e.preventDefault(); e.stopPropagation(); setOver(-1); if (files(e).length) add(files(e), { block: i }); };
  const onPaste = (e) => { const f = e.clipboardData && e.clipboardData.files; if (f && f.length) { e.preventDefault(); add(f, { caret: e.target.selectionStart }); } };
  const mv = (i, d) => A.setModal((m) => ({ text: moveBlockText(m.text, i, d) }));
  const rm = (i) => A.setModal((m) => ({ text: removeBlockText(m.text, i) }));

  const IB = ({ icon, label: l, disabled, onClick }) => html`<button type="button" class="ib" aria-label=${l} disabled=${disabled} onClick=${onClick} style="width:32px;height:32px"><${Icon} name=${icon} size=${16} /></button>`;

  return html`<div style="display:flex;flex-direction:column;gap:8px">
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px">
      <span style="font-weight:700;font-size:14px;flex:1">${label}</span>
      <div role="group" aria-label="Editor mode" style="display:inline-flex;background:var(--accent-soft);border-radius:999px;padding:4px">
        <button type="button" class="seg" aria-pressed=${!preview} onClick=${() => A.setModal({ tab: 'write' })} style=${!preview ? ON : ''}>Write</button>
        <button type="button" class="seg" aria-pressed=${preview} onClick=${() => A.setModal({ tab: 'preview' })} style=${preview ? ON : ''}>Preview and arrange</button>
      </div>
      <label class="btn filebtn" style="position:relative;min-height:40px;cursor:pointer">
        <${Icon} name="image" />Add image
        <input type="file" accept="image/*" multiple onChange=${(e) => { add(e.target.files, { caret: caret.current }); e.target.value = ''; }} style="position:absolute;opacity:0;width:1px;height:1px;left:0;top:0" />
      </label>
    </div>
    ${!preview ? html`
      <textarea class="field" rows="10" aria-label=${label} value=${md.text} placeholder="Write with GitHub markdown. Drop or paste images here." onInput=${(e) => { A.setModal({ text: e.target.value }); keepCaret(e); }} onSelect=${keepCaret} onBlur=${keepCaret} onClick=${keepCaret} onKeyUp=${keepCaret} onPaste=${onPaste} onDragOver=${allow} onDrop=${dropText} style="font-family:Consolas, monospace;font-size:14px"></textarea>
      <span style="${SMALL};line-height:1.4">Click in the text where an image should go, then drop it in, paste it, or press Add image. GitHub markdown works: headings, **bold**, *italic*, ~~strike~~, lists, task lists, tables, quotes, code and links.</span>` : html`
      <div style="display:flex;flex-direction:column;gap:10px;border:1.5px solid var(--line);border-radius:14px;padding:12px;background:var(--bg);max-height:440px;overflow-y:auto">
        ${raw.length === 0 ? html`<div onDragOver=${allow} onDrop=${dropText} style="border:2px dashed var(--line);border-radius:12px;padding:22px;text-align:center;color:var(--muted);font-weight:700">Nothing to show yet. Write something, or drop an image here.</div>` : null}
        ${raw.map((r, i) => html`<div key=${i} class="block" onDragOver=${(e) => { e.preventDefault(); setOver(i); }} onDragLeave=${() => setOver(-1)} onDrop=${dropBlock(i)} style=${'display:flex;gap:6px;align-items:flex-start;background:var(--surface);border:1.5px solid var(--line);border-radius:12px;padding:8px 6px 8px 12px;' + (over === i ? 'box-shadow:0 5px 0 0 var(--strong);' : '')}>
          <div style="flex:1;min-width:0;display:flex;flex-direction:column;gap:8px;line-height:1.5">${renderBlock(r, md.images)}</div>
          <div style="display:flex;flex-direction:column;flex:none">
            <${IB} icon="up" label="Move up" disabled=${i === 0} onClick=${() => mv(i, -1)} />
            <${IB} icon="down" label="Move down" disabled=${i === raw.length - 1} onClick=${() => mv(i, 1)} />
            <${IB} icon="close" label="Remove this block" onClick=${() => rm(i)} />
          </div>
        </div>`)}
      </div>
      <span style=${SMALL}>Use the arrows to move a paragraph or an image up or down. Drop an image on any block to place it right after that block.</span>`}
  </div>`;
}
