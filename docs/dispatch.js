const BASE_URL = 'https://pub-4591c8c5282040459ade2ed1e5e3d5be.r2.dev/dispatch';

const FALLBACK_DATA = [
    'DL27042026.pdf', 'DL23022026.pdf', 'DL20042026.pdf', 'DL16022026.pdf',
    'DL10032026.pdf', 'DL09022026.pdf', 'DL04052026.pdf', 'DL04042026.pdf',
    'DL27022026.pdf', 'DL07012026.pdf', 'DL22012026.pdf', 'DL30012026.pdf',
    'DL01062026.pdf', 'DL27052026.pdf', 'DL18052026.pdf',
    'DL03062020C.pdf', 'DL03062020D.pdf', 'DL11102021AD.pdf',
    'DL01112023.pdf', 'DL02042024.pdf', 'DL03062025.pdf', 'DL04052024.pdf',
    'DL05102019.pdf', 'DL07092019.pdf', 'DL10052019.pdf', 'DL16022019.pdf',
    'DL18042019.pdf', 'DL21022018.pdf', 'DL30032019.pdf', 'DL31012025.pdf'
];

function parseDate(name) {
    const m = name.match(/DL(\d{2})(\d{2})(\d{4})[A-Z]*\.pdf/i);
    if (!m) return null;
    return { d: m[1], mo: m[2], y: m[3], date: new Date(+m[3], +m[2]-1, +m[1]) };
}

const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

function fmt(f) {
    return `${f.d} ${months[+f.mo-1]} ${f.y}`;
}

function formatSize(bytes) {
    if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + 'MB';
    if (bytes >= 1024) return Math.round(bytes / 1024) + 'KB';
    return bytes + 'B';
}

let files = [];
let years = [];
let sizeMap = {};
let activeTab = null;
let query = '';

const $ = id => document.getElementById(id);
const loadingEl = $('loadingState');
const errorEl = $('errorState');
const emptyEl = $('emptyState');
const listEl = $('fileList');
const badgeEl = $('resultBadge');
const tabsEl = $('tabs');
const searchEl = $('searchInput');
const totalCountEl = $('totalCount');

function showLoading(show) { loadingEl.classList.toggle('hidden', !show); }
function showError(show) { errorEl.classList.toggle('hidden', !show); }

function buildFromRaw(raw) {
    sizeMap = {};
    raw.forEach(f => { sizeMap[f.name] = f.size; });

    files = raw
        .map(f => ({ name: f.name, p: parseDate(f.name) }))
        .filter(f => f.p)
        .sort((a, b) => b.p.date - a.p.date);

    years = [...new Set(files.map(f => f.p.y))].sort((a, b) => b - a);
    activeTab = years[0] || null;

    totalCountEl.textContent = `${files.length} file${files.length !== 1 ? 's' : ''}`;

    tabsEl.innerHTML = years.map(y => {
            const c = files.filter(f => f.p.y === y).length;
            return `<span class="tab${activeTab === y ? ' active' : ''}" data-year="${y}">${y} <span style="opacity:0.6;font-size:0.7rem;">${c}</span></span>`;
        }).join('');

    render();
}

function filter(year) {
    return files.filter(f => {
        if (year !== null && f.p.y !== year) return false;
        if (!query) return true;
        const q = query.toLowerCase();
        return f.name.toLowerCase().includes(q) || fmt(f.p).toLowerCase().includes(q);
    });
}

function render() {
    const filtered = filter(activeTab);

    if (filtered.length === 0) {
        listEl.innerHTML = '';
        emptyEl.classList.remove('hidden');
        badgeEl.classList.toggle('hidden', !query);
        badgeEl.textContent = query ? 'No matching files' : '';
        return;
    }
    emptyEl.classList.add('hidden');

    if (query) {
        badgeEl.classList.remove('hidden');
        badgeEl.textContent = `${filtered.length} of ${files.length} files`;
    } else {
        badgeEl.classList.add('hidden');
        badgeEl.textContent = '';
    }

    let html = '';
    if (activeTab === null) {
        for (const year of years) {
            const fy = filtered.filter(f => f.p.y === year);
            if (fy.length === 0) continue;
            html += `<div class="year-header">${year} — ${fy.length} file${fy.length !== 1 ? 's' : ''}</div>`;
            html += fy.map(f => card(f)).join('');
        }
    } else {
        html = filtered.map(f => card(f)).join('');
    }
    listEl.innerHTML = html;
}

function card(f) {
    return `<a href="${BASE_URL}/${f.name}" class="file-card" target="_blank" rel="noopener">
        <div class="file-card-icon"><img src="/pdf.png" alt="" width="16" height="16"></div>
        <div class="file-card-body">
            <div class="file-card-title">${fmt(f.p)}</div>
            <div class="file-card-meta">${sizeMap[f.name] ? formatSize(sizeMap[f.name]) : ''}</div>
        </div>
    </a>`;
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

async function loadData() {
    showLoading(true);
    showError(false);
    try {
        const resp = await fetch('/api/dispatch');
        if (!resp.ok) throw new Error('API unavailable');
        const data = await resp.json();
        showLoading(false);
        buildFromRaw(data);
    } catch {
        showLoading(false);
        const fallback = FALLBACK_DATA.map(n => ({ name: n, size: Math.round(50000 + Math.random() * 200000) }));
        buildFromRaw(fallback);
    }
}

loadData();

document.getElementById('year').textContent = new Date().getFullYear();
