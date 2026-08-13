<script lang="ts">
  import type { PharmacistRecord, Category, CategoryFilter } from '$lib/types';
  import { searchRecords, suggestNames } from '$lib/api';
  import { CATEGORY_COLORS, CATEGORY_BG, CATEGORIES as CAT_NAMES } from '$lib/colors';
  import { PUBLIC_R2_PHOTO_BASE } from '$env/static/public';
  import jsPDF from 'jspdf';
  import autoTable from 'jspdf-autotable';
  import { fade, fly } from 'svelte/transition';

  function photoUrl(r: PharmacistRecord): string {
    return r.photo_url || `${PUBLIC_R2_PHOTO_BASE}/${r.registration_number}.webp`;
  }

  let query = $state('');
  let category = $state<CategoryFilter>('all');
  let loading = $state(false);
  let results = $state<PharmacistRecord[]>([]);
  let searched = $state(false);

  let suggestions = $state<PharmacistRecord[]>([]);
  let showSug = $state(false);
  let sugIndex = $state(-1);
  let sugTimer: ReturnType<typeof setTimeout> | undefined;

  const CATEGORY_FILTERS: CategoryFilter[] = ['all', ...CAT_NAMES];

  let filtered = $derived(category === 'all' ? results : results.filter(r => r.category === category));

  $effect(() => {
    if (query.trim() === '' && searched) {
      searched = false;
      results = [];
      category = 'all';
    }
  });

  async function doSearch() {
    const q = query.trim();
    if (q.length < 3) return;
    loading = true;
    searched = true;
    results = await searchRecords(query);
    loading = false;
    suggestions = [];
    showSug = false;
    sugIndex = -1;
  }

  function onInputChange() {
    clearTimeout(sugTimer);
    suggestions = [];
    sugIndex = -1;
    const q = query.trim();
    if (q.length < 2) {
      showSug = false;
      return;
    }
    showSug = true;
    sugTimer = setTimeout(async () => {
      const s = await suggestNames(q);
      if (s.length === 0) { showSug = false; return; }
      suggestions = s;
      sugIndex = -1;
    }, 150);
  }

  function selectSuggestion(r: PharmacistRecord) {
    query = r.name;
    showSug = false;
    suggestions = [];
    if (query.trim().length >= 3) doSearch();
  }

  function onSearchKeydown(e: KeyboardEvent) {
    if (suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        sugIndex = (sugIndex + 1) % suggestions.length;
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        sugIndex = sugIndex <= 0 ? suggestions.length - 1 : sugIndex - 1;
        return;
      }
      if (e.key === 'Enter' && sugIndex >= 0) {
        e.preventDefault();
        selectSuggestion(suggestions[sugIndex]);
        return;
      }
      if (e.key === 'Escape') {
        showSug = false;
        suggestions = [];
        sugIndex = -1;
        return;
      }
    }
    if (e.key === 'Enter') doSearch();
  }

  function chipStyle(cat: CategoryFilter): string {
    if (cat !== category) return 'background:#f3f4f6;color:#6b7280';
    return 'background:#00cc66;color:#fff';
  }

  function reset() {
    query = '';
    category = 'all';
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
    const title = `TGPC RPh Registry - Search: ${kw} - ${fmtDate(now)}`;
    const body = filtered.map(r => [r.registration_number, r.name, r.father_name || '—', r.gender || '—', r.category, r.validity_date || '—', r.status || '—']);

    const TEXTS: Record<string, number[]> = {
      BPharm: [0, 204, 102], DPharm: [239, 68, 68], MPharm: [124, 58, 237],
      PharmD: [245, 158, 11], QC: [8, 145, 178], QP: [120, 113, 108]
    };

    autoTable(doc, {
      startY: 15,
      head: [['RPC NUMBER', 'NAME', 'FATHER NAME', 'GENDER', 'CATEGORY', 'VALID TILL', 'STATUS']],
      body,
      theme: 'striped',
      headStyles: { fillColor: [0, 204, 102], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 9 },
      bodyStyles: { fontSize: 8, cellPadding: 2 },
      alternateRowStyles: { fillColor: [247, 247, 247] },
      margin: { top: 12, left: 10, right: 10, bottom: 12 },
      tableWidth: 'auto',
      didParseCell: (data) => {
        if (data.section === 'body' && data.row.raw) {
          const cat = (data.row.raw as string[])[4];
          const text = TEXTS[cat];
          if (text) data.cell.styles.textColor = text as [number, number, number];
        }
      },
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
      const ph = doc.internal.pageSize.height;
      doc.text('TGPC RPh Registry - Open-Source Pharmacist Data', 10, ph - 10);
      doc.text('tgpc.pages.dev', doc.internal.pageSize.width / 2, ph - 10, { align: 'center' });
      doc.text(`Page ${i} / ${total}`, doc.internal.pageSize.width - 10, ph - 10, { align: 'right' });
    }
    doc.save(`TGPC-RPH-SEARCH-${kw}-${fileDateStr(now)}.pdf`);
  }

  function exportCSV() {
    if (filtered.length === 0) return;
    const now = new Date();
    const kw = query.trim() || '(all)';
    const header = ['RPC NUMBER', 'NAME', 'FATHER NAME', 'GENDER', 'CATEGORY', 'VALID TILL', 'STATUS'];
    const rows = filtered.map(r => [
      `"${r.registration_number}"`,
      `"${(r.name || '').replace(/"/g, '""')}"`,
      `"${(r.father_name || '').replace(/"/g, '""')}"`,
      `"${r.gender || ''}"`,
      `"${r.category}"`,
      `"${r.validity_date || ''}"`,
      `"${r.status || ''}"`
    ]);
    const csv = [`# TGPC RPh Registry - Search: ${kw} - ${fmtDate(now)}`, header.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `TGPC-RPH-SEARCH-${kw}-${fileDateStr(now)}.csv`;
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
      <div class="relative min-w-0 min-h-[2rem] flex-1" style="display:{searched ? 'inline-grid' : 'grid'};grid-template-columns:1fr">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9ca3af] pointer-events-none z-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <span class="col-start-1 row-start-1 invisible whitespace-nowrap pl-9 {searched ? 'pr-36' : 'pr-16'} py-1.5 text-[0.95rem] max-sm:text-base min-w-0 overflow-hidden">{query || 'Search by Name or Registered Pharmacist Certificate (RPC) Number'}</span>
        <input
          type="text"
          bind:value={query}
          oninput={onInputChange}
          onfocus={() => { if (query.trim().length >= 2) showSug = true; }}
          onblur={() => setTimeout(() => { showSug = false; }, 150)}
          onkeydown={onSearchKeydown}
          placeholder="Search by Name or Registered Pharmacist Certificate (RPC) Number"
          aria-label="Search"
          autocomplete="off"
          class="col-start-1 row-start-1 w-full pl-9 {searched ? 'pr-36' : 'pr-16'} py-1.5 text-[0.95rem] bg-transparent outline-none max-sm:text-base"
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
        {#if showSug && suggestions.length > 0}
          <div class="absolute left-0 right-0 top-full mt-1 bg-white border border-[#e5e7eb] rounded-lg shadow-lg z-20 overflow-hidden" style="max-height:280px;overflow-y:auto" transition:fade={{ duration: 100 }}>
            {#each suggestions as s, i}
              <button
                type="button"
                onmousedown={(e) => e.preventDefault()}
                onclick={() => selectSuggestion(s)}
                onmouseenter={() => sugIndex = i}
                class="w-full text-left px-3 py-1.5 flex items-center gap-2 text-[0.8rem] border-b border-[#f3f4f6] last:border-b-0 cursor-pointer"
                style="background:{i === sugIndex ? '#f0fdf4' : '#fff'}"
              >
                <span class="font-semibold text-[#2563eb] whitespace-nowrap">{s.registration_number}</span>
                <span class="truncate text-[#374151]" title={s.name}>{s.name}</span>
                <span class="ml-auto text-[0.65rem] whitespace-nowrap" style="color:{CATEGORY_COLORS[s.category]}">{s.category}</span>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    {#if searched}
      <div class="flex items-center gap-1 min-w-0 flex-1" transition:fly={{ y: 6, duration: 200, opacity: 0 }}>
        <span class="text-[0.75rem] text-[#9ca3af] tabular-nums flex-shrink-0">{filtered.length.toLocaleString()} results</span>
        <span class="ml-auto flex items-center gap-1.5">
          {#each CATEGORY_FILTERS as cat}
            <button onclick={() => category = cat}
              class="px-2.5 py-1 rounded text-[0.7rem] font-medium transition-all cursor-pointer border-none"
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
      <div class="hidden md:block">
        <div style="max-height:calc(100vh - 240px);overflow-y:auto;overflow-x:auto">
        <table class="w-full" style="table-layout:auto">
          <thead class="sticky top-0 bg-white z-10">
            <tr class="text-[0.65rem] font-semibold text-[#9ca3af] uppercase tracking-wider">
              <th class="font-inherit text-left py-1.5 border-b-2 border-[#e5e7eb] w-[52px]"></th>
              <th class="font-inherit text-left py-1.5 border-b-2 border-[#e5e7eb]">RPC NUMBER</th>
              <th class="font-inherit text-left py-1.5 border-b-2 border-[#e5e7eb]">Name</th>
              <th class="font-inherit text-left py-1.5 border-b-2 border-[#e5e7eb] hidden lg:table-cell">Father Name</th>
              <th class="font-inherit text-left py-1.5 border-b-2 border-[#e5e7eb] hidden xl:table-cell">Gender</th>
              <th class="font-inherit text-left py-1.5 border-b-2 border-[#e5e7eb]">Category</th>
              <th class="font-inherit text-left py-1.5 border-b-2 border-[#e5e7eb] hidden xl:table-cell">Valid Till</th>
              <th class="font-inherit text-right py-1.5 border-b-2 border-[#e5e7eb] pr-10">Status</th>
            </tr>
          </thead>
          <tbody>
            {#each filtered as r}
              <tr class="text-[0.875rem] text-[#374151] border-b border-[#f3f4f6]" style="content-visibility:auto;contain-intrinsic-size:48px">
                <td class="py-1.5">
                  <img src={photoUrl(r)} alt="" loading="lazy" class="w-9 h-11 rounded object-cover bg-[#f3f4f6]" />
                </td>
                <td class="py-2.5 text-[#2563eb]" style="font-weight:600">{r.registration_number}</td>
                <td class="py-2.5 truncate hidden lg:table-cell" title={r.name}>{r.name}</td>
                <td class="py-2.5 truncate hidden lg:table-cell" title={r.father_name || ''}>{r.father_name || '—'}</td>
                <td class="py-2.5 hidden xl:table-cell">{r.gender || '—'}</td>
                <td class="py-2.5" style="color:{CATEGORY_COLORS[r.category]}">{r.category}</td>
                <td class="py-2.5 hidden xl:table-cell">{r.validity_date || '—'}</td>
                <td class="py-2.5 text-right pr-10">
                  {#if r.status}
                    <span style="color:{r.status === 'Active' ? '#000000' : '#ef4444'}">{r.status}</span>
                  {:else}
                    <span class="text-[#374151]">—</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
        </div>
      </div>
      <div class="md:hidden space-y-0.5">
          {#each filtered as r}
            <div class="flex gap-3 py-2 border-b border-[#f3f4f6] text-[0.875rem]" style="content-visibility:auto;contain-intrinsic-size:110px">
              <img src={photoUrl(r)} alt="" loading="lazy" class="w-10 h-12 rounded object-cover bg-[#f3f4f6] flex-shrink-0" />
              <div class="min-w-0">
                <span class="text-[#2563eb]" style="font-weight:600">{r.registration_number}</span>
                <div class="mt-0.5 text-[#374151] truncate">{r.name}</div>
                <div class="mt-0.5 text-[#374151] truncate">{r.father_name || '—'}</div>
                <div class="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-1 text-[#374151]">
                  {#if r.gender}<span>{r.gender}</span>{/if}
                  <span style="color:{CATEGORY_COLORS[r.category]}">{r.category}</span>
                  {#if r.validity_date}<span>Valid till: {r.validity_date}</span>{/if}
                  {#if r.status}
                    <span style="color:{r.status === 'Active' ? '#000000' : '#ef4444'}">{r.status}</span>
                  {/if}
                </div>
              </div>
            </div>
          {/each}
        </div>
    {/if}
    </div>
  {/if}
</div>
