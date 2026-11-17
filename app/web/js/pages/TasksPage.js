// Tasks area: header, period row, tag bar, list view and calendar board. Markup copied from the design.
import { Fragment } from 'preact';
import { html } from '../html.js';
import { Icon } from '../components/Icon.js';
import { Button } from '../components/Button.js';
import { IconButton } from '../components/IconButton.js';
import { Segmented } from '../components/Segmented.js';
import { Chip } from '../components/Chip.js';
import { SHORT, mondayOf, todayISO, monthName, rangeLabel, fmt, fmtTime } from '../lib/dates.js';
import { plain, imgIds } from '../lib/text.js';
import { buildTasksView, SORT_OPTIONS } from '../tasks/view.js';

const SEL_ON = 'background:var(--strong);border-color:var(--strong)';
const SEL_OFF = 'background:var(--surface);border-color:var(--muted)';
const DONE_ON = 'background:var(--accent);border-color:var(--strong)';
const DONE_OFF = 'background:var(--surface);border-color:var(--muted)';
const CHECK = '<path d="M5 12.5l4.5 4.5L19 7.5"></path>';

const Check = ({ size, opacity }) => html`<svg class="i" viewBox="0 0 24 24" aria-hidden="true" style=${'width:' + size + 'px;height:' + size + 'px;opacity:' + opacity} dangerouslySetInnerHTML=${{ __html: CHECK }}></svg>`;

// Pieces shared by every task card.
function useTask(t, s, A) {
  const tagOf = (id) => s.tags.find((g) => g.id === id);
  const imgs = imgIds(t.notes).length;
  const insert = s.overKey === 'c' + t.id && s.dragId && s.dragId !== t.id ? 'box-shadow:0 -5px 0 0 var(--strong),0 3px 0 var(--line);' : '';
  return {
    notes: plain(t.notes),
    imgLabel: imgs + (imgs === 1 ? ' image' : ' images'), hasImg: imgs > 0,
    chips: (t.tags || []).map(tagOf).filter(Boolean),
    cardStyle: (s.sel[t.id] ? 'outline:3px solid var(--strong);' : '') + (s.dragId === t.id ? 'opacity:.45;' : '') + insert,
    selOn: s.selMode,
    drag: { draggable: 'true', onDragStart: A.dragStart(t.id), onDragEnd: A.dragEnd, onDragOver: A.over('c' + t.id), onDragLeave: A.leave('c' + t.id), onDrop: A.dropOnTask(t) },
    tickStyle: t.done ? DONE_ON : DONE_OFF,
    titleStyle: t.done ? 'text-decoration:line-through;opacity:.6' : ''
  };
}

const TimeChip = ({ t }) => html`<span class="chip" style="background:var(--accent2-soft);align-self:flex-start;gap:4px"><${Icon} name="clock" size=${12} />${fmtTime(t.time)}</span>`;
const ImgChip = ({ label }) => html`<span class="chip" style="background:var(--accent-soft);align-self:flex-start;gap:4px"><${Icon} name="image" size=${12} />${label}</span>`;
const Tick = ({ t, v, A, style }) => html`<button type="button" class="tick" aria-label="Mark done" aria-pressed=${!!t.done} onClick=${() => A.toggleDone(t)} style=${(style || '') + v.tickStyle}><${Check} size=${style && style.includes('22') ? 12 : 14} opacity=${t.done ? 1 : 0} /></button>`;
const Sq = ({ t, s, A, style, size = 14 }) => html`<button type="button" class="sq" aria-label="Select task" aria-pressed=${!!s.sel[t.id]} onClick=${() => A.toggleSel(t.id)} style=${(style || '') + (s.sel[t.id] ? SEL_ON : SEL_OFF)}><${Check} size=${size} opacity=${s.sel[t.id] ? 1 : 0} /></button>`;
const TagChips = ({ list }) => list.map((g) => html`<${Chip} key=${g.id} bg=${g.color}>${g.name}<//>`);

function Actions({ t, A, small }) {
  const st = small ? 32 : undefined;
  return html`<div class="acts">
    <${IconButton} icon="edit" label="Edit task" size=${st} onClick=${() => A.openTask(t.id)} />
    <${IconButton} icon="archive" label="Archive task" size=${st} onClick=${() => A.archive(t.id)} />
    <${IconButton} icon="trash" label="Delete task" size=${st} onClick=${() => A.askDelete(t.id)} />
  </div>`;
}

