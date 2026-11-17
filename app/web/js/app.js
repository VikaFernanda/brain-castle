import { render } from 'preact';
import { html } from './html.js';
import { createStore, useStore } from './store.js';
import { createApi } from './api.js';
import { TopBar, Sidebar, PlaceholderPage, SearchPlaceholder, THEMES } from './shell.js';
import { Toast } from './components/Toast.js';
import { ConfirmDialog } from './components/ConfirmDialog.js';

const api = createApi();
const store = createStore({
  area: 'tasks', tview: 'list', dview: 'list', theme: 'pink', themeOpen: false, q: '',
  tasks: [], notes: [], books: [], tags: [], toast: '', confirm: null, loaded: false
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
  go: (area) => setState({ area, themeOpen: false, q: '' }),
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

const SUBS = {
  tasks: 'The task list and calendar board come in a later phase.',
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
  return html`<div class="bc appbox" data-theme=${s.theme} style="height:100vh;overflow:hidden;display:flex;flex-direction:column">
    <${TopBar} state=${s} actions=${actions} />
    <div class="shell">
      <${Sidebar} state=${s} counts=${counts} actions=${actions} />
      <main class="mainpane" style="flex:1 1 0;min-width:0;padding:24px 28px 120px;display:flex;flex-direction:column;gap:20px">
        ${s.q.trim() ? html`<${SearchPlaceholder} q=${s.q} />` : html`<${PlaceholderPage} title=${TITLES[s.area]} sub=${SUBS[s.area]} />`}
      </main>
    </div>
    <${Toast} message=${s.toast} />
    ${s.confirm ? html`<${ConfirmDialog} text=${s.confirm.text} onCancel=${() => setState({ confirm: null })} onYes=${() => { const c = s.confirm; setState({ confirm: null }); c.yes(); }} />` : null}
  </div>`;
}

async function boot() {
  render(html`<${App} />`, document.getElementById('root'));
  const data = await api.load_all();
  const theme = THEMES[data.settings.theme] ? data.settings.theme : 'pink';
  setState({ tasks: data.tasks, notes: data.notes, books: data.books, tags: data.tags, theme, loaded: true });
  await api.run_maintenance();
}
boot();

// Exposed for dev tools and Playwright only.
window.__bc = { store, api, actions };
