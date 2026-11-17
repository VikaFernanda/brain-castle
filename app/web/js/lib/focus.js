// Keyboard focus for dialogs: move focus in when the dialog opens, keep Tab inside it,
// and give focus back to the element that opened it when it closes.
import { useEffect } from 'preact/hooks';

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]):not([type=hidden]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
const FIRST_FIELD = 'input[type=text],textarea';

export const focusables = (root) => Array.from(root.querySelectorAll(FOCUSABLE));

// What Tab / Shift+Tab should do inside a dialog: the element to focus, or null to let the browser decide.
export function nextTabTarget(list, active, shift) {
  if (!list.length) return null;
  const i = list.indexOf(active);
  if (shift && i <= 0) return list[list.length - 1];
  if (!shift && (i === -1 || i === list.length - 1)) return list[0];
  return null;
}

export function useDialogFocus(ref, { fields = true } = {}) {
  useEffect(() => {
    const root = ref.current;
    if (!root) return undefined;
    const opener = document.activeElement;
    const start = (fields && root.querySelector(FIRST_FIELD)) || focusables(root)[0] || root;
    start.focus({ preventScroll: true });
    const onKey = (e) => {
      if (e.key !== 'Tab') return;
      const list = focusables(root);
      const target = nextTabTarget(list, document.activeElement, e.shiftKey);
      if (target) { e.preventDefault(); target.focus(); } else if (!list.length) e.preventDefault();
    };
    root.addEventListener('keydown', onKey);
    return () => {
      root.removeEventListener('keydown', onKey);
      if (opener && opener !== document.body && opener.isConnected) opener.focus({ preventScroll: true });
    };
  }, []);
}
