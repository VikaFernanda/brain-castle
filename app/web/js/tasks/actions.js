// Task actions: talk to `api`, then update the store with what the api returned.
import { addDays, addMonths, mondayOf, monthOf, todayISO } from '../lib/dates.js';
import { pruneImgs } from '../lib/text.js';
import { PAL } from '../mock-data.js';

export function createTaskActions({ api, store, toast, ask }) {
  const { getState, setState } = store;
  const idle = { dragId: null, overKey: null };

  // An api error becomes a short toast (see data-contract.md).
  const safe = (fn) => async (...args) => {
    try { return await fn(...args); } catch (e) { toast(e && e.message ? e.message : 'Something went wrong'); return undefined; }
  };
  const swap = (items) => {
    const m = new Map(items.map((x) => [x.id, x]));
    setState((s) => ({ tasks: s.tasks.map((t) => m.get(t.id) || t) }));
  };
  const patch = async (ids, fields) => swap(await Promise.all(ids.map((id) => api.update_task(id, fields))));
  const dropIds = (ids) => {
    const set = new Set(ids);
    setState((s) => { const sel = { ...s.sel }; ids.forEach((i) => delete sel[i]); return { tasks: s.tasks.filter((t) => !set.has(t.id)), sel }; });
  };
  const remove = async (ids) => { await Promise.all(ids.map((id) => api.delete_task(id))); dropIds(ids); toast('Deleted'); };
  const applyOrder = (order) => setState((s) => {
    const pos = new Map(order.map((id, i) => [id, i]));
    return { tasks: [...s.tasks].sort((a, b) => (pos.get(a.id) ?? 1e9) - (pos.get(b.id) ?? 1e9)) };
  });
  const setDate = (ids, date) => swap(ids.map((id) => ({ ...getState().tasks.find((t) => t.id === id), date })));
  const maintenance = async () => {
    const { autoArchived } = await api.run_maintenance();
    if (!autoArchived.length) return;
    setState((s) => ({ tasks: s.tasks.map((t) => (autoArchived.includes(t.id) ? { ...t, archived: true, auto: true } : t)) }));
    toast(autoArchived.length + (autoArchived.length === 1 ? ' task older than 3 months was archived' : ' tasks older than 3 months were archived'));
  };

  // Dragging a selected task moves every selected task.
  const dragIds = () => {
    const s = getState();
    if (s.sel[s.dragId]) return Object.keys(s.sel).filter((k) => k[0] === 't');
    return s.dragId && s.dragId[0] === 't' ? [s.dragId] : [];
  };

  const A = {
    maintenance: safe(maintenance),

    // ---- period, view, filters ----
    setView: (tview) => setState({ tview, sel: {} }),
    setSort: (tsort) => setState({ tsort }),
    setScope: (tscope) => setState({ tscope, sel: {} }),
    setStat: (tstat) => setState({ tstat, sel: {} }),
    setTag: (tagF) => setState({ tagF }),
    step: (dir) => setState((s) => {
      if (s.tscope === 'week') { const w = addDays(s.tweek, 7 * dir); return { tweek: w, tmonth: monthOf(w) }; }
      const m = addMonths(s.tmonth, dir);
      return { tmonth: m, tweek: mondayOf(m + '-01') };
    }),
    today: () => setState({ tweek: mondayOf(todayISO()), tmonth: monthOf(todayISO()) }),

    // ---- selection ----
    toggleSelMode: () => setState((s) => ({ selMode: !s.selMode, sel: {} })),
    toggleSel: (id) => setState((s) => { const sel = { ...s.sel }; if (sel[id]) delete sel[id]; else sel[id] = true; return { sel }; }),
    clearSel: () => setState({ sel: {} }),
    selectAll: (ids) => setState((s) => ({ sel: ids.length > 0 && ids.every((i) => s.sel[i]) ? {} : Object.fromEntries(ids.map((i) => [i, true])) })),

    // ---- single task ----
    toggleDone: safe((t) => patch([t.id], { done: !t.done })),
    archive: safe(async (id) => { await patch([id], { archived: true }); toast('Task archived'); }),
    askDelete: (id) => ask('This task will be deleted for good.', safe(() => remove([id]))),

    // ---- bulk ----
    bulkMove: safe(async (value) => {
      if (!value) return;
      const ids = Object.keys(getState().sel).filter((i) => i[0] === 't');
      const date = value === 'none' ? '' : value;
      await api.move(ids, { date });
      setDate(ids, date);
      setState({ sel: {} });
      toast(ids.length + ' moved');
    }),
    bulkArchive: safe(async () => {
      const ids = Object.keys(getState().sel);
      await patch(ids, { archived: true });
      setState({ sel: {} });
      toast(ids.length + ' archived');
    }),
    askBulkDelete: () => {
      const ids = Object.keys(getState().sel);
      ask('Delete ' + ids.length + ' selected item' + (ids.length === 1 ? '' : 's') + ' for good?', safe(() => remove(ids)));
    },

    // ---- drag and drop ----
    dragStart: (id) => (e) => {
      try { e.dataTransfer.setData('text/plain', id); e.dataTransfer.effectAllowed = 'move'; } catch (x) { /* ignore */ }
      setState({ dragId: id });
    },
    dragEnd: () => setState(idle),
    over: (key) => (e) => { e.preventDefault(); if (getState().overKey !== key) setState({ overKey: key }); },
    leave: (key) => (e) => { if (getState().overKey === key && !e.currentTarget.contains(e.relatedTarget)) setState({ overKey: null }); },
    dropOnDay: (date) => safe(async (e) => {
      e.preventDefault();
      const ids = dragIds();
      setState(idle);
      if (!ids.length) return;
      await api.move(ids, { date });
      setDate(ids, date);
      toast(ids.length > 1 ? ids.length + ' tasks moved' : 'Task moved');
    }),
    // Drop on a task: take that task's day and sit right before it (this is what Manual sort uses).
    dropOnTask: (t) => safe(async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const ids = dragIds();
      setState(idle);
      if (!ids.length || ids.includes(t.id)) return;
      await api.move(ids, { date: t.date });
      setDate(ids, t.date);
      const { ids: order } = await api.reorder(ids, t.id);
      applyOrder(order);
    }),

    // ---- task modal ----
    openTask: (id, day) => {
      const t = id && getState().tasks.find((x) => x.id === id);
      const date = t ? t.date : (day === undefined ? todayISO() : day);
      setState({ modal: { kind: 'task', id: id || null, title: t ? t.title : '', text: t ? t.notes : '', images: t ? { ...(t.images || {}) } : {}, time: t ? (t.time || '') : '', date: date || '', tags: t ? [...t.tags] : [], newTag: '', err: '' } });
    },
    openTags: () => setState((s) => ({ modal: { kind: 'tag', id: null, title: '', color: PAL[s.tags.length % 6], err: '' } })),
    setModal: (p) => setState((s) => ({ modal: { ...s.modal, ...(typeof p === 'function' ? p(s.modal) : p) } })),
    toast,
    closeModal: () => setState({ modal: null }),
    saveTask: safe(async () => {
      const md = getState().modal;
      const title = (md.title || '').trim();
      if (!title) { A.setModal({ err: 'Please add a name first.' }); return; }
      const f = { title, notes: md.text, images: pruneImgs(md.text, md.images), date: md.date || '', time: md.time || '', tags: md.tags };
      if (md.id) swap([await api.update_task(md.id, f)]);
      else { const t = await api.create_task(f); setState((s) => ({ tasks: [...s.tasks, t] })); }
      setState({ modal: null });
      toast('Saved');
      await maintenance();
    }),
    archiveFromModal: safe(async () => { const id = getState().modal.id; await patch([id], { archived: true }); setState({ modal: null }); toast('Archived'); }),
    deleteFromModal: () => { const id = getState().modal.id; setState({ modal: null }); ask('Delete this for good? This cannot be undone.', safe(() => remove([id]))); },

    // ---- tags ----
    addTagToModal: safe(async () => {
      const md = getState().modal;
      const name = (md.newTag || '').trim();
      if (!name) return;
      const g = await api.create_tag({ name, color: PAL[getState().tags.length % 6] });
      setState((s) => ({ tags: [...s.tags, g], modal: { ...s.modal, tags: [...s.modal.tags, g.id], newTag: '' } }));
    }),
    saveTag: safe(async () => {
      const md = getState().modal;
      const name = (md.title || '').trim();
      if (!name) { setState({ modal: null }); return; }
      const g = await api.create_tag({ name, color: md.color });
      setState((s) => ({ tags: [...s.tags, g], modal: { ...s.modal, title: '', color: PAL[(s.tags.length + 1) % 6] } }));
      toast('Tag added');
    }),
    askDeleteTag: (g) => ask('Delete the tag "' + g.name + '"? It will be removed from every task and note.', safe(async () => {
      await api.delete_tag(g.id);
      setState((s) => ({
        tags: s.tags.filter((t) => t.id !== g.id),
        tasks: s.tasks.map((t) => ({ ...t, tags: (t.tags || []).filter((x) => x !== g.id) })),
        notes: s.notes.map((n) => ({ ...n, tags: (n.tags || []).filter((x) => x !== g.id) })),
        tagF: s.tagF === g.id ? null : s.tagF
      }));
      toast('Tag deleted');
    }))
  };
  return A;
}
