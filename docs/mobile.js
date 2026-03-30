const mobileConfig = window.TGPC_CONFIG || {};
let db;
let cat = 'all';

const MOBILE_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MOBILE_DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function fmt(n) {
    return n?.toLocaleString() || '—';
}

function esc(s) {
    return s ? s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') : '';
}

function hide() {
    document.getElementById('resultsSection').style.display = 'none';
}

function getDateText() {
    const now = new Date();
    const dayName = MOBILE_DAYS[now.getDay()];
    const day = now.getDate().toString().padStart(2, '0');
    const month = MOBILE_MONTHS[now.getMonth()];
    return `${dayName} ${day} ${month}`;
}

function getTimeText() {
    const now = new Date();
    const h = now.getHours().toString().padStart(2, '0');
    const m = now.getMinutes().toString().padStart(2, '0');
    const s = now.getSeconds().toString().padStart(2, '0');
    return `${h}:${m}:${s}`;
}

function startClock() {
    const el = document.getElementById('liveTime');
    if (!el) {
        return;
    }

    el.textContent = getTimeText();
    setInterval(() => {
        el.textContent = getTimeText();
    }, 1000);
}

function moveSlider(chip) {
    const slider = document.getElementById('filterSlider');
    const filters = document.querySelector('.filters');
    const chipRect = chip.getBoundingClientRect();
    const filtersRect = filters.getBoundingClientRect();

    slider.style.left = `${chipRect.left - filtersRect.left}px`;
    slider.style.width = `${chipRect.width}px`;
}

function sortRecords(data) {
    return [...data].sort((a, b) => {
        const parseReg = (reg) => {
            const match = reg.match(/^([A-Z]+)(\d+)$/);
            if (match) {
                return { prefix: match[1], num: parseInt(match[2], 10) };
            }
            return { prefix: reg, num: 0 };
        };

        const regA = parseReg(a.registration_number);
        const regB = parseReg(b.registration_number);

        if (regA.prefix !== regB.prefix) {
            return regA.prefix.localeCompare(regB.prefix);
        }

        return regA.num - regB.num;
    });
}

async function loadStatusAndStats() {
    if (!db) {
        document.getElementById('statusText').textContent = 'Offline';
        return;
    }

    try {
        await db.from('rx').select('id').limit(1);
        const statusEl = document.getElementById('status');
        statusEl.classList.add('live');
        statusEl.innerHTML = `<span class="dot"></span><span>Live</span><span class="sep">|</span><span class="date">${getDateText()} <span id="liveTime"></span></span>`;
        startClock();
    } catch (error) {
        document.getElementById('statusText').textContent = 'Offline';
    }

    try {
        const { data } = await db.rpc('get_rx_stats');
        if (data) {
            document.getElementById('total').textContent = fmt(data.total);
            if (data.categories) {
                for (const [key, value] of Object.entries(data.categories)) {
                    const el = document.getElementById(key.toLowerCase());
                    if (el) {
                        el.textContent = fmt(value);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Mobile analytics error:', error);
    }
}

async function search() {
    const q = document.getElementById('q').value.trim();
    if (q.length < 2 || !db) {
        hide();
        return;
    }

    document.getElementById('loading').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';

    try {
        let query = db.from('rx')
            .select('registration_number,name,father_name,category')
            .or(`registration_number.ilike.%${q}%,name.ilike.%${q}%,father_name.ilike.%${q}%`);

        if (cat !== 'all') {
            query = query.eq('category', cat);
        }

        const { data } = await query.limit(100000);
        render(sortRecords(data || []));
    } catch (error) {
        console.error('Mobile search error:', error);
        document.getElementById('list').innerHTML = '<div class="empty">Error searching</div>';
    }

    document.getElementById('loading').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
}

function render(data) {
    document.getElementById('count').textContent = data.length;
    const list = document.getElementById('list');

    if (data.length === 0) {
        list.innerHTML = '<div class="empty">No results</div>';
        return;
    }

    list.innerHTML = data.map(r => `
        <div class="card">
            <div class="card-row">
                <span class="reg">${esc(r.registration_number)}</span>
                <span class="tag ${esc(r.category).toLowerCase()}">${esc(r.category)}</span>
            </div>
            <div class="name">${esc(r.name)}</div>
            ${r.father_name ? `<div class="father">FATHER NAME: ${esc(r.father_name)}</div>` : ''}
        </div>
    `).join('');
}

function resetSearch() {
    document.getElementById('q').value = '';
    hide();
    document.querySelectorAll('.chip').forEach(chip => chip.classList.remove('active'));
    const allChip = document.querySelector('.chip[data-v="all"]');
    allChip.classList.add('active');
    moveSlider(allChip);
    cat = 'all';
}

document.addEventListener('DOMContentLoaded', () => {
    if (window.supabase?.createClient && mobileConfig.SUPABASE_URL && mobileConfig.SUPABASE_ANON_KEY) {
        db = window.supabase.createClient(mobileConfig.SUPABASE_URL, mobileConfig.SUPABASE_ANON_KEY);
    }

    document.getElementById('mobileResetButton').addEventListener('click', resetSearch);
    document.getElementById('mobileSearchButton').addEventListener('click', search);
    document.getElementById('q').addEventListener('keypress', event => {
        if (event.key === 'Enter') {
            search();
        }
    });

    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const hasSearch = document.getElementById('q').value.length >= 2;
            cat = chip.dataset.v;

            if (hasSearch) {
                document.querySelectorAll('.chip').forEach(item => item.classList.remove('active'));
                chip.classList.add('active');
                moveSlider(chip);
                search();
            }
        });
    });

    setTimeout(() => {
        const activeChip = document.querySelector('.chip.active');
        if (activeChip) {
            moveSlider(activeChip);
        }
    }, 100);

    loadStatusAndStats();
});
