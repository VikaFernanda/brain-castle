// Archive actions: talk to `api`, then reload the lists from `load_all` (restoring a note also restores its
// book, deleting a book also deletes its notes, so the api is the one that knows the final state).
export function createArchiveActions({ api, store, toast, ask, T }) {
  const { getState, setState } = store;
  const safe = (fn) => async (...args) => {
    try { return await fn(...args); } catch (e) { toast(e && e.message ? e.message : 'Something went wrong'); return undefined; }
  };
  const reload = async () => {
    const d = await api.load_all();
    setState((s) => {
      const alive = new Set([...d.tasks, ...d.notes, ...d.books].map((x) => x.id));
      const sel = Object.fromEntries(Object.keys(s.sel).filter((i) => alive.has(i)).map((i) => [i, true]));
      return { tasks: d.tasks, notes: d.notes, books: d.books, tags: d.tags, sel, openBook: alive.has(s.openBook) ? s.openBook : null };
    });
  };
  const restore = async (ids) => {
    const noteIds = new Set(ids.filter((i) => i[0] === 'n'));
    // restoring a note restores its book: skip the books that a note in this list will bring back
    for (const id of ids) {
      if (id[0] === 't') await api.restore_task(id);
      else if (id[0] === 'n') await api.restore_note(id);
      else if (id[0] === 'b') await api.restore_book(id);
    }
    await reload();
    setState({ sel: {} });
    toast('Restored');
    return noteIds;
  };
  const remove = async (ids) => {
    const books = new Set(ids.filter((i) => i[0] === 'b'));
    const nbook = (id) => (getState().notes.find((n) => n.id === id) || {}).bookId;
    for (const id of ids) {
      if (id[0] === 't') await api.delete_task(id);
      else if (id[0] === 'b') await api.delete_book(id);
      else if (id[0] === 'n' && !books.has(nbook(id))) await api.delete_note(id); // its book takes it along
    }
    await reload();
    setState({ sel: {} });
    toast('Deleted');
  };
  const selIds = () => Object.keys(getState().sel);

  return {
    restoreOne: safe((id) => restore([id])),
    askDeleteOne: (id) => ask('This will be deleted forever. It cannot be undone.', safe(() => remove([id]))),
    restoreSel: safe(() => restore(selIds())),
    askDeleteSel: () => {
      const ids = selIds();
      ask('Delete ' + ids.length + ' selected item' + (ids.length === 1 ? '' : 's') + ' forever? This cannot be undone.', safe(() => remove(ids)));
    },
    restoreAll: safe((ids) => restore(ids)),
    askDeleteAll: (ids) => ask('Empty the archive? All ' + ids.length + ' items will be deleted forever.', safe(() => remove(ids))),
    toggleSel: T.toggleSel,
    selectAll: T.selectAll
  };
}
