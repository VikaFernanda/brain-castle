// Sample data copied from the design (Main.dc.html). Dates are relative to the current week,
// exactly like the design's wd(i) helper. Used by MockApi only. The real app starts empty.
import { iso, parseD, addDays, mondayOf, todayISO } from './lib/dates.js';
export { iso, parseD, addDays, mondayOf, todayISO };
const wd = (i) => addDays(mondayOf(todayISO()), i);

export const PAL = ['#FFC9D9', '#FFE9A0', '#C3D4FF', '#E0CCFF', '#BFEBDD', '#FFD3B8'];
export const PALN = ['Pink', 'Yellow', 'Blue', 'Purple', 'Mint', 'Peach'];

const C = (a) => a.map((x, i) => ({ ...x, created: i + 1 }));
const CT = (a) => a.map((x, i) => { const { day, ...r } = x; return { notes: '', time: '', tags: [], images: {}, done: false, archived: false, ...r, date: r.date !== undefined ? r.date : (day == null ? '' : wd(day)), created: i + 1 }; });

export function sampleData() {
  return {
    tags: [
      { id: 'g1', name: 'self-care', color: PAL[0] }, { id: 'g2', name: 'work', color: PAL[2] },
      { id: 'g3', name: 'home', color: PAL[4] }, { id: 'g4', name: 'ideas', color: PAL[1] },
      { id: 'g5', name: 'dreams', color: PAL[3] }
    ],
    tasks: CT([
      { id: 't1', title: 'Water the plants', day: 0, tags: ['g3'], done: true },
      { id: 't2', title: 'Reply to Mia', notes: 'Ask about Saturday brunch', day: 0, time: '10:00', tags: ['g2'] },
      { id: 't3', title: 'Grocery run', notes: 'Oat milk, berries, bread', day: 1, time: '17:30', tags: ['g3'] },
      { id: 't4', title: '30 minute stretch', day: 1, tags: ['g1'] },
      { id: 't5', title: 'Plan next week', day: 2, time: '09:00', tags: ['g2'] },
      { id: 't6', title: 'Call grandma', day: 2, time: '19:00', tags: ['g1'] },
      { id: 't7', title: 'Book the dentist', day: 3 },
      { id: 't8', title: 'Tidy the desk', day: 4, tags: ['g3'] },
      { id: 't9', title: 'Cozy movie night', notes: 'Pick something soft and funny', day: 5, tags: ['g1'] },
      { id: 't10', title: 'Learn a new recipe', day: null, tags: ['g4'] },
      { id: 't11', title: 'Return library books', day: 2, done: true, archived: true },
      { id: 't12', title: 'Renew bus pass', date: wd(-125) },
      { id: 't13', title: 'Plan birthday dinner', notes: 'Book a table for four', date: wd(9), tags: ['g1'] },
      { id: 't14', title: 'Send expense report', date: wd(-20), tags: ['g2'], done: true }
    ]),
    books: C([
      { id: 'b1', name: 'Daily Diary', color: PAL[1], date: '', archived: false },
      { id: 'b2', name: 'Dream Journal', color: PAL[3], date: '2026-11-01', archived: false },
      { id: 'b3', name: 'Idea Garden', color: PAL[4], date: '', archived: false },
      { id: 'b4', name: 'Book Club', color: PAL[0], date: '2026-10-20', archived: false }
    ]),
    notes: C([
      { id: 'n1', bookId: 'b1', title: 'A slow Sunday', body: 'Made pancakes, read by the window and finally cleaned the bookshelf. Felt calm all day.', date: '2026-11-15', tags: ['g1'], archived: false },
      { id: 'n2', bookId: 'b1', title: 'Small wins', body: 'Finished the sketch, answered every email and walked home in the rain.', date: '2026-11-12', tags: [], archived: false },
      { id: 'n3', bookId: 'b2', title: 'The floating library', body: 'I was in a library with no roof. Books drifted up like balloons and I had to catch them before they left.', date: '2026-11-09', tags: ['g5'], archived: false },
      { id: 'n4', bookId: 'b2', title: 'Purple ocean', body: 'The water was warm and the sky was lilac. A whale waved at me.', date: '', tags: ['g5'], archived: false },
      { id: 'n5', bookId: 'b3', title: 'Tiny desk garden', body: 'Try a row of herbs on the windowsill: basil, mint and chives.', date: '', tags: ['g4', 'g3'], archived: false },
      { id: 'n6', bookId: 'b4', title: 'Chapter 3 thoughts', body: 'I loved the quiet scenes more than the plot. Bring tea to the next meeting.', date: '2026-10-28', tags: [], archived: false },
      { id: 'n7', bookId: 'b1', title: 'Draft: October recap', body: 'Too long. Cut it down later.', date: '2026-10-31', tags: [], archived: true }
    ]).map((n) => ({ images: {}, ...n }))
  };
}
