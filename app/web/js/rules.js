// ALL data rules in ONE module (Phase 6 ports this file to Python, function by function).
// Pure functions: plain data in, plain data out. No DOM, no Date objects in the results.
// Rules (see docs/data-contract.md):
//   - Archiving a book hides its notes (the notes' own flags are not changed).
//   - Restoring a note also restores its book. Restoring sets archived=false, auto=false, keep=true.
//   - Deleting a book deletes its notes. Deleting a tag removes it from every task and note.
//   - Auto-archive: tasks with a date older than 3 calendar months. No date = never. keep=true = never.
import { iso, parseD } from './lib/dates.js';

export const AUTO_ARCHIVE_MONTHS = 3;

// Today minus 3 calendar months, "YYYY-MM-DD". When the target month is shorter the day is clamped
// to its last day (May 31 -> Feb 28, Dec 31 -> Sep 30). The same as dateutil's relativedelta(months=-3).
export function cutoffDate(today, months = AUTO_ARCHIVE_MONTHS) {
  const t = parseD(today);
  const first = new Date(t.getFullYear(), t.getMonth() - months, 1);
  const last = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
  return iso(new Date(first.getFullYear(), first.getMonth(), Math.min(t.getDate(), last)));
}

// Ids of the tasks to archive. A task dated exactly on the cutoff day is NOT older, so it stays.
export function autoArchiveIds(tasks, today) {
  const cut = cutoffDate(today);
  return tasks.filter((t) => !t.archived && !t.keep && t.date && t.date < cut).map((t) => t.id);
}

// Restore: the item comes back and is never auto-archived again. A note also brings its book back.
export function restoreFields() { return { archived: false, auto: false, keep: true }; }
export function restoreBookIdOfNote(note) { return note.bookId; }

// Delete a book: its notes go with it.
export function notesAfterBookDelete(notes, bookId) { return notes.filter((n) => n.bookId !== bookId); }

// Delete a tag: take its id off every item.
export function withoutTag(items, tagId) {
  return items.map((x) => ((x.tags || []).includes(tagId) ? { ...x, tags: x.tags.filter((i) => i !== tagId) } : x));
}
