import { render } from 'preact';
import { html } from './html.js';
import { createStore, useStore } from './store.js';
import { createApi } from './api.js';
import { TopBar, Sidebar, THEMES } from './shell.js';
import { Toast } from './components/Toast.js';
import { ConfirmDialog } from './components/ConfirmDialog.js';
import { BulkBar } from './components/BulkBar.js';
import { TasksPage } from './pages/TasksPage.js';
import { DiaryPage } from './pages/DiaryPage.js';
import { ArchivePage } from './pages/ArchivePage.js';
import { SearchPage } from './pages/SearchPage.js';
import { createArchiveActions } from './archive/actions.js';
import { TaskModal, TagsModal } from './pages/TaskModals.js';
import { NoteModal, BookModal } from './pages/DiaryModals.js';
import { createTaskActions } from './tasks/actions.js';
import { buildTasksView } from './tasks/view.js';
import { createDiaryActions } from './diary/actions.js';
import { buildDiaryView } from './diary/view.js';
import { installDesktop } from './lib/desktop.js';
import { DAYS, fmt, mondayOf, monthOf, todayISO } from './lib/dates.js';

const api = createApi();
const store = createStore({
  area: 'tasks', tview: 'list', dview: 'list', theme: 'pink', themeOpen: false, q: '',
  tasks: [], notes: [], books: [], tags: [], toast: '', confirm: null, loaded: false,
  tsort: 'manual', tscope: 'week', tweek: mondayOf(todayISO()), tmonth: monthOf(todayISO()), tstat: 'all',
  bsort: 'manual', nsort: 'manual', bscope: 'all', bweek: mondayOf(todayISO()), bmonth: monthOf(todayISO()), expanded: { b1: true }, openBook: null,
  tagF: null, selMode: false, sel: {}, modal: null, dragId: null, overKey: null
});
const { setState } = store;

let toastTimer;
const toast = (msg) => {
  setState({ toast: msg });
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => setState({ toast: '' }), 2600);
};

// All view actions in one place. Pages added later get their own action files.
const actions = {
  go: (area) => setState({ area, themeOpen: false, q: '', sel: {}, selMode: false, tagF: null, modal: null, openBook: null }),
  resetSel: () => setState({ sel: {}, selMode: false }),
  closeBook: () => setState({ openBook: null, sel: {} }),
  setQuery: (q) => setState({ q }),
  clearSearch: () => setState({ q: '' }),
  toggleThemeMenu: () => setState((s) => ({ themeOpen: !s.themeOpen })),
  pickTheme: (theme) => {
    setState({ theme, themeOpen: false });
    api.set_settings({ theme }).catch((e) => { toast(e && e.message ? e.message : 'Something went wrong'); reload().catch(() => {}); });
  },
  toast,
  ask: (text, yes) => setState({ confirm: { text, yes } })
};
// Python is the source of truth: load everything again (start, and after a failed call).
const reload = async () => {
  const d = await api.load_all();
  setState((s) => {
    const alive = new Set([...d.tasks, ...d.notes, ...d.books].map((x) => x.id));
    const sel = Object.fromEntries(Object.keys(s.sel).filter((i) => alive.has(i)).map((i) => [i, true]));
    return { tasks: d.tasks, notes: d.notes, books: d.books, tags: d.tags, sel, openBook: alive.has(s.openBook) ? s.openBook : null,
      theme: THEMES[d.settings.theme] ? d.settings.theme : s.theme };
  });
};
const T = createTaskActions({ api, store, toast, ask: actions.ask, reload });
const D = createDiaryActions({ api, store, toast, ask: actions.ask, T, reload });
const R = createArchiveActions({ api, store, toast, ask: actions.ask, T });

// Click a search result: tasks and notes open their modal, a book opens in the Diary board.
const openResult = (r) => {
  if (r.kind === 'task') T.openTask(r.id);
  else if (r.kind === 'note') D.openNote(r.id);
  else setState({ area: 'diary', dview: 'board', openBook: r.id, q: '', sel: {}, selMode: false });
};

