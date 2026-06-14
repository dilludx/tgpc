<script lang="ts">
  import type { PharmacistRecord, Category, CategoryFilter } from '$lib/types';
  import { searchRecords } from '$lib/api';
  import { CATEGORY_COLORS, CATEGORY_BG, CATEGORIES as CAT_NAMES } from '$lib/colors';
  import jsPDF from 'jspdf';
  import autoTable from 'jspdf-autotable';
  import { fade, fly } from 'svelte/transition';

  let query = $state('');
  let category = $state<CategoryFilter>('all');
  let page = $state(1);
  let loading = $state(false);
  let results = $state<PharmacistRecord[]>([]);
  let searched = $state(false);

  const PER_PAGE = 50;
  const CATEGORY_FILTERS: CategoryFilter[] = ['all', ...CAT_NAMES];

  let filtered = $derived(category === 'all' ? results : results.filter(r => r.category === category));
  let totalPages = $derived(Math.max(1, Math.ceil(filtered.length / PER_PAGE)));
  let paginated = $derived(filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE));
  let start = $derived(filtered.length === 0 ? 0 : (page - 1) * PER_PAGE + 1);
  let end = $derived(Math.min(page * PER_PAGE, filtered.length));

  $effect(() => {
    if (query.trim() === '' && searched) {
      searched = false;
      results = [];
      category = 'all';
      page = 1;
    }
  });

  async function doSearch() {
    const q = query.trim();
    if (q.length < 3) return;
    loading = true;
    searched = true;
    page = 1;
    results = await searchRecords(query);
    loading = false;
  }

  function chipStyle(cat: CategoryFilter): string {
    if (cat !== category) return 'background:#f3f4f6;color:#6b7280';
    return 'background:#00cc66;color:#fff';
  }

  function reset() {
    query = '';
    category = 'all';
    page = 1;
    results = [];
    searched = false;
  }

  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

  function fmtDate(d: Date) {
    return `${DAYS[d.getDay()]}, ${String(d.getDate()).padStart(2,'0')} ${MONTHS[d.getMonth()]} ${d.getFullYear()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  }

  function fileDateStr(d: Date) {
    return `${String(d.getDate()).padStart(2,'0')}${String(d.getMonth()+1).padStart(2,'0')}${d.getFullYear()}`;
  }

  function exportPDF() {
    if (filtered.length === 0) return;
    const doc = new jsPDF({ format: 'a4', unit: 'mm' });
    const now = new Date();
    const kw = query.trim() || '(all)';
    const title = `TGPC Rx Registry - Search: ${kw} - ${fmtDate(now)}`;
    const body = filtered.map(r => [r.registration_number, r.name, r.father_name || '—', r.category.toUpperCase()]);
    autoTable(doc, {
      startY: 15,
      head: [['RPC NUMBER', 'NAME', 'FATHER NAME', 'CATEGORY']],
      body,
      theme: 'striped',
      headStyles: { fillColor: [0, 204, 102], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 9 },
      bodyStyles: { fontSize: 8, cellPadding: 2 },
      alternateRowStyles: { fillColor: [250, 250, 250] },
      margin: { top: 12, left: 10, right: 10, bottom: 12 },
      tableWidth: 'auto',
      didDrawPage: (data) => {
        doc.setFontSize(11);
        doc.setTextColor(0, 204, 102);
        doc.text(title, 10, 10);
      }
    });
    const total = doc.getNumberOfPages();
    for (let i = 1; i <= total; i++) {
      doc.setPage(i);
      doc.setFontSize(8);
      doc.setTextColor(150, 150, 150);
      doc.text(`Page ${i} / ${total}`, doc.internal.pageSize.width - 10, 10, { align: 'right' });
      doc.text(`Page ${i} / ${total}`, doc.internal.pageSize.width - 10, doc.internal.pageSize.height - 10, { align: 'right' });
    }
    doc.save(`TGPC-RX-SEARCH-${kw}-${fileDateStr(now)}.pdf`);
  }

  function exportCSV() {
    if (filtered.length === 0) return;
    const now = new Date();
    const kw = query.trim() || '(all)';
    const header = ['RPC NUMBER', 'NAME', 'FATHER NAME', 'CATEGORY'];
    const rows = filtered.map(r => [
      `"${r.registration_number}"`,
      `"${(r.name || '').replace(/"/g, '""')}"`,
      `"${(r.father_name || '').replace(/"/g, '""')}"`,
      `"${r.category.toUpperCase()}"`
    ]);
    const csv = [`# TGPC Rx Registry - Search: ${kw} - ${fmtDate(now)}`, header.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `TGPC-RX-SEARCH-${kw}-${fileDateStr(now)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }
</script>

<div class="space-y-4">
  <!-- Search + Chips row -->
  <div class="flex items-center gap-3">
    <div class="flex items-center min-w-0 border-b-2 border-[#e5e7eb] transition-colors focus-within:border-[#00cc66]"
         class:flex-1={!searched}
         class:max-w-[25vw]={searched}>
      <div class="relative min-w-0 min-h-[2.5rem] flex-1" style="display:{searched ? 'inline-grid' : 'grid'};grid-template-columns:1fr">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9ca3af] pointer-events-none z-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <span class="col-start-1 row-start-1 invisible whitespace-nowrap pl-9 {searched ? 'pr-36' : 'pr-16'} py-2.5 text-[0.95rem] max-sm:text-base min-w-0 overflow-hidden">{query || 'Search by Name or Registered Pharmacist Certificate (RPC) Number'}</span>
        <input
          type="text"
          bind:value={query}
          onkeydown={(e) => e.key === 'Enter' && doSearch()}
          placeholder="Search by Name or Registered Pharmacist Certificate (RPC) Number"
          aria-label="Search"
          class="col-start-1 row-start-1 w-full pl-9 {searched ? 'pr-36' : 'pr-16'} py-2.5 text-[0.95rem] bg-transparent outline-none max-sm:text-base"
        />
        {#if query.trim()}
          <div class="absolute right-0.5 top-1/2 -translate-y-1/2 z-10 flex items-center gap-1">
            <button onclick={doSearch} disabled={query.trim().length < 3}
              class="rounded cursor-pointer border-none transition-colors disabled:opacity-30 disabled:cursor-not-allowed {searched ? 'px-2.5 py-1 text-[0.65rem] font-medium' : 'px-3 py-1 text-[0.7rem] font-semibold'}"
              style="background:{query.trim().length >= 3 ? (searched ? '#f0fdf4' : '#00cc66') : '#f3f4f6'};color:{query.trim().length >= 3 ? (searched ? '#16a34a' : '#fff') : '#9ca3af'}"
              transition:fly={{ y: 4, duration: 120, opacity: 0 }}>
              SEARCH
            </button>
            {#if searched}
              <button onclick={reset}
                class="px-2.5 py-1 rounded text-[0.65rem] font-medium cursor-pointer border-none transition-colors uppercase"
                style="background:#fef2f2;color:#dc2626"
                transition:fly={{ y: 4, duration: 120, opacity: 0 }}>
                Clear
              </button>
            {/if}
          </div>
        {/if}
      </div>
    </div>

    {#if searched}
      <div class="flex items-center gap-1 min-w-0 flex-1" transition:fly={{ y: 6, duration: 200, opacity: 0 }}>
        <span class="text-[0.75rem] text-[#9ca3af] tabular-nums flex-shrink-0">{start}–{end} of {filtered.length}</span>
        <span class="ml-auto flex items-center gap-1.5">
          {#each CATEGORY_FILTERS as cat}
            <button onclick={() => { category = cat; page = 1; }}
              class="px-2.5 py-1 rounded text-[0.7rem] font-medium transition-all cursor-pointer border-none uppercase"
              style={chipStyle(cat)}>
              {cat === 'all' ? 'All' : cat}
            </button>
          {/each}
          <button onclick={exportCSV} class="flex items-center gap-1 px-2.5 py-1 rounded text-[0.65rem] font-medium cursor-pointer border-none transition-colors" style="background:#f0fdf4;color:#16a34a">EXPORT CSV</button>
          <button onclick={exportPDF} class="flex items-center gap-1 px-2.5 py-1 rounded text-[0.65rem] font-medium cursor-pointer border-none transition-colors" style="background:#fef2f2;color:#dc2626">EXPORT PDF</button>
        </span>
      </div>
    {/if}
  </div>

  <!-- Results -->
  {#if searched}
    <div transition:fly={{ y: 10, duration: 250, opacity: 0 }}>
    {#if loading}
      <div class="space-y-3 py-4">
        {#each Array(8) as _}
          <div class="h-4 bg-[#f3f4f6] rounded animate-pulse" style="width:{40 + Math.random() * 60}%"></div>
        {/each}
      </div>
    {:else if filtered.length === 0}
      <p class="text-[0.85rem] text-[#9ca3af] py-8 text-center">No results</p>
    {:else}
      {#if filtered.length > 0}
      <div class="hidden md:block">
        <div class="flex items-center gap-2 py-1.5 border-b-2 border-[#e5e7eb] text-[0.65rem] font-semibold text-[#9ca3af] uppercase tracking-wider">
          <span class="flex-1 min-w-0">RPC NUMBER</span>
          <span class="flex-1 min-w-0">Name</span>
          <span class="flex-1 min-w-0 hidden lg:block">Father Name</span>
          <span class="flex-1 min-w-0 text-right">Category</span>
        </div>
      </div>
      <div style="max-height:calc(100vh - 280px);overflow-y:auto">
        <!-- Desktop -->
        <div class="hidden md:block">
          {#each paginated as r}
            <div class="flex items-center gap-2 py-2.5 border-b border-[#f3f4f6] text-[0.875rem]">
              <span class="flex-1 min-w-0 font-semibold text-[#2563eb]">{r.registration_number}</span>
              <span class="flex-1 min-w-0">{r.name}</span>
              <span class="flex-1 min-w-0 text-[#6b7280] hidden lg:block">{r.father_name || '—'}</span>
              <span class="flex-1 min-w-0 flex justify-end">
                <span class="inline-flex items-center px-1.5 rounded-full text-[0.65rem] font-semibold leading-[18px] uppercase" style="background:{CATEGORY_BG[r.category]};color:{CATEGORY_COLORS[r.category]}">
                  {r.category}
                </span>
              </span>
            </div>
          {/each}
        </div>

        <!-- Mobile -->
        <div class="md:hidden space-y-0.5">
          {#each paginated as r}
            <div class="py-2.5 border-b border-[#f3f4f6]">
              <div class="flex items-center justify-between">
                <span class="font-semibold text-[#2563eb] text-[0.875rem]">{r.registration_number}</span>
                <span class="inline-flex items-center px-1.5 rounded-full text-[0.6rem] font-semibold leading-[18px] uppercase" style="background:{CATEGORY_BG[r.category]};color:{CATEGORY_COLORS[r.category]}">{r.category}</span>
              </div>
              <div class="text-[0.875rem] mt-0.5">{r.name}</div>
              <div class="text-[0.75rem] text-[#6b7280] mt-0.5">{r.father_name || '—'}</div>
            </div>
          {/each}
        </div>
      </div>

      <!-- Pagination -->
      {#if filtered.length > PER_PAGE}
        <div class="flex items-center justify-between pt-3 text-[0.8rem] text-[#6b7280]">
          <button onclick={() => { if (page > 1) page--; }} disabled={page <= 1}
            class="px-3 py-1 rounded text-[0.75rem] font-medium transition-all cursor-pointer border disabled:opacity-30 disabled:cursor-not-allowed bg-white"
            style="border-color:#e5e7eb;color:#111">← Prev</button>
          <span class="tabular-nums">{page} / {totalPages}</span>
          <button onclick={() => { if (page < totalPages) page++; }} disabled={page >= totalPages}
            class="px-3 py-1 rounded text-[0.75rem] font-medium transition-all cursor-pointer border disabled:opacity-30 disabled:cursor-not-allowed bg-white"
            style="border-color:#e5e7eb;color:#111">Next →</button>
        </div>
      {/if}
      {/if}
    {/if}
    </div>
  {/if}
</div>
