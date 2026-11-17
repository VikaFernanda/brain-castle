// GitHub-style markdown for tasks and notes. Started from the design's renderer (inl, splitBlocks, parseBlock).
//
// SAFETY RULE: this module never builds an HTML string. The parser turns text into plain data
// (nodes), and the renderer turns that data into Preact elements (h(...)). Every piece of user text
// reaches the page as a text node or as an attribute value, so `<script>` is just visible text.
// Links are only kept when they start with http:, https: or mailto:. Images only come from the
// note's own image map (token ![alt](img:ID)).
//
// Public API:
//   splitBlocks(text)            -> string[]   blocks split by blank lines (code fences stay whole)
//   parseBlock(raw, images)      -> part[]     block-level data (heading, p, quote, list, table, ...)
//   parseInline(text, images)    -> node[]     inline data (text, code, em, strong, del, link, br, img)
//   renderBlock(raw, images)     -> vnode[]    one block as Preact elements
//   renderMarkdown(text, images) -> vnode      the whole text as Preact elements
//   safeHref(url)                -> string|''  the url if allowed, else ''
import { h } from 'preact';

/* ---------- styles (copied from the design) ---------- */
const CODE_STYLE = 'font-family:Consolas,monospace;background:var(--accent-soft);padding:1px 6px;border-radius:6px;font-size:.92em';
const LINK_STYLE = 'color:var(--strong);font-weight:700';
const HEAD_SIZES = [28, 24, 20, 18, 16, 15];
const QUOTE_STYLE = 'background:var(--accent2-soft);border-radius:10px;padding:8px 12px;font-style:italic;display:flex;flex-direction:column;gap:6px';
// Nested quotes need a different look or they vanish into the parent. (Not in the design: extra, kept in the same palette.)
const QUOTE_INNER_STYLE = 'background:var(--surface);border:1.5px solid var(--line);border-radius:10px;padding:8px 12px;font-style:italic;display:flex;flex-direction:column;gap:6px';
const PRE_STYLE = 'margin:0;padding:10px 12px;border-radius:10px;background:var(--accent-soft);font-family:Consolas,monospace;font-size:13px;white-space:pre-wrap;overflow-x:auto';
const IMG_STYLE = 'max-width:100%;max-height:320px;border-radius:12px;align-self:flex-start';

/* ---------- links and image sources ---------- */
export const safeHref = (u) => {
  const s = String(u || '').trim();
  if (/[\u0000- \u007f]/.test(s)) return '';
  return /^(https?:\/\/|mailto:)[^\s]/i.test(s) ? s : '';
};
const safeImgSrc = (u) => (/^(data:image\/[a-z0-9.+-]+[;,]|https?:\/\/|blob:|file:)/i.test(String(u || '')) ? String(u) : '');

