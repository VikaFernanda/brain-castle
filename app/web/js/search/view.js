// Pure view logic for universal search. Matches title, text, tag names and book names.
// Archived items are excluded (a note of an archived book too). The tag filter combines with the text.
import { fmt, fmtTime } from '../lib/dates.js';
import { plain } from '../lib/text.js';

export function buildSearchView(s) {
  const q = s.q.trim().toLowerCase();
  const tagName = (id) => (s.tags.find((g) => g.id === id) || {}).name || '';
  const chips = (ids) => (ids || []).map((id) => s.tags.find((g) => g.id === id)).filter(Boolean);
  const hit = (item, hay) => {
    if (s.tagF && !(item.tags || []).includes(s.tagF)) return false;
    return (hay + ' ' + (item.tags || []).map(tagName).join(' ')).toLowerCase().includes(q);
  };
  const actBooks = s.books.filter((b) => !b.archived);
  const bookName = (id) => (actBooks.find((b) => b.id === id) || {}).name || 'a book';
  const tasks = s.tasks.filter((t) => !t.archived && hit(t, t.title + ' ' + plain(t.notes)))
    .map((t) => ({ id: t.id, kind: 'task', title: t.title, meta: (t.date ? fmt(t.date) : 'No date yet') + (t.time ? ' · ' + fmtTime(t.time) : ''), tags: chips(t.tags) }));
  const notes = s.notes.filter((n) => !n.archived && actBooks.some((b) => b.id === n.bookId) && hit(n, n.title + ' ' + plain(n.body) + ' ' + bookName(n.bookId)))
    .map((n) => ({ id: n.id, kind: 'note', title: n.title, meta: 'In ' + bookName(n.bookId) + (n.date ? ' · ' + fmt(n.date) : ''), tags: chips(n.tags) }));
  const books = s.tagF ? [] : actBooks.filter((b) => b.name.toLowerCase().includes(q))
    .map((b) => ({ id: b.id, kind: 'book', title: b.name, meta: 'Book · ' + s.notes.filter((n) => n.bookId === b.id && !n.archived).length + ' notes', tags: [] }));
  const sections = [{ key: 'tasks', title: 'Tasks', rows: tasks }, { key: 'notes', title: 'Notes', rows: notes }, { key: 'books', title: 'Books', rows: books }]
    .filter((x) => x.rows.length > 0).map((x) => ({ ...x, count: x.rows.length }));
  const total = tasks.length + notes.length + books.length;
  return { sections, total, empty: total === 0, sub: total + (total === 1 ? ' match' : ' matches') + ' across tasks, notes and books' };
}
