// App shell: top bar + sidebar + main area. Markup and inline styles copied from the design.
import { html } from './html.js';
import { Icon, CastleLogo } from './components/Icon.js';
import { Button } from './components/Button.js';
import { IconButton } from './components/IconButton.js';
import { Chip } from './components/Chip.js';
import { Card } from './components/Card.js';

export const THEMES = {
  pink: { name: 'Pink & Yellow', c1: '#FFB8CC', c2: '#FFE58F' },
  blue: { name: 'Blue & Purple', c1: '#B3C0FF', c2: '#DCC4FF' },
  teal: { name: 'Teal Green & Pink', c1: '#92E3CF', c2: '#FFBBD0' }
};
const NAV_ON = 'background:var(--surface);box-shadow:0 2px 0 var(--line)';
const AREA_NAME = { tasks: 'Tasks', diary: 'Diary', archive: 'Archive' };
const CRUMB_ON = 'font-weight:800;color:var(--ink)';
const CRUMB_OFF = 'font-weight:600';

// Same rules as the design's crumbs. Sub-views are fixed for Phase 1 (the pages add their own later).
export function buildCrumbs(s, actions) {
  const q = s.q.trim();
  if (q) {
    return [
      { label: 'Search', go: actions.clearSearch, style: CRUMB_OFF, sep: false },
      { label: '"' + q + '"', go: () => {}, style: CRUMB_ON, sep: true, current: true }
    ];
  }
  const list = [{ label: AREA_NAME[s.area], go: () => actions.go(s.area), current: s.area === 'archive' }];
  if (s.area === 'tasks') list.push({ label: s.tview === 'list' ? 'Week list' : 'Calendar board', go: () => {}, current: true });
  if (s.area === 'diary') list.push({ label: s.dview === 'list' ? 'List' : 'Board', go: () => {}, current: true });
  return list.map((c, i) => ({ ...c, sep: i > 0, style: c.current ? CRUMB_ON : CRUMB_OFF }));
}

function ThemeMenu({ theme, open, onToggle, onPick }) {
  return html`<div style="position:relative">
    <${Button} variant="yellow" icon="palette" aria-expanded=${open} onClick=${onToggle}>Themes<//>
    ${open ? html`<div class="card" role="menu" aria-label="Themes" style="position:absolute;right:0;top:52px;width:270px;padding:10px;display:flex;flex-direction:column;gap:6px;box-shadow:0 10px 30px rgba(60,30,45,.18)">
      ${Object.keys(THEMES).map((k) => html`<button type="button" key=${k} role="menuitemradio" aria-checked=${theme === k} onClick=${() => onPick(k)} style=${'display:flex;align-items:center;gap:12px;min-height:48px;padding:0 12px;border-radius:14px;border:0;font-size:15px;font-weight:700;color:var(--ink);cursor:pointer;' + (theme === k ? 'background:var(--accent-soft)' : 'background:transparent')}>
        <span style="display:inline-flex;flex:none">
          <span style=${'width:22px;height:22px;border-radius:50%;border:2px solid #fff;background:' + THEMES[k].c1}></span>
          <span style=${'width:22px;height:22px;border-radius:50%;border:2px solid #fff;margin-left:-8px;background:' + THEMES[k].c2}></span>
        </span>
        <span style="flex:1;text-align:left">${THEMES[k].name}</span>
        ${theme === k ? html`<${Icon} name="check" />` : null}
      </button>`)}
    </div>` : null}
  </div>`;
}

export function TopBar({ state, actions }) {
  const crumbs = buildCrumbs(state, actions);
  return html`<header style="display:flex;flex-wrap:wrap;align-items:center;gap:12px 24px;padding:12px 24px;background:var(--surface);border-bottom:1.5px solid var(--line);position:relative;z-index:20">
    <div style="display:flex;align-items:center;gap:10px;min-width:190px">
      <${CastleLogo} />
      <span style="font-family:Fredoka,system-ui,sans-serif;font-size:26px;font-weight:600;letter-spacing:.2px">Brain Castle</span>
    </div>
    <nav aria-label="Breadcrumb" style="display:flex;align-items:center;flex-wrap:wrap;flex:1 1 220px;min-width:0">
      ${crumbs.map((c) => html`<span key=${c.label} style="display:inline-flex;align-items:center">
        ${c.sep ? html`<${Icon} name="chevronRight" size=${14} style="color:var(--muted)" />` : null}
        <button type="button" class="crumb" aria-current=${c.current ? 'page' : undefined} onClick=${c.go} style=${c.style}>${c.label}</button>
      </span>`)}
    </nav>
    <div style="flex:1 1 280px;max-width:420px;position:relative">
      <${Icon} name="search" style="position:absolute;left:14px;top:13px;color:var(--muted)" />
      <input class="field" type="text" aria-label="Search all tasks, notes and tags" placeholder="Search all tasks and notes" value=${state.q} onInput=${(e) => actions.setQuery(e.target.value)} style="padding-left:42px;padding-right:46px;border-radius:999px;background:var(--bg)" />
      ${state.q ? html`<${IconButton} icon="close" label="Clear search" onClick=${actions.clearSearch} style="position:absolute;right:2px;top:2px" />` : null}
    </div>
    <${ThemeMenu} theme=${state.theme} open=${state.themeOpen} onToggle=${actions.toggleThemeMenu} onPick=${actions.pickTheme} />
  </header>`;
}

function NavItem({ icon, label, count, chipBg, on, onClick }) {
  return html`<button type="button" class="nav" aria-current=${on ? 'page' : undefined} onClick=${onClick} style=${on ? NAV_ON : ''}>
    <${Icon} name=${icon} size=${22} />
    <span style="flex:1">${label}</span>
    <${Chip} bg=${chipBg}>${count}<//>
  </button>`;
}

export function Sidebar({ state, counts, actions }) {
  const inArea = (a) => state.area === a;
  return html`<aside class="side" aria-label="Main navigation" style="flex:0 0 244px;background:var(--side);padding:20px 14px;display:flex;flex-direction:column;gap:6px">
    <${NavItem} icon="tasks" label="Tasks" count=${counts.openTasks} chipBg="var(--accent)" on=${inArea('tasks')} onClick=${() => actions.go('tasks')} />
    <${NavItem} icon="diary" label="Diary" count=${counts.books} chipBg="var(--accent2)" on=${inArea('diary')} onClick=${() => actions.go('diary')} />
    <div class="push" style="margin-top:auto;padding-top:24px">
      <${NavItem} icon="archive" label="Archive" count=${counts.archive} chipBg="var(--surface)" on=${inArea('archive')} onClick=${() => actions.go('archive')} />
    </div>
  </aside>`;
}

// Placeholder area page. Real pages replace this in later phases.
export function PlaceholderPage({ title, sub }) {
  return html`<div>
    <h1 style="font-size:34px">${title}</h1>
    <div style="color:var(--muted);font-weight:600">${sub}</div>
  </div>`;
}

export function SearchPlaceholder({ q }) {
  return html`<div>
    <h1 style="font-size:34px">Search results</h1>
    <div style="color:var(--muted);font-weight:600">Showing results for "${q.trim()}" will come in a later phase.</div>
  </div>`;
}

export { Card };