// ---- list view row ----
function ListRow({ t, s, A }) {
  const v = useTask(t, s, A);
  return html`<div class="card" ...${v.drag} style=${'display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:8px 10px 8px 14px;cursor:grab;' + v.cardStyle}>
    ${v.selOn ? html`<${Sq} t=${t} s=${s} A=${A} />` : null}
    <${Tick} t=${t} v=${v} A=${A} />
    <div style="flex:1 1 200px;min-width:0;display:flex;flex-direction:column;gap:2px">
      <button type="button" class="link" onClick=${() => A.openTask(t.id)} style=${v.titleStyle}>${t.title}</button>
      ${v.notes ? html`<span style="font-size:13px;color:var(--muted)">${v.notes}</span>` : null}
      ${t.time ? html`<${TimeChip} t=${t} />` : null}
      ${v.hasImg ? html`<${ImgChip} label=${v.imgLabel} />` : null}
    </div>
    ${v.chips.length ? html`<div style="display:flex;flex-wrap:wrap;gap:6px"><${TagChips} list=${v.chips} /></div>` : null}
    <${Actions} t=${t} A=${A} />
  </div>`;
}

function ListGroup({ g, s, A }) {
  const over = s.overKey === g.key;
  return html`<section class="card" aria-label=${g.label} onDragOver=${A.over(g.key)} onDragLeave=${A.leave(g.key)} onDrop=${A.dropOnDay(g.date)} style=${'padding:16px 18px;display:flex;flex-direction:column;gap:12px;' + (over ? 'border:2px dashed var(--strong);background:var(--accent2-soft)' : '')}>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px">
      <h2 style="font-size:22px">${g.label}</h2>
      ${g.isToday ? html`<${Chip} bg="var(--accent2)">Today<//>` : null}
      <span style="color:var(--muted);font-weight:600;font-size:14px">${g.dateLabel}</span>
      <span style="flex:1"></span>
      ${g.progress ? html`<span style="color:var(--muted);font-size:13px;font-weight:700">${g.progress}</span>` : null}
      <${Button} onClick=${() => A.openTask(null, g.date)} style="min-height:36px;padding:0 14px;font-size:14px"><${Icon} name="plus" size=${16} />Add<//>
    </div>
    ${g.tasks.map((t) => html`<${ListRow} key=${t.id} t=${t} s=${s} A=${A} />`)}
    ${g.tasks.length === 0 ? html`<div style="border:2px dashed var(--line);border-radius:14px;padding:14px;text-align:center;color:var(--muted);font-weight:600;font-size:14px">${g.emptyText}</div>` : null}
  </section>`;
}

// ---- board cards (week columns and "No date yet") ----
function BoardCard({ t, s, A }) {
  const v = useTask(t, s, A);
  return html`<div class="card" ...${v.drag} style=${'padding:10px 10px 8px 12px;display:flex;flex-direction:column;gap:8px;cursor:grab;' + v.cardStyle}>
    <div style="display:flex;align-items:flex-start;gap:8px">
      <${Tick} t=${t} v=${v} A=${A} style="margin-top:1px;" />
      <button type="button" class="link" onClick=${() => A.openTask(t.id)} style=${'flex:1;min-width:0;font-size:15px;' + v.titleStyle}>${t.title}</button>
      ${v.selOn ? html`<${Sq} t=${t} s=${s} A=${A} />` : null}
    </div>
    ${v.notes ? html`<span style="font-size:13px;color:var(--muted)">${v.notes}</span>` : null}
    ${t.time ? html`<${TimeChip} t=${t} />` : null}
    ${v.hasImg ? html`<${ImgChip} label=${v.imgLabel} />` : null}
    <div style="display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:4px 6px">
      <div style="flex:1 1 auto;display:flex;flex-wrap:wrap;gap:4px"><${TagChips} list=${v.chips} /></div>
      <${Actions} t=${t} A=${A} small=${true} />
    </div>
  </div>`;
}

function DayColumn({ g, s, A }) {
  const over = s.overKey === g.key;
  return html`<section aria-label=${g.label} onDragOver=${A.over(g.key)} onDragLeave=${A.leave(g.key)} onDrop=${A.dropOnDay(g.date)} style=${'background:var(--side);border:2px solid transparent;border-radius:20px;padding:12px 10px;display:flex;flex-direction:column;gap:10px;min-height:320px;' + (over ? 'border:2px dashed var(--strong);background:var(--accent2-soft)' : '')}>
    <div style="display:flex;align-items:center;gap:8px;padding:0 4px">
      <div style="flex:1;min-width:0">
        <h2 style="font-size:18px">${g.short}</h2>
        <div style="font-size:13px;color:var(--muted);font-weight:700">${g.dateLabel}</div>
      </div>
      ${g.isToday ? html`<${Chip} bg="var(--accent2)">Today<//>` : null}
      <${IconButton} icon="plus" label="Add task" onClick=${() => A.openTask(null, g.date)} style="background:var(--surface)" />
    </div>
    ${g.tasks.map((t) => html`<${BoardCard} key=${t.id} t=${t} s=${s} A=${A} />`)}
    ${g.tasks.length === 0 ? html`<div style="border:2px dashed var(--accent);border-radius:14px;padding:18px 10px;text-align:center;color:var(--muted);font-weight:600;font-size:13px">Drop a task here</div>` : null}
  </section>`;
}

// ---- month grid ----
function MonthCard({ t, s, A }) {
  const v = useTask(t, s, A);
  return html`<div class="card" ...${v.drag} style=${'padding:6px 8px;display:flex;align-items:center;gap:6px;cursor:grab;border-radius:12px;' + v.cardStyle}>
    <${Tick} t=${t} v=${v} A=${A} style="width:22px;height:22px;" />
    <button type="button" class="link" onClick=${() => A.openTask(t.id)} style=${'flex:1;min-width:0;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;' + v.titleStyle}>${t.title}</button>
    ${t.time ? html`<span style="font-size:11px;font-weight:700;color:var(--muted);flex:none">${fmtTime(t.time)}</span>` : null}
    ${v.hasImg ? html`<${ImgChip} label=${v.imgLabel} />` : null}
    ${v.selOn ? html`<${Sq} t=${t} s=${s} A=${A} size=${12} style="width:20px;height:20px;" />` : null}
  </div>`;
}

function MonthCell({ g, s, A }) {
  if (!g.inMonth) {
    return html`<section style="min-height:132px;min-width:0;border-radius:16px;border:2px solid transparent;padding:8px;display:flex;flex-direction:column;gap:6px;background:transparent;opacity:.45;">
      <div style="display:flex;align-items:center;gap:6px"><span style="font-family:Fredoka,system-ui,sans-serif;font-weight:600;font-size:18px;flex:1">${g.dayNum}</span></div>
    </section>`;
  }
  const over = s.overKey === g.key;
  return html`<section aria-label=${g.label} onDragOver=${A.over(g.key)} onDragLeave=${A.leave(g.key)} onDrop=${A.dropOnDay(g.date)} style=${'min-height:132px;min-width:0;border-radius:16px;border:2px solid transparent;padding:8px;display:flex;flex-direction:column;gap:6px;background:var(--side);' + (over ? 'border:2px dashed var(--strong);background:var(--accent2-soft)' : '')}>
    <div style="display:flex;align-items:center;gap:6px">
      <span style="font-family:Fredoka,system-ui,sans-serif;font-weight:600;font-size:18px;flex:1">${g.dayNum}</span>
      ${g.isToday ? html`<${Chip} bg="var(--accent2)">Today<//>` : null}
      <${IconButton} icon="plus" label="Add task on this day" size=${32} onClick=${() => A.openTask(null, g.date)} style="background:var(--surface)" />
    </div>
    ${g.tasks.map((t) => html`<${MonthCard} key=${t.id} t=${t} s=${s} A=${A} />`)}
  </section>`;
}

function NoDate({ g, s, A }) {
  const over = s.overKey === g.key;
  return html`<section aria-label="No date yet" onDragOver=${A.over(g.key)} onDragLeave=${A.leave(g.key)} onDrop=${A.dropOnDay('')} style=${'background:var(--accent2-soft);border:2px solid transparent;border-radius:20px;padding:14px 16px;display:flex;flex-direction:column;gap:10px;' + (over ? 'border:2px dashed var(--strong);background:var(--accent2-soft)' : '')}>
    <div style="display:flex;align-items:center;gap:12px">
      <h2 style="font-size:18px">No date yet</h2>
      <span style="color:var(--muted);font-size:13px;font-weight:700;flex:1">Parking lot for tasks you have not planned</span>
      <${Button} onClick=${() => A.openTask(null, '')} style="min-height:36px;padding:0 14px;font-size:14px;background:var(--surface)"><${Icon} name="plus" size=${16} />Add<//>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px">
      ${g.tasks.map((t) => html`<${BoardCard} key=${t.id} t=${t} s=${s} A=${A} />`)}
    </div>
    ${g.tasks.length === 0 ? html`<div style="color:var(--muted);font-weight:600;font-size:13px">Nothing parked here. Drop a task to unplan it.</div>` : null}
  </section>`;
}

function Board({ s, A, view }) {
  return html`<div style="display:flex;flex-direction:column;gap:16px">
    ${s.tscope === 'week' ? html`<div style="overflow-x:auto;padding-bottom:8px">
      <div class="board" style="display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:12px;min-width:1120px;align-items:start">
        ${view.weekGroups.map((g) => html`<${DayColumn} key=${g.key} g=${g} s=${s} A=${A} />`)}
      </div>
    </div>` : html`<div style="overflow-x:auto;padding-bottom:8px">
      <div style="min-width:1040px;display:flex;flex-direction:column;gap:10px">
        <div style="display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:10px">
          ${SHORT.map((n) => html`<div key=${n} style="text-align:center;font-weight:800;color:var(--muted);font-size:14px">${n}</div>`)}
        </div>
        ${view.monthWeeks.map((w, i) => html`<div key=${i} style="display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:10px">
          ${w.map((g) => html`<${MonthCell} key=${g.date} g=${g} s=${s} A=${A} />`)}
        </div>`)}
      </div>
    </div>`}
    <${NoDate} g=${view.noDay} s=${s} A=${A} />
  </div>`;
}

export function TasksPage({ s, A }) {
  const view = buildTasksView(s);
  const today = todayISO();
  const title = s.tscope === 'week' ? (s.tweek === mondayOf(today) ? 'This week' : 'Week of ' + fmt(s.tweek)) : monthName(s.tmonth);
  const sub = s.tscope === 'week' ? rangeLabel(s.tweek) : (s.tstat === 'done' ? 'Finished tasks' : s.tstat === 'todo' ? 'Tasks still to do' : 'All tasks this month');
  const label = s.tscope === 'week' ? rangeLabel(s.tweek) : monthName(s.tmonth);
  return html`<${Fragment}>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:12px 16px">
      <div style="flex:1 1 240px">
        <h1 style="font-size:34px">${title}</h1>
        <div style="color:var(--muted);font-weight:600">${sub}</div>
      </div>
      <${Segmented} label="Tasks view" value=${s.tview} onChange=${A.setView} options=${[{ value: 'list', label: 'List', icon: 'list' }, { value: 'board', label: 'Calendar board', icon: 'calendarBoard' }]} />
      <label class="mini">Sort
        <select class="field" aria-label="Sort tasks within each day" value=${s.tsort} onChange=${(e) => A.setSort(e.target.value)}>
          ${SORT_OPTIONS.map((o) => html`<option key=${o.value} value=${o.value}>${o.label}</option>`)}
        </select>
      </label>
      <${Button} aria-pressed=${s.selMode} onClick=${A.toggleSelMode} style=${s.selMode ? 'background:var(--accent2)' : ''}>${s.selMode ? 'Done selecting' : 'Select'}<//>
      <${Button} variant="primary" icon="plus" onClick=${() => A.openTask(null)}>New task<//>
    </div>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px">
      <${Segmented} label="Period" value=${s.tscope} onChange=${A.setScope} options=${[{ value: 'week', label: 'Week' }, { value: 'month', label: 'Month' }]} />
      <div style="display:inline-flex;align-items:center;gap:2px">
        <${IconButton} icon="chevronLeft" label="Previous" onClick=${() => A.step(-1)} />
        <span style="min-width:150px;text-align:center;font-weight:800">${label}</span>
        <${IconButton} icon="chevronRight" label="Next" onClick=${() => A.step(1)} />
      </div>
      <${Button} onClick=${A.today} style="min-height:40px">Today<//>
      <${Segmented} tone="soft2" label="Show tasks" value=${s.tstat} onChange=${A.setStat} options=${[{ value: 'all', label: 'All' }, { value: 'todo', label: 'To do' }, { value: 'done', label: 'Done' }]} />
    </div>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px">
      <${Icon} name="tag" style="color:var(--muted)" />
      <button type="button" class="tagbtn" aria-pressed=${!s.tagF} onClick=${() => A.setTag(null)} style=${'background:var(--accent-soft);' + (!s.tagF ? 'outline:3px solid var(--strong);outline-offset:1px' : '')}>All</button>
      ${s.tags.map((g) => html`<button type="button" key=${g.id} class="tagbtn" aria-pressed=${s.tagF === g.id} onClick=${() => A.setTag(s.tagF === g.id ? null : g.id)} style=${'background:' + g.color + ';' + (s.tagF === g.id ? 'outline:3px solid var(--strong);outline-offset:1px' : '')}>${g.name}</button>`)}
      <button type="button" class="tagbtn" onClick=${A.openTags} style="background:transparent;border:1.5px dashed var(--muted);color:var(--ink)">Manage tags</button>
    </div>
    ${s.tview === 'list' ? html`<div style="display:flex;flex-direction:column;gap:16px">
      ${view.taskGroups.map((g) => html`<${ListGroup} key=${g.key} g=${g} s=${s} A=${A} />`)}
      ${view.monthEmpty ? html`<div class="card" style="padding:24px;text-align:center;color:var(--muted);font-weight:700">No tasks match in this month.</div>` : null}
    </div>` : html`<${Board} s=${s} A=${A} view=${view} />`}
  </${Fragment}>`;
}

export { buildTasksView };
