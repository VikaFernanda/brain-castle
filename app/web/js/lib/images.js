// Images inside note text: shrink a picked file, and edit the text blocks (from the design's
// shrink, addImages, moveBlock, removeBlock). The text holds the token ![alt](img:ID).
import { splitBlocks } from '../markdown.js';

let seq = 0;
// UI-side id for now (MockApi). Python will own image ids later (see data-contract.md).
export const newImageId = () => 'i' + Date.now() + (seq++);

// File -> { id, alt, src }. Max 1200px on the long side, GIFs untouched. Resolves null if unreadable.
export const shrinkImage = (f) => new Promise((res) => {
  const r = new FileReader();
  r.onerror = () => res(null);
  r.onload = () => {
    const base = { id: newImageId(), alt: (f.name || 'image').replace(/\.[^.]+$/, '').replace(/[[\]()]/g, '') || 'image' };
    if (f.type === 'image/gif') { res({ ...base, src: r.result }); return; }
    const img = new Image();
    img.onerror = () => res(null);
    img.onload = () => {
      const k = Math.min(1, 1200 / Math.max(img.width, img.height, 1));
      const c = document.createElement('canvas');
      c.width = Math.max(1, Math.round(img.width * k)); c.height = Math.max(1, Math.round(img.height * k));
      let src = r.result;
      try { c.getContext('2d').drawImage(img, 0, 0, c.width, c.height); src = c.toDataURL(f.type === 'image/png' ? 'image/png' : 'image/jpeg', 0.85); } catch (e) { /* keep the original */ }
      res({ ...base, src });
    };
    img.src = r.result;
  };
  r.readAsDataURL(f);
});

export const imageToken = (r) => '![' + r.alt + '](img:' + r.id + ')';

// where = { block: i } puts the tokens right after block i; { caret: n } puts them at the caret (null = end).
export function insertTokens(text, toks, where) {
  text = text || '';
  if (where && where.block != null) {
    const bl = splitBlocks(text); bl.splice(where.block + 1, 0, ...toks);
    return bl.join('\n\n');
  }
  const at = where && where.caret != null ? Math.min(where.caret, text.length) : text.length;
  const before = text.slice(0, at).replace(/\s+$/, ''); const after = text.slice(at).replace(/^\s+/, '');
  return (before ? before + '\n\n' : '') + toks.join('\n\n') + (after ? '\n\n' + after : '');
}

export function moveBlockText(text, i, d) {
  const bl = splitBlocks(text); const j = i + d;
  if (i < 0 || i >= bl.length || j < 0 || j >= bl.length) return text;
  const t = bl[i]; bl[i] = bl[j]; bl[j] = t;
  return bl.join('\n\n');
}

export function removeBlockText(text, i) {
  const bl = splitBlocks(text); bl.splice(i, 1);
  return bl.join('\n\n');
}
