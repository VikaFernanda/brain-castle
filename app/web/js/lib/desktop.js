// Desktop behaviour that adds no visible UI: keyboard shortcuts, drag and drop safety,
// and blocking browser behaviours in the release build (--debug turns those blocks off).

// ---------- keyboard shortcuts ----------

// Pure: which shortcut does this key press mean for this state? Returns a name or null.
export function shortcutFor(e, s) {
  const key = (e.key || '').toLowerCase();
  const ctrl = (e.ctrlKey || e.metaKey) && !e.altKey && !e.shiftKey;
  const dialog = !!(s.modal || s.confirm);
  if (ctrl && key === 'k') return dialog ? 'none' : 'search';
  if (ctrl && key === 'n') {
    if (dialog || e.repeat) return 'none'; // still swallow the key so the browser does not act on it
    return s.area === 'tasks' ? 'new-task' : s.area === 'diary' ? 'new-note' : 'none';
  }
  if (key === 'escape') {
    if (s.confirm) return 'close-confirm';
    if (s.modal) return null; // the modal closes itself
    if (s.themeOpen) return 'close-themes';
    if (s.q) return 'clear-search';
    if (s.selMode || Object.keys(s.sel).length) return 'leave-select';
  }
  return null;
}

export function installShortcuts({ store, actions, T, D }) {
  document.addEventListener('keydown', (e) => {
    const s = store.getState();
    const name = shortcutFor(e, s);
    if (!name) return;
    const run = {
      search: () => { const i = document.querySelector('header input[type=text]'); if (i) { i.focus(); i.select(); } },
      'new-task': () => T.openTask(null),
      'new-note': () => D.openNote(null, s.openBook || undefined),
      'close-confirm': () => store.setState({ confirm: null }),
      'close-themes': () => store.setState({ themeOpen: false }),
      'clear-search': () => actions.clearSearch(),
      'leave-select': () => actions.resetSel(),
      none: () => {}
    }[name];
    e.preventDefault();
    // This listener is registered before the modal's, so the modal under a confirm never sees this Esc.
    if (name === 'close-confirm') e.stopImmediatePropagation();
    run();
  });
}

// ---------- drag and drop safety ----------

const hasFiles = (e) => !!e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files');
// Places that really take dropped files: the editor text box and the preview blocks of a modal.
const inEditor = (t) => !!(t && t.closest && t.closest('[role=dialog] textarea, [role=dialog] .block, [role=dialog] [data-drop]'));
const asElement = (t) => (t && t.nodeType === 3 ? t.parentElement : t);

export function installDropGuards() {
  // Bubble phase: the editor and the item drop zones already ran. Whatever is left is outside them.
  window.addEventListener('dragover', (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault();
    if (!inEditor(e.target)) e.dataTransfer.dropEffect = 'none';
  });
  window.addEventListener('drop', (e) => { if (hasFiles(e)) e.preventDefault(); });
  // Only our own draggable items (cards, books) may start a drag. A selected text, a link or an image
  // must not, or it would be dropped on a day or a book as if it were an item.
  window.addEventListener('dragstart', (e) => {
    const t = asElement(e.target);
    if (t && t.closest && t.closest('input,textarea')) return;
    if (!(e.target.nodeType === 1 && e.target.matches('[draggable="true"]'))) e.preventDefault();
  }, true);
  // Pressing on a draggable item while some text is selected would drag the text instead of the item.
  window.addEventListener('mousedown', (e) => {
    const t = asElement(e.target);
    if (!t || !t.closest || !t.closest('[draggable="true"]') || t.closest('input,textarea')) return;
    const sel = window.getSelection && window.getSelection();
    if (sel && !sel.isCollapsed) sel.removeAllRanges();
  }, true);
}

// ---------- release build: no browser behaviours ----------

export function blocksKey(e) {
  const k = (e.key || '').toLowerCase();
  const ctrl = e.ctrlKey || e.metaKey;
  if (k === 'f5' || k === 'f12') return true;
  if (ctrl && (k === 'r' || k === 'u' || k === 'p' || k === 's')) return true;
  if (ctrl && e.shiftKey && ['i', 'j', 'c', 'r'].includes(k)) return true;
  if (ctrl && ['+', '=', '-', '_', '0'].includes(k)) return true; // zoom
  if (e.altKey && (k === 'arrowleft' || k === 'arrowright')) return true; // history back / forward
  return false;
}

export function installReleaseGuards() {
  window.addEventListener('keydown', (e) => { if (blocksKey(e)) { e.preventDefault(); e.stopPropagation(); } }, true);
  window.addEventListener('contextmenu', (e) => e.preventDefault(), true);
  window.addEventListener('wheel', (e) => { if (e.ctrlKey) e.preventDefault(); }, { passive: false, capture: true });
}

// Desktop window = ?host=py. A normal browser (tests, screenshots) keeps every browser behaviour.
export function installDesktop({ store, actions, T, D }) {
  const q = new URLSearchParams(window.location.search);
  installShortcuts({ store, actions, T, D });
  installDropGuards();
  if (q.get('host') === 'py' && q.get('debug') !== '1') installReleaseGuards();
}
