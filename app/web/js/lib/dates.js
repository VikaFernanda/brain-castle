// Date helpers copied from the design. Dates are "YYYY-MM-DD" strings, never Date objects in state.
export const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
export const SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
export const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

export const iso = (d) => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
export const parseD = (s) => { const p = s.split('-').map(Number); return new Date(p[0], p[1] - 1, p[2]); };
export const addDays = (s, n) => { const d = parseD(s); d.setDate(d.getDate() + n); return iso(d); };
export const mondayOf = (s) => addDays(s, -((parseD(s).getDay() + 6) % 7));
export const todayISO = () => iso(new Date());
export const monthOf = (s) => s.slice(0, 7);
export const addMonths = (ym, n) => { const p = ym.split('-').map(Number); return iso(new Date(p[0], p[1] - 1 + n, 1)).slice(0, 7); };
export const monthName = (ym) => MONTHS[+ym.slice(5, 7) - 1] + ' ' + ym.slice(0, 4);
export const rangeLabel = (mon) => { const a = parseD(mon); const b = parseD(addDays(mon, 6)); return MON[a.getMonth()] + ' ' + a.getDate() + ' to ' + MON[b.getMonth()] + ' ' + b.getDate(); };
export const weekdayIdx = (d) => (parseD(d).getDay() + 6) % 7;
export const fmt = (s) => { if (!s) return ''; const p = s.split('-'); return MON[+p[1] - 1] + ' ' + (+p[2]); };
export const fmtTime = (t) => { if (!t) return ''; const p = t.split(':').map(Number); return ((p[0] % 12) || 12) + ':' + String(p[1]).padStart(2, '0') + (p[0] >= 12 ? ' PM' : ' AM'); };
