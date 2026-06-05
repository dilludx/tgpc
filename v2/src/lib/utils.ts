const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export function fmtDate(date: Date): string {
  const day = date.getDate().toString().padStart(2, '0');
  return `${DAYS[date.getDay()]} ${day} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`;
}

export function fmtTime(date: Date): string {
  return date.toTimeString().slice(0, 8);
}

export function fmtNumber(n: number | null | undefined): string {
  return n?.toLocaleString() || '—';
}

export function escapeHtml(s: string): string {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
