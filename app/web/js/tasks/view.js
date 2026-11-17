// Pure view logic for the Tasks area (JS owns filter, sort, group). No DOM, no api here.
import { DAYS, SHORT, addDays, mondayOf, monthOf, todayISO, weekdayIdx, fmt } from '../lib/dates.js';
import { plain } from '../lib/text.js';

export const SORT_OPTIONS = [{ value: 'new', label: 'Latest created' }, { value: 'soon', label: 'Deadline soon' }, { value: 'manual', label: 'Manual' }];

// Sort inside one day. manual = stored order. soon = time of day, items without a time last.
export function sortTasks(arr, mode) {
  if (mode === 'manual') return arr;
  const a = [...arr];
  if (mode === 'new') return a.sort((x, y) => (y.created || 0) - (x.created || 0));
  return a.sort((x, y) => {
    const kx = x.time; const ky = y.time;
    if (!kx && !ky) return (y.created || 0) - (x.created || 0);
    if (!kx) return 1;
    if (!ky) return -1;
    return kx < ky ? -1 : kx > ky ? 1 : 0;
  });
}

export const tagFilterHit = (t, tagF, tags, q) => {
  if (tagF && !(t.tags || []).includes(tagF)) return false;
  if (!q) return true;
  const tn = (t.tags || []).map((i) => (tags.find((g) => g.id === i) || {}).name || '').join(' ');
  return (t.title + ' ' + plain(t.notes) + ' ' + tn).toLowerCase().includes(q);
};

// Everything the Tasks page draws, computed from the store state.
export function buildTasksView(s) {
  const today = todayISO();
  const filtering = !!s.tagF;
  const stat = (t) => (s.tstat === 'all' ? true : s.tstat === 'done' ? !!t.done : !t.done);
  const live = s.tasks.filter((t) => !t.archived);
  const vis = live.filter((t) => stat(t) && tagFilterHit(t, s.tagF, s.tags, ''));
  const mkGroup = (date) => {
    const none = date === '';
    const all = live.filter((t) => (t.date || '') === date);
    const items = sortTasks(vis.filter((t) => (t.date || '') === date), s.tsort);
    return {
      date, key: 'd' + date,
      label: none ? 'No date yet' : DAYS[weekdayIdx(date)], short: none ? 'Later' : SHORT[weekdayIdx(date)],
      dateLabel: none ? 'Plan it when you are ready' : fmt(date),
      isToday: date === today, tasks: items,
      emptyText: filtering || s.tstat !== 'all' ? 'No matching tasks' : 'Nothing planned. Drop a task here.',
      progress: all.length ? all.filter((t) => t.done).length + ' of ' + all.length + ' done' : ''
    };
  };
  const weekDates = [0, 1, 2, 3, 4, 5, 6].map((i) => addDays(s.tweek, i));
  const weekGroups = weekDates.map(mkGroup);
  const noDay = mkGroup('');
  const mY = +s.tmonth.slice(0, 4); const mM = +s.tmonth.slice(5, 7); const mDays = new Date(mY, mM, 0).getDate();
  const monthDates = Array.from({ length: mDays }, (_, i) => s.tmonth + '-' + String(i + 1).padStart(2, '0'));
  const monthListGroups = monthDates.filter((d) => vis.some((t) => t.date === d)).map(mkGroup);
  const taskGroups = (s.tscope === 'week' ? weekGroups : monthListGroups).concat([noDay]);
  const monthWeeks = [];
  for (let d = mondayOf(monthDates[0]); d <= addDays(mondayOf(monthDates[mDays - 1]), 6); d = addDays(d, 7)) {
    monthWeeks.push([0, 1, 2, 3, 4, 5, 6].map((i) => {
      const cd = addDays(d, i);
      return monthOf(cd) === s.tmonth ? { ...mkGroup(cd), dayNum: +cd.slice(8), inMonth: true } : { date: cd, dayNum: +cd.slice(8), inMonth: false, tasks: [], isToday: false };
    }));
  }
  return {
    weekDates, weekGroups, noDay, taskGroups, monthWeeks,
    monthEmpty: s.tscope === 'month' && monthListGroups.length === 0,
    visibleIds: taskGroups.reduce((a, g) => a.concat(g.tasks.map((t) => t.id)), [])
  };
}
