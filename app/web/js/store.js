// Tiny store, same idea as the design's setState: setState(patch) or setState(fn(state) => patch).
import { useEffect, useState } from 'preact/hooks';

export function createStore(initial) {
  let state = initial;
  const subs = new Set();
  return {
    getState: () => state,
    setState(patch) {
      const p = typeof patch === 'function' ? patch(state) : patch;
      if (!p) return;
      state = { ...state, ...p };
      subs.forEach((fn) => fn(state));
    },
    subscribe(fn) { subs.add(fn); return () => subs.delete(fn); }
  };
}

// Re-render a component whenever the store changes.
export function useStore(store) {
  const [s, set] = useState(store.getState());
  useEffect(() => store.subscribe(set), [store]);
  return s;
}
