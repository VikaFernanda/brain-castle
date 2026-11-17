// After a failed call the screen may no longer match the data: reload it from Python.
// A failing reload must not throw again (the error toast is already showing).
export async function reloadQuietly(reload) {
  if (typeof reload !== 'function') return;
  try { await reload(); } catch (e) { /* keep what is on screen */ }
}
