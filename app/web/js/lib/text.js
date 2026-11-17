// Markdown text helpers from the design (Phase 5 makes the editor rich; tasks only need these now).
export const imgIds = (t) => { const out = []; String(t || '').replace(/!\[[^\]]*\]\(img:([\w-]+)\)/g, (_, id) => { out.push(id); return ''; }); return out; };
export const pruneImgs = (t, imgs) => { const o = {}; imgIds(t).forEach((id) => { if (imgs && imgs[id]) o[id] = imgs[id]; }); return o; };
export const plain = (t) => String(t || '').replace(/!\[[^\]]*\]\(img:[\w-]+\)/g, '').replace(/```[\s\S]*?```/g, ' ').replace(/^#{1,6}\s+/gm, '').replace(/^>\s?/gm, '').replace(/^\s*([-*+]|\d+\.)\s+(\[[ xX]\]\s+)?/gm, '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').replace(/(\*\*|__|~~|`)/g, '').replace(/\|/g, ' ').replace(/\s+/g, ' ').trim();
