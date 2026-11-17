// Pure view logic for the Diary area (JS owns filter, sort, group). No DOM, no api here.
import { addDays, fmt, mondayOf, monthOf, monthName, rangeLabel, todayISO } from '../lib/dates.js';
import { plain, imgIds } from '../lib/text.js';

export const DSORT_OPTIONS = [{ value: 'new', label: 'Latest created' }, { value: 'soon', label: 'Date soon' }, { value: 'manual', label: 'Manual' }];

// manual = stored order. new = newest first. soon = dates from today on (nearest first), then past dates
// (most recent first), items without a date last.
export function sortByDate(arr, mode, today = todayISO()) {
  if (mode === 'manual') return arr;
  const a = [...arr];
  if (mode === 'new') return a.sort((x, y) => (y.created || 0) - (x.created || 0));
  return a.sort((x, y) => {
    const kx = x.date; const ky = y.date;
    if (!kx && !ky) return (y.created || 0) - (x.created || 0);
    if (!kx) return 1;
    if (!ky) return -1;
    const fx = kx >= today; const fy = ky >= today;
    if (fx !== fy) return fx ? -1 : 1;
    if (fx) return kx < ky ? -1 : kx > ky ? 1 : 0;
    return kx < ky ? 1 : kx > ky ? -1 : 0;
  });
}

export const firstImg = (imgs, text) => {
  const ids = imgIds(text);
  for (let i = 0; i < ids.length; i++) if (imgs && imgs[ids[i]]) return imgs[ids[i]];
  return '';
};
export const excerpt = (body) => { const p = plain(body); return p.length > 150 ? p.slice(0, 150) + '...' : p; };
export const countLabel = (n) => n + (n === 1 ? ' note' : ' notes');

// Everything the Diary page draws, computed from the store state.
export function buildDiaryView(s) {
  const today = todayISO();
  const q = s.q.trim().toLowerCase();
  const filtering = !!(q || s.tagF);
  const tagName = (id) => (s.tags.find((g) => g.id === id) || {}).name || '';
  const hit = (item, hay) => {
    if (s.tagF && !(item.tags || []).includes(s.tagF)) return false;
    if (!q) return true;
    return (hay + ' ' + (item.tags || []).map(tagName).join(' ')).toLowerCase().includes(q);
  };
  const inPeriod = (d) => !d || (s.bscope === 'all' ? true : s.bscope === 'week' ? (d >= s.bweek && d <= addDays(s.bweek, 6)) : monthOf(d) === s.bmonth);

  const actBooks = s.books.filter((b) => !b.archived);
  const notesOf = (bookId) => sortByDate(s.notes.filter((n) => n.bookId === bookId && !n.archived), s.nsort, today);

  const rows = sortByDate(actBooks, s.bsort, today).map((b) => {
    const all = notesOf(b.id);
    const matched = all.filter((n) => hit(n, n.title + ' ' + n.body));
    const nameHit = !!q && !s.tagF && b.name.toLowerCase().includes(q);
    const shown = filtering ? (nameHit && matched.length === 0 ? all : matched) : all;
    const visible = !filtering || nameHit || matched.length > 0;
    return { book: b, all, shown, visible, date: b.date || '', open: !!s.expanded[b.id] || filtering };
  }).filter((r) => r.visible && inPeriod(r.date));

  // Month heading, then "Week of ..." heading, then books. Undated books go last under "No date".
  const flow = [];
  const dated = rows.filter((r) => r.date); const undated = rows.filter((r) => !r.date);
  [...new Set(dated.map((r) => monthOf(r.date)))].sort().reverse().forEach((mo) => {
    flow.push({ kind: 'month', key: 'm' + mo, label: monthName(mo) });
    const inMo = dated.filter((r) => monthOf(r.date) === mo);
    [...new Set(inMo.map((r) => mondayOf(r.date)))].sort().reverse().forEach((wk) => {
      flow.push({ kind: 'week', key: 'w' + wk, label: 'Week of ' + rangeLabel(wk) });
      inMo.filter((r) => mondayOf(r.date) === wk).forEach((r) => flow.push({ kind: 'book', key: r.book.id, row: r }));
    });
  });
  if (undated.length) { flow.push({ kind: 'month', key: 'mnone', label: 'No date' }); undated.forEach((r) => flow.push({ kind: 'book', key: r.book.id, row: r })); }

  const openB = s.dview === 'board' && s.openBook ? actBooks.find((b) => b.id === s.openBook) || null : null;
  const openAll = openB ? notesOf(openB.id) : [];
  const openShown = openB ? (filtering ? openAll.filter((n) => hit(n, n.title + ' ' + n.body)) : openAll) : [];
  const otherBooks = openB ? actBooks.filter((b) => b.id !== openB.id) : [];
  const noteCount = s.notes.filter((n) => !n.archived && actBooks.some((b) => b.id === n.bookId)).length;

  let visibleIds;
  if (openB) visibleIds = openShown.map((n) => n.id);
  else if (s.dview === 'board') visibleIds = rows.map((r) => r.book.id);
  else visibleIds = rows.reduce((a, r) => a.concat([r.book.id], r.open ? r.shown.map((n) => n.id) : []), []);

  return {
    filtering, flow, rows, actBooks, openB, openAll, openShown, otherBooks, visibleIds,
    title: openB ? openB.name : 'Diary',
    sub: openB ? (openB.date ? 'Started ' + fmt(openB.date) : 'No date') : actBooks.length + ' books and ' + noteCount + ' notes',
    periodLabel: s.bscope === 'week' ? rangeLabel(s.bweek) : monthName(s.bmonth),
    emptyText: filtering ? 'No books or notes match your search.' : 'No books yet. Press New book to start one.'
  };
}
