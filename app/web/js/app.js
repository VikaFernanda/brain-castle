import { render } from 'preact';
import { html } from './html.js';
import { createStore, useStore } from './store.js';
import { createApi } from './api.js';
import { TopBar, Sidebar, PlaceholderPage, SearchPlaceholder, THEMES } from './shell.js';
import { Toast } from './components/Toast.js';
import { ConfirmDialog } from './components/ConfirmDialog.js';
import { BulkBar } from './components/BulkBar.js';
import { TasksPage } from './pages/TasksPage.js';
import { TaskModal, TagsModal } from './pages/TaskModals.js';
import { createTaskActions } from './tasks/actions.js';
import { buildTasksView } from './tasks/view.js';
import { DAYS, fmt, mondayOf, monthOf, todayISO } from './lib/dates.js';

const api = createApi();
const store = createStore({
  area: 'tasks', tview: 'list', dview: 'list', theme: 'pink', themeOpen: false, q: '',
  tasks: [], notes: [], books: [], tags: [], toast: '', confirm: null, loaded: false,
  tsort: 'manual', tscope: 'week', tweek: mondayOf(todayISO()), tmonth: monthOf(todayISO()), tstat: 'all',
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
  go: (area) => setState({ area, themeOpen: false, q: '', sel: {}, selMode: false, tagF: null, modal: null }),
  setQuery: (q) => setState({ q }),
  clearSearch: () => setState({ q: '' }),
  toggleThemeMenu: () => setState((s) => ({ themeOpen: !s.themeOpen })),
  pickTheme: (theme) => {
    setState({ theme, themeOpen: false });
    api.set_settings({ theme });
  },
  toast,
  ask: (text, yes) => setState({ confirm: { text, yes } })
};
const T = createTaskActions({ api, store, toast, ask: actions.ask });

const SUBS = {
  diary: 'Books and notes come in a later phase.',
  archive: 'Archived items come in a later phase.'
};
const TITLES = { tasks: 'Tasks', diary: 'Diary', archive: 'Archive' };

function App() {
  const s = useStore(store);
  const counts = {
    openTasks: s.tasks.filter((t) => !t.archived && !t.done).length,
    books: s.books.filter((b) => !b.archived).length,
    archive: s.tasks.filter((t) => t.archived).length + s.notes.filter((n) => n.archived).length + s.books.filter((b) => b.archived).length
  };
  const isTasks = s.area === 'tasks' && !s.q.trim();
  const view = isTasks ? buildTasksView(s) : null;
  const selCount = Object.keys(s.sel).length;
  const dayOpts = view ? [{ value: '', label: 'Move to...' }].concat(view.weekDates.map((d, i) => ({ value: d, label: DAYS[i] + ' · ' + fmt(d) })), [{ value: 'none', label: 'No date yet' }]) : [];
  return html`<div class="bc appbox" data-theme=${s.theme} style="height:100vh;overflow:hidden;display:flex;flex-direction:column">
    <${TopBar} state=${s} actions=${actions} />
    <div class="shell">
      <${Sidebar} state=${s} counts=${counts} actions=${actions} />
      <main class="mainpane" style="flex:1 1 0;min-width:0;padding:24px 28px 120px;display:flex;flex-direction:column;gap:20px">
        ${s.q.trim() ? html`<${SearchPlaceholder} q=${s.q} />` : isTasks ? html`<${TasksPage} s=${s} A=${T} />` : html`<${PlaceholderPage} title=${TITLES[s.area]} sub=${SUBS[s.area]} />`}
      </main>
    </div>
    ${isTasks && selCount > 0 ? html`<${BulkBar} count=${selCount} moveOptions=${dayOpts} moveLabel="Move selected tasks to a day" onMove=${(e) => { T.bulkMove(e.target.value); e.target.value = ''; }} onArchive=${T.bulkArchive} onDelete=${T.askBulkDelete} onClear=${T.clearSel} onSelectAll=${() => T.selectAll(view.visibleIds)} selectAllLabel=${view.visibleIds.length > 0 && view.visibleIds.every((i) => s.sel[i]) ? 'Clear selection' : 'Select all'} />` : null}
    ${s.modal && s.modal.kind === 'task' ? html`<${TaskModal} s=${s} A=${T} />` : null}
    ${s.modal && s.modal.kind === 'tag' ? html`<${TagsModal} s=${s} A=${T} />` : null}
    <${Toast} message=${s.toast} />
    ${s.confirm ? html`<${ConfirmDialog} text=${s.confirm.text} onCancel=${() => setState({ confirm: null })} onYes=${() => { const c = s.confirm; setState({ confirm: null }); c.yes(); }} />` : null}
  </div>`;
}

async function boot() {
  render(html`<${App} />`, document.getElementById('root'));
  const data = await api.load_all();
  const theme = THEMES[data.settings.theme] ? data.settings.theme : 'pink';
  setState({ tasks: data.tasks, notes: data.notes, books: data.books, tags: data.tags, theme, loaded: true });
  await T.maintenance();
}
boot();

// Exposed for dev tools and Playwright only.
window.__bc = { store, api, actions };
