// Diary actions: talk to `api`, then update the store with what the api returned.
// Shared behaviour (selection, tags, drag events, tag modal) comes from the task actions `T`.
import { addDays, addMonths, mondayOf, monthOf, todayISO } from '../lib/dates.js';
import { pruneImgs } from '../lib/text.js';
import { PAL } from '../mock-data.js';

const SHARED = ['toggleSelMode', 'toggleSel', 'clearSel', 'selectAll', 'setTag', 'openTags', 'setModal', 'toast', 'closeModal',
  'dragStart', 'dragEnd', 'over', 'leave', 'addTagToModal', 'saveTag', 'askDeleteTag'];

export function createDiaryActions({ api, store, toast, ask, T }) {
  const { getState, setState } = store;
  const idle = { dragId: null, overKey: null };
  const letter = (id) => id[0];

  const safe = (fn) => async (...args) => {
    try { return await fn(...args); } catch (e) { toast(e && e.message ? e.message : 'Something went wrong'); return undefined; }
  };
  const KEY = { n: 'notes', b: 'books' };
  const swap = (key, items) => {
    const m = new Map(items.map((x) => [x.id, x]));
    setState((s) => ({ [key]: s[key].map((x) => m.get(x.id) || x) }));
  };
  const applyOrder = (key, order) => setState((s) => {
    const pos = new Map(order.map((id, i) => [id, i]));
    return { [key]: [...s[key]].sort((a, b) => (pos.get(a.id) ?? 1e9) - (pos.get(b.id) ?? 1e9)) };
  });
  const setBook = (ids, bookId) => setState((s) => ({ notes: s.notes.map((n) => (ids.includes(n.id) ? { ...n, bookId } : n)) }));
  // Drop selected ids from state. Deleting a book also deletes its notes (data contract).
  const dropIds = (ids) => {
    const set = new Set(ids);
    setState((s) => {
      const sel = { ...s.sel }; ids.forEach((i) => delete sel[i]);
      const books = s.books.filter((b) => !set.has(b.id));
      const notes = s.notes.filter((n) => !set.has(n.id) && !set.has(n.bookId));
      return { books, notes, sel, openBook: set.has(s.openBook) ? null : s.openBook };
    });
  };
  const remove = async (ids) => {
    await Promise.all(ids.map((id) => (letter(id) === 'b' ? api.delete_book(id) : api.delete_note(id))));
    dropIds(ids);
    toast('Deleted');
  };
  const archiveIds = async (ids) => {
    const done = await Promise.all(ids.map((id) => (letter(id) === 'b' ? api.archive_book(id) : api.archive_note(id))));
    swap('notes', done.filter((x) => x.id[0] === 'n'));
    swap('books', done.filter((x) => x.id[0] === 'b'));
    setState((s) => { const sel = { ...s.sel }; ids.forEach((i) => delete sel[i]); return { sel }; });
  };

  // Dragging a selected item moves every selected item of the same kind.
  const dragIds = (l) => {
    const s = getState();
    if (s.sel[s.dragId]) return Object.keys(s.sel).filter((k) => k[0] === l);
    return s.dragId && s.dragId[0] === l ? [s.dragId] : [];
  };
  const moveNotes = async (ids, bookId) => {
    await api.move(ids, { bookId });
    setBook(ids, bookId);
    toast(ids.length > 1 ? ids.length + ' notes moved' : 'Note moved');
  };

  const D = {};
  SHARED.forEach((k) => { D[k] = T[k]; });
  Object.assign(D, {
    // ---- view, period, sort ----
    setView: (dview) => setState({ dview, sel: {} }),
    setScope: (bscope) => setState({ bscope, sel: {} }),
    setBSort: (bsort) => setState({ bsort }),
    setNSort: (nsort) => setState({ nsort }),
    step: (dir) => setState((s) => {
      if (s.bscope === 'week') { const w = addDays(s.bweek, 7 * dir); return { bweek: w, bmonth: monthOf(w) }; }
      const m = addMonths(s.bmonth, dir);
      return { bmonth: m, bweek: mondayOf(m + '-01') };
    }),
    today: () => setState({ bweek: mondayOf(todayISO()), bmonth: monthOf(todayISO()) }),
    toggleOpen: (id) => setState((s) => ({ expanded: { ...s.expanded, [id]: !s.expanded[id] } })),
    openBookView: (id) => setState({ openBook: id }),
    closeBook: () => setState({ openBook: null, sel: {} }),

    // ---- single items ----
    archive: safe(async (id) => { await archiveIds([id]); toast(letter(id) === 'b' ? 'Book archived' : 'Note archived'); }),
    askDeleteNote: (id) => ask('This note will be deleted for good.', safe(() => remove([id]))),
    askDeleteBook: (id) => ask('This book and all its notes will be deleted for good.', safe(() => remove([id]))),

    // ---- bulk ----
    bulkMove: safe(async (bookId) => {
      if (!bookId) return;
      const ids = Object.keys(getState().sel).filter((i) => i[0] === 'n');
      await api.move(ids, { bookId });
      setBook(ids, bookId);
      setState({ sel: {} });
      toast(ids.length + ' moved');
    }),
    bulkArchive: safe(async () => {
      const ids = Object.keys(getState().sel);
      await archiveIds(ids);
      toast(ids.length + ' archived');
    }),
    askBulkDelete: () => {
      const ids = Object.keys(getState().sel);
      ask('Delete ' + ids.length + ' selected item' + (ids.length === 1 ? '' : 's') + ' for good?', safe(() => remove(ids)));
    },

    // ---- drag and drop ----
    // Drop on a book: notes move into it, books are placed before it (Manual sort).
    dropOnBook: (bookId) => safe(async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const d = getState().dragId || '';
      const ids = dragIds(letter(d) || 'n');
      setState(idle);
      if (!ids.length) return;
      if (d[0] === 'n') await moveNotes(ids, bookId);
      else if (d[0] === 'b' && !ids.includes(bookId)) {
        const { ids: order } = await api.reorder(ids, bookId);
        applyOrder('books', order);
      }
    }),
    // Drop on a note: take that note's book and sit right before it.
    dropOnNote: (n) => safe(async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const ids = dragIds('n');
      setState(idle);
      if (!ids.length || ids.includes(n.id)) return;
      await api.move(ids, { bookId: n.bookId });
      setBook(ids, n.bookId);
      const { ids: order } = await api.reorder(ids, n.id);
      applyOrder('notes', order);
    }),
    // Drop on a book chip in the open-book view.
    dropOnChip: (bookId) => safe(async (e) => {
      e.preventDefault();
      const ids = dragIds('n');
      setState(idle);
      if (ids.length) await moveNotes(ids, bookId);
    }),

    // ---- modals ----
    openNote: (id, bookId) => {
      const s = getState();
      const n = id && s.notes.find((x) => x.id === id);
      const first = s.books.find((b) => !b.archived);
      setState({ modal: { kind: 'note', id: id || null, title: n ? n.title : '', text: n ? n.body : '', images: n ? { ...(n.images || {}) } : {}, bookId: n ? n.bookId : (bookId || (first ? first.id : '')), date: n ? n.date : '', tags: n ? [...n.tags] : [], newTag: '', err: '' } });
    },
    openBookModal: (id) => {
      const s = getState();
      const b = id && s.books.find((x) => x.id === id);
      setState({ modal: { kind: 'book', id: id || null, title: b ? b.name : '', date: b ? b.date : '', color: b ? b.color : PAL[s.books.length % 6], err: '' } });
    },
    saveNote: safe(async () => {
      const md = getState().modal;
      const title = (md.title || '').trim();
      if (!title) { D.setModal({ err: 'Please add a name first.' }); return; }
      if (!md.bookId) { D.setModal({ err: 'Make a book first, then add notes to it.' }); return; }
      const f = { title, body: md.text, images: pruneImgs(md.text, md.images), bookId: md.bookId, date: md.date || '', tags: md.tags };
      if (md.id) swap('notes', [await api.update_note(md.id, f)]);
      else {
        const n = await api.create_note(f);
        setState((s) => ({ notes: [...s.notes, n], expanded: { ...s.expanded, [md.bookId]: true } }));
      }
      setState({ modal: null });
      toast('Saved');
    }),
    saveBook: safe(async () => {
      const md = getState().modal;
      const name = (md.title || '').trim();
      if (!name) { D.setModal({ err: 'Please add a name first.' }); return; }
      const f = { name, date: md.date || '', color: md.color };
      if (md.id) swap('books', [await api.update_book(md.id, f)]);
      else { const b = await api.create_book(f); setState((s) => ({ books: [...s.books, b] })); }
      setState({ modal: null });
      toast('Saved');
    }),
    archiveFromModal: safe(async () => { const id = getState().modal.id; await archiveIds([id]); setState({ modal: null }); toast('Archived'); }),
    deleteFromModal: () => { const id = getState().modal.id; setState({ modal: null }); ask('Delete this for good? This cannot be undone.', safe(() => remove([id]))); }
  });
  return D;
}
