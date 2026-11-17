// Pure view logic for the Archive page: sections Tasks / Notes / Books with counts and row texts.
import { fmt } from '../lib/dates.js';

export const AUTO_TEXT = 'Archived automatically (older than 3 months)';

export function buildArchiveView(s) {
  const aT = s.tasks.filter((t) => t.archived);
  const aN = s.notes.filter((n) => n.archived);
  const aB = s.books.filter((b) => b.archived);
  const bookName = (id) => (s.books.find((b) => b.id === id) || {}).name || 'a book';
  const sections = [
    { key: 'tasks', title: 'Tasks', rows: aT.map((t) => ({ id: t.id, title: t.title, meta: (t.date ? fmt(t.date) : 'No date') + (t.auto ? ' · ' + AUTO_TEXT : '') })) },
    { key: 'notes', title: 'Notes', rows: aN.map((n) => ({ id: n.id, title: n.title, meta: 'In ' + bookName(n.bookId) + (n.date ? ' · ' + fmt(n.date) : '') })) },
    { key: 'books', title: 'Books', rows: aB.map((b) => ({ id: b.id, title: b.name, meta: s.notes.filter((n) => n.bookId === b.id).length + ' notes inside' })) }
  ].filter((x) => x.rows.length > 0).map((x) => ({ ...x, count: x.rows.length }));
  const ids = sections.reduce((a, x) => a.concat(x.rows.map((r) => r.id)), []);
  return {
    sections, ids, empty: ids.length === 0,
    sub: ids.length + (ids.length === 1 ? ' item waiting' : ' items waiting')
  };
}