function App() {
  const s = useStore(store);
  const counts = {
    openTasks: s.tasks.filter((t) => !t.archived && !t.done).length,
    books: s.books.filter((b) => !b.archived).length,
    archive: s.tasks.filter((t) => t.archived).length + s.notes.filter((n) => n.archived).length + s.books.filter((b) => b.archived).length
  };
  const isTasks = s.area === 'tasks' && !s.q.trim();
  const view = isTasks ? buildTasksView(s) : null;
  const isDiary = s.area === 'diary' && !s.q.trim();
  const dview = isDiary ? buildDiaryView(s) : null;
  const selCount = Object.keys(s.sel).length;
  const dayOpts = view ? [{ value: '', label: 'Move to...' }].concat(view.weekDates.map((d, i) => ({ value: d, label: DAYS[i] + ' · ' + fmt(d) })), [{ value: 'none', label: 'No date yet' }]) : [];
  const bookOpts = dview ? [{ value: '', label: 'Move to book...' }].concat(dview.actBooks.map((b) => ({ value: b.id, label: b.name }))) : [];
  const hasSelNote = Object.keys(s.sel).some((i) => i[0] === 'n');
  return html`<div class="bc appbox" data-theme=${s.theme} style="height:100vh;overflow:hidden;display:flex;flex-direction:column">
    <${TopBar} state=${s} actions=${actions} />
    <div class="shell">
      <${Sidebar} state=${s} counts=${counts} actions=${actions} />
      <main class="mainpane" style="flex:1 1 0;min-width:0;padding:24px 28px 120px;display:flex;flex-direction:column;gap:20px">
        ${s.q.trim() ? html`<${SearchPage} s=${s} onOpen=${openResult} />` : isTasks ? html`<${TasksPage} s=${s} A=${T} />` : isDiary ? html`<${DiaryPage} s=${s} A=${D} />` : html`<${ArchivePage} s=${s} A=${R} />`}
      </main>
    </div>
    ${isTasks && selCount > 0 ? html`<${BulkBar} count=${selCount} moveOptions=${dayOpts} moveLabel="Move selected tasks to a day" onMove=${(e) => { T.bulkMove(e.target.value); e.target.value = ''; }} onArchive=${T.bulkArchive} onDelete=${T.askBulkDelete} onClear=${T.clearSel} onSelectAll=${() => T.selectAll(view.visibleIds)} selectAllLabel=${view.visibleIds.length > 0 && view.visibleIds.every((i) => s.sel[i]) ? 'Clear selection' : 'Select all'} />` : null}
    ${isDiary && selCount > 0 ? html`<${BulkBar} count=${selCount} moveOptions=${hasSelNote ? bookOpts : null} moveLabel="Move selected notes to a book" onMove=${(e) => { D.bulkMove(e.target.value); e.target.value = ''; }} onArchive=${D.bulkArchive} onDelete=${D.askBulkDelete} onClear=${D.clearSel} onSelectAll=${() => D.selectAll(dview.visibleIds)} selectAllLabel=${dview.visibleIds.length > 0 && dview.visibleIds.every((i) => s.sel[i]) ? 'Clear selection' : 'Select all'} />` : null}
    ${s.modal && s.modal.kind === 'note' ? html`<${NoteModal} s=${s} A=${D} />` : null}
    ${s.modal && s.modal.kind === 'book' ? html`<${BookModal} s=${s} A=${D} />` : null}
    ${s.modal && s.modal.kind === 'task' ? html`<${TaskModal} s=${s} A=${T} />` : null}
    ${s.modal && s.modal.kind === 'tag' ? html`<${TagsModal} s=${s} A=${T} />` : null}
    <${Toast} message=${s.toast} />
    ${s.confirm ? html`<${ConfirmDialog} text=${s.confirm.text} onCancel=${() => setState({ confirm: null })} onYes=${() => { const c = s.confirm; setState({ confirm: null }); c.yes(); }} />` : null}
  </div>`;
}

async function boot() {
  render(html`<${App} />`, document.getElementById('root'));
  try { await reload(); } catch (e) { toast(e && e.message ? e.message : 'Could not load your data'); }
  setState({ loaded: true });
  await T.maintenance();
}
boot();

// Shortcuts (Ctrl+K, Ctrl+N, Esc), drag and drop safety, release-build blocks. No new UI.
// Registered before any modal, so its Esc rules run first.
installDesktop({ store, actions, T, D });

// Auto-archive again at every midnight while the app is open.
function scheduleMidnight() {
  const n = new Date();
  const ms = new Date(n.getFullYear(), n.getMonth(), n.getDate() + 1, 0, 0, 1) - n;
  setTimeout(async () => { await T.maintenance(); scheduleMidnight(); }, ms);
}
scheduleMidnight();

// Auto-archive also when the window gets focus (after the PC slept) and every hour.
window.addEventListener('focus', () => { T.maintenance(); });
setInterval(() => { T.maintenance(); }, 60 * 60 * 1000);

// Exposed for dev tools and Playwright only.
window.__bc = { store, api, actions, reload };