/* ---------- blocks: split ---------- */
const FENCE_RE = /^ {0,3}(`{3,}|~{3,})/;
export const splitBlocks = (text) => {
  const out = []; let cur = []; let fence = null;
  String(text || '').replace(/\r\n?/g, '\n').split('\n').forEach((l) => {
    const f = FENCE_RE.exec(l);
    if (f) {
      if (!fence) fence = { ch: f[1][0], len: f[1].length };
      else if (f[1][0] === fence.ch && f[1].length >= fence.len && l.replace(FENCE_RE, '').trim() === '') fence = null;
    }
    if (!fence && l.trim() === '') { if (cur.length) { out.push(cur.join('\n')); cur = []; } } else cur.push(l);
  });
  if (cur.length) out.push(cur.join('\n'));
  return out;
};

/* ---------- inline ---------- */
const BR = ''; // private marker for a hard line break, inserted by the paragraph parser
const PUNCT = /[!-/:-@[-`{-~]/;
const isAlnum = (c) => !!c && /[\p{L}\p{N}]/u.test(c);
const isSpace = (c) => !c || /\s/.test(c);

// Index of the "]" that closes the "[" at i, skipping escapes, code spans and nested brackets. -1 if none.
function findClose(s, i) {
  let depth = 0;
  for (let j = i; j < s.length; j++) {
    const c = s[j];
    if (c === '\\') { j++; continue; }
    if (c === '`') {
      const run = /^`+/.exec(s.slice(j))[0].length;
      const k = s.indexOf('`'.repeat(run), j + run);
      if (k > 0) { j = k + run - 1; continue; }
      j += run - 1; continue;
    }
    if (c === '[') depth++;
    else if (c === ']') { depth--; if (depth === 0) return j; }
  }
  return -1;
}

// Parse "(destination "title")" starting at s[p] === "(". Returns { url, end } (end = index after ")") or null.
function parseDest(s, p) {
  let i = p + 1;
  while (i < s.length && /[ \t]/.test(s[i])) i++;
  let url = '';
  if (s[i] === '<') {
    const k = s.indexOf('>', i);
    if (k < 0) return null;
    url = s.slice(i + 1, k); i = k + 1;
  } else {
    let depth = 0;
    while (i < s.length) {
      const c = s[i];
      if (c === '\\' && i + 1 < s.length && PUNCT.test(s[i + 1])) { url += s[i + 1]; i += 2; continue; }
      if (/\s/.test(c)) break;
      if (c === '(') depth++;
      if (c === ')') { if (depth === 0) break; depth--; }
      url += c; i++;
    }
  }
  while (i < s.length && /[ \t]/.test(s[i])) i++;
  if (s[i] === '"' || s[i] === "'") { // optional title, ignored
    const q = s[i]; const k = s.indexOf(q, i + 1);
    if (k < 0) return null;
    i = k + 1;
    while (i < s.length && /[ \t]/.test(s[i])) i++;
  }
  return s[i] === ')' ? { url, end: i + 1 } : null;
}

const trimUrl = (u) => {
  let t = u;
  for (;;) {
    const before = t;
    t = t.replace(/[?!.,:;*_~'"]+$/, '');
    if (t.endsWith(')') && (t.match(/\)/g) || []).length > (t.match(/\(/g) || []).length) t = t.slice(0, -1);
    if (t === before) return t;
  }
};

function inline(s, images, inLink, depth) {
  const out = []; let buf = ''; let i = 0;
  const flush = () => { if (buf) { out.push({ t: 'text', s: buf }); buf = ''; } };
  const sub = (txt, link) => (depth > 20 ? [{ t: 'text', s: txt }] : inline(txt, images, inLink || link, depth + 1));
  while (i < s.length) {
    const c = s[i];
    // backslash escape
    if (c === '\\' && i + 1 < s.length && PUNCT.test(s[i + 1])) { buf += s[i + 1]; i += 2; continue; }
    if (c === BR) { flush(); out.push({ t: 'br' }); i++; continue; }
    // code span (inline code)
    if (c === '`') {
      const n = /^`+/.exec(s.slice(i))[0].length; let close = -1;
      const re = /`+/g; re.lastIndex = i + n; let m;
      while ((m = re.exec(s))) { if (m[0].length === n) { close = m.index; break; } }
      if (close < 0) { buf += '`'.repeat(n); i += n; continue; }
      let code = s.slice(i + n, close).replace(/[\n]/g, ' ');
      if (code.length > 2 && code[0] === ' ' && code[code.length - 1] === ' ' && code.trim() !== '') code = code.slice(1, -1);
      flush(); out.push({ t: 'code', s: code }); i = close + n; continue;
    }
    // link, or image token
    if (c === '[' || (c === '!' && s[i + 1] === '[')) {
      const isImg = c === '!'; const open = isImg ? i + 1 : i;
      const close = findClose(s, open);
      if (close > 0 && s[close + 1] === '(') {
        const d = parseDest(s, close + 1);
        if (d) {
          const label = s.slice(open + 1, close);
          flush();
          if (isImg) {
            const im = /^img:([\w-]+)$/.exec(d.url);
            if (im) { const src = safeImgSrc((images || {})[im[1]]); out.push({ t: 'img', alt: label || 'image', src, has: !!src }); }
            else out.push({ t: 'text', s: label }); // pictures from the web are never loaded: show the alt text
          } else {
            const href = inLink ? '' : safeHref(d.url);
            const kids = sub(label, true);
            if (href) out.push({ t: 'link', href, c: kids.length ? kids : [{ t: 'text', s: href }] });
            else out.push(...kids); // unsafe or nested link: keep the words, drop the link
          }
          i = d.end; continue;
        }
      }
    }
    // <https://...> and <mail@x.com>
    if (c === '<') {
      const m = /^<((?:https?:\/\/|mailto:)[^\s<>]+)>/i.exec(s.slice(i)) || null;
      const e = !m && /^<([^\s<>@]+@[^\s<>@]+\.[^\s<>@]+)>/.exec(s.slice(i));
      const url = m ? m[1] : (e ? 'mailto:' + e[1] : '');
      const href = !inLink && safeHref(url);
      if (href) { flush(); out.push({ t: 'link', href, c: [{ t: 'text', s: m ? m[1] : e[1] }] }); i += (m || e)[0].length; continue; }
    }
    // bare URL (autolink)
    if ((c === 'h' || c === 'H' || c === 'w' || c === 'W') && !inLink && !isAlnum(s[i - 1]) && s[i - 1] !== '/') {
      const m = /^(?:https?:\/\/|www\.)[^\s<>]+/i.exec(s.slice(i));
      if (m) {
        const url = trimUrl(m[0]);
        const www = /^www\./i.test(url);
        const ok = www ? /^www\.[^./]+\.[^./]/i.test(url) : /^https?:\/\/[^/\s]+/i.test(url);
        const href = ok ? safeHref(www ? 'http://' + url : url) : '';
        if (href) { flush(); out.push({ t: 'link', href, c: [{ t: 'text', s: url }] }); i += url.length; continue; }
      }
    }
    // emphasis: ***x***, **x**, *x*, __x__, _x_, ~~x~~
    if (c === '*' || c === '_' || c === '~') {
      let n = 1; while (s[i + n] === c) n++;
      const use = c === '~' ? (n >= 2 ? 2 : 0) : Math.min(n, 3);
      const start = i + n;
      const canOpen = use > 0 && !isSpace(s[start]) && (c !== '_' || !isAlnum(s[i - 1]));
      if (canOpen) {
        let j = start; let found = -1;
        while (j < s.length) {
          if (s[j] === '\\') { j += 2; continue; }
          if (s[j] === '`') { const r = /^`+/.exec(s.slice(j))[0].length; const k = s.indexOf('`'.repeat(r), j + r); j = k > 0 ? k + r : j + r; continue; }
          if (s[j] === c) {
            let m = 1; while (s[j + m] === c) m++;
            if (m === use && j > start && !isSpace(s[j - 1]) && (c !== '_' || !isAlnum(s[j + m]))) { found = j; break; }
            j += m; continue;
          }
          j++;
        }
        if (found > 0) {
          const kids = sub(s.slice(start, found), false);
          buf += c.repeat(n - use); flush();
          if (c === '~') out.push({ t: 'del', c: kids });
          else if (use === 1) out.push({ t: 'em', c: kids });
          else if (use === 2) out.push({ t: 'strong', c: kids });
          else out.push({ t: 'strong', c: [{ t: 'em', c: kids }] });
          i = found + use; continue;
        }
      }
      buf += c.repeat(n); i += n; continue;
    }
    buf += c; i++;
  }
  flush();
  return out;
}
export const parseInline = (text, images) => inline(String(text || '').replace(//g, ''), images, false, 0);

/* ---------- blocks: parse ---------- */
const ITEM_RE = /^( *)([-*+]|\d{1,9}[.)])[ ]+(.*)$/;
const HR_RE = /^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$/;
const IMG_LINE_RE = /^\s*!\[([^\]]*)\]\(img:([\w-]+)\)\s*$/;
const HEAD_RE = /^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$/;
const QUOTE_RE = /^ {0,3}>/;
const DELIM_RE = /^:?-+:?$/;
const MAX_DEPTH = 6;

const splitRow = (line) => {
  let t = line.trim();
  if (t.startsWith('|')) t = t.slice(1);
  if (t.endsWith('|') && !t.endsWith('\\|')) t = t.slice(0, -1);
  const cells = []; let buf = '';
  for (let k = 0; k < t.length; k++) {
    if (t[k] === '\\' && t[k + 1] === '|') { buf += '|'; k++; } else if (t[k] === '|') { cells.push(buf.trim()); buf = ''; } else buf += t[k];
  }
  cells.push(buf.trim());
  return cells;
};
const isTableStart = (lines, i) => {
  if (i + 1 >= lines.length || !lines[i].includes('|') || !lines[i + 1].includes('-')) return false;
  const head = splitRow(lines[i]); const dl = splitRow(lines[i + 1]);
  return head.length === dl.length && dl.every((c) => DELIM_RE.test(c)) && /^[\s|:-]+$/.test(lines[i + 1]);
};
const startsBlock = (l) => FENCE_RE.test(l) || HEAD_RE.test(l) || HR_RE.test(l) || QUOTE_RE.test(l) || IMG_LINE_RE.test(l)
  || /^ {0,3}[-*+][ ]+/.test(l) || /^ {0,3}1[.)][ ]+/.test(l); // like GitHub: only a bullet or "1." can interrupt a paragraph

function parseLines(lines, images, depth) {
  const parts = []; let i = 0; let m;
  while (i < lines.length) {
    const ln = lines[i];
    if (ln.trim() === '') { i++; continue; }
    // fenced code
    if ((m = FENCE_RE.exec(ln))) {
      const ch = m[1][0]; const len = m[1].length; const code = []; i++;
      while (i < lines.length && !(new RegExp('^ {0,3}\\' + ch + '{' + len + ',}[ \\t]*$').test(lines[i]))) code.push(lines[i++]);
      i++; parts.push({ t: 'code', text: code.join('\n') }); continue;
    }
    if ((m = HEAD_RE.exec(ln))) { parts.push({ t: 'h', level: m[1].length, c: inline(m[2], images, false, 0) }); i++; continue; }
    if (HR_RE.test(ln)) { parts.push({ t: 'hr' }); i++; continue; }
    if ((m = IMG_LINE_RE.exec(ln))) { const src = safeImgSrc((images || {})[m[2]]); parts.push({ t: 'img', src, has: !!src, missing: !src, alt: m[1] || 'image' }); i++; continue; }
    // quote (nested quotes come from the recursive call)
    if (QUOTE_RE.test(ln) && depth < MAX_DEPTH) {
      const q = [];
      while (i < lines.length && QUOTE_RE.test(lines[i])) q.push(lines[i++].replace(/^ {0,3}> ?/, ''));
      parts.push({ t: 'quote', depth, parts: parseLines(q, images, depth + 1) }); continue;
    }
    // list (nested by indent)
    if (ITEM_RE.test(ln)) {
      const items = []; const stack = []; const counters = []; const kinds = [];
      while (i < lines.length) {
        const im = ITEM_RE.exec(lines[i]);
        if (!im) {
          if (/^\s+\S/.test(lines[i]) && items.length && !FENCE_RE.test(lines[i])) { items[items.length - 1].raw += ' ' + lines[i].trim(); i++; continue; } // continuation line
          break;
        }
        if (HR_RE.test(lines[i])) break;
        const n = im[1].length;
        while (stack.length && n < stack[stack.length - 1]) stack.pop();
        if (!stack.length || n > stack[stack.length - 1]) stack.push(n);
        const d = stack.length - 1;
        const ordered = /\d/.test(im[2]);
        counters.length = d + 1; kinds.length = d + 1;
        if (kinds[d] !== ordered) { kinds[d] = ordered; counters[d] = ordered ? parseInt(im[2], 10) : 0; } else if (ordered) counters[d]++;
        let txt = im[3]; let task = false; let done = false; const tm = /^\[( |x|X)\][ \t]+(.*)$/.exec(txt);
        if (tm) { task = true; done = tm[1] !== ' '; txt = tm[2]; }
        items.push({ pad: d * 18, marker: task ? '' : (ordered ? counters[d] + '.' : '•'), task, done, raw: txt });
        i++;
      }
      parts.push({ t: 'list', items: items.map((it) => ({ pad: it.pad, marker: it.marker, task: it.task, done: it.done, c: inline(it.raw, images, false, 0) })) });
      continue;
    }
    // table, with column alignment
    if (isTableStart(lines, i)) {
      const head = splitRow(ln); const align = splitRow(lines[i + 1]).map((c) => (c[0] === ':' && c.endsWith(':') ? 'center' : c.endsWith(':') ? 'right' : c[0] === ':' ? 'left' : ''));
      i += 2; const rows = [];
      while (i < lines.length && lines[i].trim() && lines[i].includes('|')) { const r = splitRow(lines[i++]); rows.push(head.map((_, c) => inline(r[c] || '', images, false, 0))); }
      parts.push({ t: 'table', cols: head.length, align, head: head.map((c) => inline(c, images, false, 0)), rows }); continue;
    }
    // paragraph. Soft line breaks become a space; two trailing spaces or a backslash make a hard break.
    const p = [ln]; i++;
    while (i < lines.length && lines[i].trim() && !startsBlock(lines[i])) p.push(lines[i++]);
    let text = '';
    p.forEach((l, k) => {
      let line = l.trim();
      if (k < p.length - 1) {
        const bs = /\\+$/.exec(line);
        if (bs && bs[0].length % 2 === 1) { text += line.slice(0, -1) + BR; return; }
        if (/ {2,}$/.test(l.replace(/\t/g, ' '))) { text += line + BR; return; }
        text += line + ' ';
      } else text += line;
    });
    parts.push({ t: 'p', c: inline(text, images, false, 0) });
  }
  return parts;
}
export const parseBlock = (raw, images) => parseLines(String(raw || '').replace(/\r\n?/g, '\n').replace(/[\u0000]/g, '').split('\n').map((l) => l.replace(/^[ \t]+/, (w) => w.replace(/\t/g, '    '))), images, 0);

/* ---------- render (Preact elements only) ---------- */
function renderInline(nodes) {
  return nodes.map((n) => {
    switch (n.t) {
      case 'text': return n.s;
      case 'br': return h('br', null);
      case 'code': return h('span', { style: CODE_STYLE }, n.s);
      case 'strong': return h('span', { style: 'font-weight:800' }, renderInline(n.c));
      case 'em': return h('span', { style: 'font-style:italic' }, renderInline(n.c));
      case 'del': return h('span', { style: 'text-decoration:line-through' }, renderInline(n.c));
      case 'link': return h('a', { href: n.href, target: '_blank', rel: 'noopener noreferrer', style: LINK_STYLE }, renderInline(n.c));
      case 'img': return n.has ? h('img', { src: n.src, alt: n.alt, style: IMG_STYLE + ';vertical-align:middle' }) : 'Image not found: ' + n.alt;
      default: return null;
    }
  });
}

const checkIcon = (done) => h('span', { style: 'flex:none;width:18px;height:18px;margin-top:3px;border-radius:6px;border:2px solid var(--muted);background:' + (done ? 'var(--accent)' : 'var(--surface)') + ';display:inline-flex;align-items:center;justify-content:center' },
  h('svg', { class: 'i', viewBox: '0 0 24 24', 'aria-hidden': 'true', style: 'width:12px;height:12px;opacity:' + (done ? 1 : 0) }, h('path', { d: 'M5 12.5l4.5 4.5L19 7.5' })));

function renderPart(pt) {
  switch (pt.t) {
    case 'h': return h('div', { style: 'font-family:Fredoka, system-ui, sans-serif;font-weight:600;line-height:1.2;font-size:' + HEAD_SIZES[pt.level - 1] + 'px' }, renderInline(pt.c));
    case 'p': return h('div', null, renderInline(pt.c));
    case 'quote': return h('div', { style: pt.depth > 0 ? QUOTE_INNER_STYLE : QUOTE_STYLE }, pt.parts.map(renderPart));
    case 'code': return h('pre', { style: PRE_STYLE }, pt.text);
    case 'hr': return h('div', { style: 'height:2px;background:var(--line);border-radius:2px' });
    case 'img': return pt.has ? h('img', { src: pt.src, alt: pt.alt, style: IMG_STYLE }) : h('div', { style: 'color:var(--muted);font-weight:700;font-size:14px' }, 'Image not found: ' + pt.alt);
    case 'list': return h('div', { style: 'display:flex;flex-direction:column;gap:4px' }, pt.items.map((it) => h('div', { style: 'display:flex;gap:8px;align-items:flex-start;padding-left:' + it.pad + 'px' },
      it.task ? checkIcon(it.done) : null,
      it.marker ? h('span', { style: 'flex:none;min-width:18px;color:var(--muted);font-weight:800' }, it.marker) : null,
      h('span', { style: 'flex:1;min-width:0' }, renderInline(it.c)))));
    case 'table': {
      const al = (c) => (pt.align[c] ? ';text-align:' + pt.align[c] : '');
      const cell = (nodes, c, head) => h('div', { style: 'padding:6px 10px;border:0.5px solid var(--line);' + (head ? 'font-weight:800;background:var(--accent-soft)' : '') + al(c) }, renderInline(nodes));
      return h('div', { style: 'overflow-x:auto' }, h('div', { style: 'display:grid;grid-template-columns:repeat(' + pt.cols + ', minmax(90px, 1fr));border:1.5px solid var(--line);border-radius:10px;overflow:hidden;font-size:14px' },
        pt.head.map((nodes, c) => cell(nodes, c, true)), pt.rows.map((r) => r.map((nodes, c) => cell(nodes, c, false)))));
    }
    default: return null;
  }
}

export const renderBlock = (raw, images) => parseBlock(raw, images).map(renderPart);
export const renderMarkdown = (text, images) => h('div', { style: 'display:flex;flex-direction:column;gap:8px;line-height:1.5' }, splitBlocks(text).map((r) => renderBlock(r, images)));
