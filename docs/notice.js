const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function fmtDate(dateStr) {
    const d = new Date(dateStr + 'T00:00:00');
    const day = d.getDate().toString().padStart(2, '0');
    const mon = MONTHS[d.getMonth()];
    const yr = d.getFullYear();
    return `${day} ${mon} ${yr}`;
}

function getYear(dateStr) {
    return dateStr.slice(0, 4);
}

function ext(url) {
    const m = url.match(/\.([a-z0-9]+)(?:\?.*)?$/i);
    return m ? m[1].toLowerCase() : 'link';
}

function linkClass(url) {
    const e = ext(url);
    if (e === 'pdf') return 'pdf';
    if (['jpg','jpeg','png','gif','webp'].includes(e)) return 'image';
    return 'ext';
}

function esc(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

let notices = [];
let years = [];
let activeTab = null;
let query = '';

const $ = id => document.getElementById(id);
const tabsEl = $('tabs');
const tbody = $('tableBody');
const emptyEl = $('emptyState');
const loadingEl = $('loadingState');
const searchEl = $('searchInput');
const badgeEl = $('resultBadge');
const totalCountEl = $('totalCount');

function filter() {
    return notices.filter(n => {
        if (activeTab && getYear(n.date) !== activeTab) return false;
        if (!query) return true;
        const q = query.toLowerCase();
        return n.title.toLowerCase().includes(q) ||
               fmtDate(n.date).toLowerCase().includes(q);
    });
}

function render() {
    const filtered = filter();

    if (filtered.length === 0) {
        tbody.innerHTML = '';
        emptyEl.classList.remove('hidden');
        badgeEl.classList.toggle('hidden', !query);
        badgeEl.textContent = query ? 'No matching notices' : '';
        return;
    }
    emptyEl.classList.add('hidden');

    if (query) {
        badgeEl.classList.remove('hidden');
        badgeEl.textContent = `${filtered.length} of ${notices.length} notices`;
    } else {
        badgeEl.classList.add('hidden');
    }

    const year = activeTab;
    if (!year) {
        let html = '';
        for (const y of years) {
            const fy = filtered.filter(n => getYear(n.date) === y);
            if (fy.length === 0) continue;
            html += `<tr style="background:#f9fafb;font-weight:600;color:var(--text-muted);font-size:0.75rem;text-transform:uppercase;letter-spacing:0.5px;"><td colspan="3" style="padding:0.75rem 1rem;border-bottom:2px solid var(--border);">${y} &mdash; ${fy.length} notice${fy.length !== 1 ? 's' : ''}</td></tr>`;
            html += fy.map(r => row(r)).join('');
        }
        tbody.innerHTML = html;
    } else {
        tbody.innerHTML = filtered.map(r => row(r)).join('');
    }
}

function row(n) {
    const date = fmtDate(n.date);
    const links = (n.links || []).map(l => {
        const cls = linkClass(l.url);
        const label = esc(l.label);
        const url = l.url.startsWith('http') ? esc(l.url) : `https://pub-4591c8c5282040459ade2ed1e5e3d5be.r2.dev/notice${esc(l.url)}`;
        return `<a href="${url}" class="link-badge ${cls}" target="_blank" rel="noopener">${label}</a>`;
    }).join(' ');

    return `<tr>
        <td class="date-cell" data-label="Date">${esc(date)}</td>
        <td class="title-cell" data-label="Title">${esc(n.title)}</td>
        <td class="links-cell" data-label="Links">${links || '&mdash;'}</td>
    </tr>`;
}

searchEl.addEventListener('input', e => {
    query = e.target.value;
    render();
});

tabsEl.addEventListener('click', e => {
    const tab = e.target.closest('.tab');
    if (!tab) return;
    tabsEl.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    activeTab = tab.dataset.year;
    render();
});

async function load() {
    loadingEl.classList.remove('hidden');
    try {
        const resp = await fetch('/api/notice');
        if (!resp.ok) throw new Error('Failed to load notices');
        const data = await resp.json();

        data.sort((a, b) => b.date.localeCompare(a.date));
        notices = data;
        years = [...new Set(notices.map(n => getYear(n.date)))].sort((a, b) => b - a);
        activeTab = years[0] || null;

        totalCountEl.textContent = `${notices.length} notice${notices.length !== 1 ? 's' : ''}`;

        tabsEl.innerHTML = years.map(y => {
            const c = notices.filter(n => getYear(n.date) === y).length;
            return `<span class="tab${activeTab === y ? ' active' : ''}" data-year="${y}">${y} <span style="opacity:0.6;font-size:0.7rem;">${c}</span></span>`;
        }).join('');

        render();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align:center;padding:3rem 1rem;color:var(--text-muted);">Failed to load notices.</td></tr>`;
    }
    loadingEl.classList.add('hidden');
}

load();
$('year').textContent = new Date().getFullYear();
