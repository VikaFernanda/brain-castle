// ONE interface for data. The UI only talks to `api`. Phase 1 has MockApi (in memory, browser only).
// Later a PywebviewApi with the same method names forwards each call to Python (window.pywebview.api).
// Every method is async and returns plain JSON. See docs/data-contract.md for fields and rules.
import { sampleData } from './mock-data.js';

export const API_METHODS = [
  'load_all',
  'create_task', 'update_task', 'delete_task', 'archive_task', 'restore_task',
  'create_note', 'update_note', 'delete_note', 'archive_note', 'restore_note',
  'create_book', 'update_book', 'delete_book', 'archive_book', 'restore_book',
  'create_tag', 'update_tag', 'delete_tag',
  'reorder', 'move', 'run_maintenance', 'get_settings', 'set_settings'
];

const KINDS = { task: 'tasks', note: 'notes', book: 'books' };
const PREFIX = { t: 'task', n: 'note', b: 'book', g: 'tag', i: 'image' };
const SETTINGS_DEFAULTS = { theme: 'pink' };
const THEME_KEY = 'bc-theme';
const clone = (x) => JSON.parse(JSON.stringify(x));

export class MockApi {
  constructor(seed = sampleData()) {
    this.db = clone(seed);
    this.seq = 100;
  }
  _id(prefix) { this.seq += 1; return prefix + this.seq; }
  _list(kind) { return this.db[KINDS[kind]]; }
  _find(kind, id) { return this._list(kind).find((x) => x.id === id); }
  _byId(id) { const kind = PREFIX[id[0]]; return kind && KINDS[kind] ? { kind, item: this._find(kind, id) } : { kind: null, item: null }; }

  async load_all() {
    return clone({ tasks: this.db.tasks, notes: this.db.notes, books: this.db.books, tags: this.db.tags, settings: await this.get_settings() });
  }

  // ---- generic CRUD, used by the typed methods below ----
  _create(kind, fields) {
    const letter = { task: 't', note: 'n', book: 'b' }[kind];
    const item = { ...fields, id: this._id(letter), archived: false, created: Date.now() };
    this._list(kind).push(item);
    return clone(item);
  }
  _update(kind, id, fields) {
    const item = this._find(kind, id);
    if (!item) throw new Error(kind + ' not found: ' + id);
    const { id: _ignore, ...rest } = fields;
    Object.assign(item, rest);
    return clone(item);
  }
  _delete(kind, id) {
    this.db[KINDS[kind]] = this._list(kind).filter((x) => x.id !== id);
    if (kind === 'book') this.db.notes = this.db.notes.filter((n) => n.bookId !== id); // deleting a book deletes its notes
    return { id };
  }
  _archive(kind, id) { return this._update(kind, id, { archived: true }); }
  _restore(kind, id) {
    const item = this._update(kind, id, { archived: false, auto: false, keep: true });
    if (kind === 'note') this._update('book', item.bookId, { archived: false }); // a restored note needs its book
    return item;
  }

  async create_task(f) { return this._create('task', { title: '', notes: '', date: '', time: '', tags: [], images: {}, done: false, ...f }); }
  async update_task(id, f) { return this._update('task', id, f); }
  async delete_task(id) { return this._delete('task', id); }
  async archive_task(id) { return this._archive('task', id); }
  async restore_task(id) { return this._restore('task', id); }

  async create_note(f) { return this._create('note', { title: '', body: '', bookId: '', date: '', tags: [], images: {}, ...f }); }
  async update_note(id, f) { return this._update('note', id, f); }
  async delete_note(id) { return this._delete('note', id); }
  async archive_note(id) { return this._archive('note', id); }
  async restore_note(id) { return this._restore('note', id); }

  async create_book(f) { return this._create('book', { name: '', color: '', date: '', ...f }); }
  async update_book(id, f) { return this._update('book', id, f); }
  async delete_book(id) { return this._delete('book', id); }
  async archive_book(id) { return this._archive('book', id); }
  async restore_book(id) { return this._restore('book', id); }

  async create_tag(f) { const t = { id: this._id('g'), name: '', color: '', ...f }; this.db.tags.push(t); return clone(t); }
  async update_tag(id, f) {
    const t = this.db.tags.find((x) => x.id === id);
    if (!t) throw new Error('tag not found: ' + id);
    Object.assign(t, f, { id });
    return clone(t);
  }
  async delete_tag(id) {
    this.db.tags = this.db.tags.filter((t) => t.id !== id);
    this.db.tasks.forEach((t) => { t.tags = (t.tags || []).filter((x) => x !== id); });
    this.db.notes.forEach((n) => { n.tags = (n.tags || []).filter((x) => x !== id); });
    return { id };
  }

  // reorder(ids, beforeId): put `ids` (all one kind) right before `beforeId`; null = at the end.
  async reorder(ids, beforeId = null) {
    const first = this._byId(ids[0]);
    if (!first.kind) throw new Error('unknown id: ' + ids[0]);
    const key = KINDS[first.kind];
    const moved = this.db[key].filter((x) => ids.includes(x.id));
    const rest = this.db[key].filter((x) => !ids.includes(x.id));
    const i = beforeId ? rest.findIndex((x) => x.id === beforeId) : -1;
    rest.splice(i < 0 ? rest.length : i, 0, ...moved);
    this.db[key] = rest;
    return { ids: rest.map((x) => x.id) };
  }
  // move(ids, target): task target {date: 'YYYY-MM-DD' | ''}, note target {bookId}.
  async move(ids, target) {
    ids.forEach((id) => {
      const { kind } = this._byId(id);
      if (kind === 'task') this._update('task', id, { date: target.date || '' });
      else if (kind === 'note') this._update('note', id, { bookId: target.bookId });
      else throw new Error('cannot move ' + id);
    });
    return { ids };
  }
  // Archives tasks dated more than 3 months ago (unless the user restored them). Returns their ids.
  async run_maintenance() {
    const n = new Date();
    const cut = (d => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'))(new Date(n.getFullYear(), n.getMonth() - 3, n.getDate()));
    const ids = this.db.tasks.filter((t) => !t.archived && !t.keep && t.date && t.date < cut).map((t) => t.id);
    this.db.tasks.forEach((t) => { if (ids.includes(t.id)) { t.archived = true; t.auto = true; } });
    return { autoArchived: ids };
  }

  async get_settings() {
    let theme = SETTINGS_DEFAULTS.theme;
    try { theme = localStorage.getItem(THEME_KEY) || theme; } catch (e) { /* storage blocked */ }
    return { ...SETTINGS_DEFAULTS, ...(this.db.settings || {}), theme };
  }
  async set_settings(patch) {
    this.db.settings = { ...(this.db.settings || {}), ...patch };
    if (patch.theme) { try { localStorage.setItem(THEME_KEY, patch.theme); } catch (e) { /* storage blocked */ } }
    return this.get_settings();
  }
}

// The single entry point. Phase 1: always MockApi. Later: window.pywebview ? new PywebviewApi() : new MockApi().
export function createApi() { return new MockApi(); }
