<script lang="ts">
  import type { PharmacistRecord, Category, CategoryFilter } from '$lib/types';
  import { searchRecords, advancedSearch, type AdvancedFilters } from '$lib/api';
  import DatePicker from '$lib/DatePicker.svelte';
  import { CATEGORY_COLORS, CATEGORIES as CAT_NAMES } from '$lib/colors';
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
  let advMode = $state(false);
  let advActive = $state(false);

  const CATEGORY_FILTERS: CategoryFilter[] = ['all', ...CAT_NAMES];

  let advFilters = $state<AdvancedFilters>({ valid_till: '' });
  let advCats = $state<Category[]>([]);

  let filtered = $derived(category === 'all' ? results : results.filter(r => r.category === category));
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;

  // Debounced typeahead — 300ms after typing, q>=3
  $effect(() => {
    const q = query.trim();
    if (advActive) return;
    clearTimeout(debounceTimer);
    if (q.length < 3) {
      if (q.length === 0 && searched && !advActive) {
        // handled by clear effect below
      }
      return;
    }
    // Don't debounce if already searched same query
    debounceTimer = setTimeout(() => { doSearch(); }, 300);
    return () => clearTimeout(debounceTimer);
  });

  // Single scrollable list — no cap, show all results.
  let resultsBox = $state<HTMLDivElement | undefined>();
  let resultsMaxH = $state('calc(100vh - 240px)');
  let resultsMinH = $state('0px');

  function measureResultsBox() {
    if (!resultsBox) return;
    const boxTop = resultsBox.getBoundingClientRect().top;
    const footer = document.querySelector('footer');
    const footerTop = footer ? footer.getBoundingClientRect().top : window.innerHeight;
    const available = Math.round(footerTop - boxTop - 10);
    if (available > 0) {
      resultsMaxH = `${available}px`;
      resultsMinH = `${available}px`;
    }
  }

  let resizeObserver: ResizeObserver | undefined;
  let measureTimer: ReturnType<typeof setTimeout> | undefined;

  $effect(() => {
    const panelOpen = advMode;
    const hasSearched = searched;
    if (resultsBox && (panelOpen || hasSearched)) {
      if (!panelOpen && hasSearched) {
        // Panel is closing (120ms fly transition) — re-measure once it's
        // gone rather than polling the DOM for the placeholder input.
        clearTimeout(measureTimer);
        measureTimer = setTimeout(measureResultsBox, 160);
      } else {
        measureResultsBox();
      }
    }
    // Clear any pending timer on unmount or when the effect re-runs, so a
    // stale timer can never fire after the component is destroyed.
    return () => clearTimeout(measureTimer);
  });

  $effect(() => {
    if (resultsBox) {
      measureResultsBox();
      resizeObserver?.disconnect();
      resizeObserver = new ResizeObserver(measureResultsBox);
      resizeObserver.observe(resultsBox);
      return () => resizeObserver?.disconnect();
    }
  });

  $effect(() => {
    if (query.trim() === '' && searched && !advActive) {
      searched = false;
      results = [];
      category = 'all';
    }
  });

  async function doSearch() {
    const q = query.trim();
    if (q.length < 3 || loading) return;
    loading = true;
    searched = true;
    advMode = false;
    advActive = false;
    try {
      results = await searchRecords(query);
    } finally {
      loading = false;
    }
  }

  async function applyAdvanced() {
    const hasAny =
      (advFilters.name ?? '').trim() ||
      (advFilters.father_name ?? '').trim() ||
      (advFilters.registration_number ?? '').trim() ||
      advCats.length > 0 ||
      (advFilters.gender ?? '') ||
      (advFilters.status ?? '') ||
      (advFilters.valid_till ?? '');
    if (!hasAny || loading) return;
    loading = true;
    searched = true;
    advActive = true;
    query = '';
    category = 'all';
    const payload: AdvancedFilters = {
      ...advFilters,
      category: advCats.length > 0 ? advCats : undefined
    };
    try {
      results = await advancedSearch(payload);
    } finally {
      loading = false;
      advMode = false;
    }
  }

  function clearAdvanced() {
    advFilters = { valid_till: '' };
    advCats = [];
    if (searched && advActive) {
      results = [];
      searched = false;
      category = 'all';
      advActive = false;
    }
  }

  function toggleAdvanced() {
    advMode = !advMode;
  }

  function onSearchKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') doSearch();
  }

  function chipStyle(cat: CategoryFilter): string {
    if (cat !== category) return 'background:#f3f4f6;color:#6b7280';
    return 'background:#00cc66;color:#fff';
  }

  function advCatStyle(cat: Category): string {
    return advCats.includes(cat)
      ? 'background:#00cc66;color:#fff'
      : 'background:#f3f4f6;color:#6b7280';
  }

  function toggleAdvCat(cat: Category) {
    advCats = advCats.includes(cat) ? advCats.filter(c => c !== cat) : [...advCats, cat];
  }

  function reset() {
    query = '';
    category = 'all';
    results = [];
    searched = false;
    advMode = false;
    advActive = false;
    advFilters = { valid_till: '' };
    advCats = [];
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
    const title = `TGPC RPh Index - Search: ${kw} - ${fmtDate(now)}`;
    const body = filtered.map(r => [r.registration_number, r.name, r.father_name || '—', r.gender || '—', r.category, r.validity_date || '—', r.status || '—']);

    const TEXTS = Object.fromEntries(
      Object.entries(CATEGORY_COLORS).map(([k, hex]) => [
        k,
        [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)]
      ])
    );

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
        if (data.section === 'body' && data.column.index === 4) {
          const cat = (data.cell.raw as string);
          const text = TEXTS[cat];
          if (text) data.cell.styles.textColor = text as [number, number, number];
        }
      },
      didDrawPage: (_data) => {
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
      doc.text('TGPC RPh Index - Open-Source Pharmacist Data', 10, ph - 10);
      doc.text('tgpc.pages.dev', doc.internal.pageSize.width / 2, ph - 10, { align: 'center' });
      doc.text(`Page ${i} / ${total}`, doc.internal.pageSize.width - 10, ph - 10, { align: 'right' });
    }
    doc.save(`TGPC-RPH-SEARCH-${kw}-${fileDateStr(now)}.pdf`);
  }

  const FORMULA_CHARS = ['=', '+', '-', '@', '\t', '\r'];

  function csvCell(value: unknown): string {
    const str = String(value ?? '');
    const escaped = str.replace(/"/g, '""');
    const prefix = FORMULA_CHARS.includes(str.trimStart().charAt(0)) ? "'" : '';
    return `"${prefix}${escaped}"`;
  }

  function exportCSV() {
    if (filtered.length === 0) return;
    const now = new Date();
    const kw = query.trim() || '(all)';
    const header = ['RPC NUMBER', 'NAME', 'FATHER NAME', 'GENDER', 'CATEGORY', 'VALID TILL', 'STATUS'];
    const rows = filtered.map(r => [
      csvCell(r.registration_number),
      csvCell(r.name),
      csvCell(r.father_name),
      csvCell(r.gender),
      csvCell(r.category),
      csvCell(r.validity_date),
      csvCell(r.status)
    ]);
    const csv = [`# TGPC RPh Index - Search: ${kw} - ${fmtDate(now)}`, header.join(','), ...rows.map(r => r.join(','))].join('\n');
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
              style="background:{query.trim().length >= 3 ? (searched ? 'rgba(0,204,102,0.08)' : '#00cc66') : '#f3f4f6'};color:{query.trim().length >= 3 ? (searched ? '#00cc66' : '#fff') : '#9ca3af'}"
              transition:fly={{ y: 4, duration: 120, opacity: 0 }}>
              SEARCH
            </button>
            {#if searched}
              <button onclick={reset}
                class="px-2.5 py-1 rounded text-[0.65rem] font-medium cursor-pointer border-none transition-colors uppercase"
                style="background:rgba(239,68,68,0.06);color:#ef4444"
                transition:fly={{ y: 4, duration: 120, opacity: 0 }}>
                Clear
              </button>
            {/if}
          </div>
        {/if}
      </div>
    </div>

    <button onclick={toggleAdvanced}
      class="flex-shrink-0 rounded px-3 py-1.5 text-[0.7rem] font-semibold uppercase cursor-pointer border transition-colors"
      style="border-color:{advMode ? '#00cc66' : '#e5e7eb'};background:{advMode ? 'rgba(0,204,102,0.08)' : '#fff'};color:{advMode ? '#00cc66' : '#374151'}"
      transition:fly={{ y: 4, duration: 120, opacity: 0 }}>
      Advanced
    </button>

    {#if searched}
      <div class="flex flex-wrap items-center gap-1 min-w-0 flex-1" transition:fly={{ y: 6, duration: 200, opacity: 0 }}>
        <span class="text-[0.75rem] text-[#9ca3af] tabular-nums flex-shrink-0">{filtered.length.toLocaleString()} results</span>
        {#if advActive}
          <span class="text-[0.65rem] font-semibold uppercase rounded px-1.5 py-0.5 flex-shrink-0" style="background:rgba(0,204,102,0.08);color:#00cc66">Advanced</span>
        {/if}
        <span class="ml-auto flex flex-wrap items-center gap-1.5">
          {#each CATEGORY_FILTERS as cat}
            <button onclick={() => { category = cat; }}
              class="px-2.5 py-1 rounded text-[0.7rem] font-medium transition-all cursor-pointer border-none"
              style={chipStyle(cat)}>
              {cat === 'all' ? 'All' : cat}
            </button>
          {/each}
          <button onclick={exportCSV} class="flex items-center gap-1 px-2.5 py-1 rounded text-[0.65rem] font-medium cursor-pointer border-none transition-colors" style="background:rgba(0,204,102,0.08);color:#00cc66">EXPORT CSV</button>
          <button onclick={exportPDF} class="flex items-center gap-1 px-2.5 py-1 rounded text-[0.65rem] font-medium cursor-pointer border-none transition-colors" style="background:rgba(239,68,68,0.06);color:#ef4444">EXPORT PDF</button>
        </span>
      </div>
    {/if}
  </div>

  {#if advMode}
    <div class="relative rounded-lg border border-[#e5e7eb] bg-white shadow-sm" transition:fade={{ duration: 150 }}>
      <button onclick={toggleAdvanced} aria-label="Close advanced search"
        class="absolute top-2 right-2 z-10 w-6 h-6 flex items-center justify-center rounded text-[#9ca3af] hover:text-[#374151] hover:bg-[#f3f4f6] cursor-pointer border-none transition-colors">
        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>

      <div class="px-3.5 py-3.5">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-3 gap-y-2.5">
          <label class="block">
            <span class="block text-[0.65rem] font-semibold text-[#6b7280] uppercase tracking-wider mb-1">RPC Number</span>
            <input type="text" bind:value={advFilters.registration_number}
              placeholder="RPC NUMBER"
              class="w-full h-8 px-2.5 text-[0.8rem] rounded-md border border-[#e5e7eb] bg-white outline-none transition-colors focus:border-[#00cc66]" />
          </label>
          <label class="block">
            <span class="block text-[0.65rem] font-semibold text-[#6b7280] uppercase tracking-wider mb-1">Name</span>
            <input type="text" bind:value={advFilters.name}
              placeholder="NAME"
              class="w-full h-8 px-2.5 text-[0.8rem] rounded-md border border-[#e5e7eb] bg-white outline-none transition-colors focus:border-[#00cc66]" />
          </label>
          <label class="block">
            <span class="block text-[0.65rem] font-semibold text-[#6b7280] uppercase tracking-wider mb-1">Father</span>
            <input type="text" bind:value={advFilters.father_name}
              placeholder="FATHER NAME"
              class="w-full h-8 px-2.5 text-[0.8rem] rounded-md border border-[#e5e7eb] bg-white outline-none transition-colors focus:border-[#00cc66]" />
          </label>

          <div>
            <span class="block text-[0.65rem] font-semibold text-[#6b7280] uppercase tracking-wider mb-1">Gender</span>
            <div class="flex h-8 rounded-md border border-[#e5e7eb] overflow-hidden bg-white">
              <button onclick={() => advFilters.gender = ''}
                class="flex-1 px-2 text-[0.75rem] font-medium cursor-pointer border-none transition-colors"
                style="{!advFilters.gender ? 'background:#00cc66;color:#fff' : 'background:#fff;color:#6b7280'}">All</button>
              <button onclick={() => advFilters.gender = 'Male'}
                class="flex-1 px-2 text-[0.75rem] font-medium cursor-pointer border-r border-[#e5e7eb] transition-colors"
                style="{advFilters.gender === 'Male' ? 'background:#00cc66;color:#fff' : 'background:#fff;color:#6b7280'}">Male</button>
              <button onclick={() => advFilters.gender = 'Female'}
                class="flex-1 px-2 text-[0.75rem] font-medium cursor-pointer border-r border-[#e5e7eb] transition-colors"
                style="{advFilters.gender === 'Female' ? 'background:#00cc66;color:#fff' : 'background:#fff;color:#6b7280'}">Female</button>
            </div>
          </div>
          <div>
            <span class="block text-[0.65rem] font-semibold text-[#6b7280] uppercase tracking-wider mb-1">Status</span>
            <div class="flex h-8 rounded-md border border-[#e5e7eb] overflow-hidden bg-white">
              <button onclick={() => advFilters.status = ''}
                class="flex-1 px-2 text-[0.75rem] font-medium cursor-pointer border-none transition-colors"
                style="{!advFilters.status ? 'background:#00cc66;color:#fff' : 'background:#fff;color:#6b7280'}">All</button>
              <button onclick={() => advFilters.status = 'Active'}
                class="flex-1 px-2 text-[0.75rem] font-medium cursor-pointer border-r border-[#e5e7eb] transition-colors"
                style="{advFilters.status === 'Active' ? 'background:#00cc66;color:#fff' : 'background:#fff;color:#6b7280'}">Active</button>
              <button onclick={() => advFilters.status = 'Inactive'}
                class="flex-1 px-2 text-[0.75rem] font-medium cursor-pointer border-r border-[#e5e7eb] transition-colors"
                style="{advFilters.status === 'Inactive' ? 'background:#ef4444;color:#fff' : 'background:#fff;color:#6b7280'}">Inactive</button>
            </div>
          </div>
          <div>
            <span class="block text-[0.65rem] font-semibold text-[#6b7280] uppercase tracking-wider mb-1">Valid Till</span>
            <DatePicker bind:value={advFilters.valid_till} />
          </div>

          <div class="sm:col-span-2 lg:col-span-2">
            <span class="block text-[0.65rem] font-semibold text-[#6b7280] uppercase tracking-wider mb-1">Category</span>
            <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
              <div class="flex flex-wrap items-center gap-1.5">
                {#each CAT_NAMES as cat}
                  <button onclick={() => toggleAdvCat(cat)}
                    class="px-3 h-8 rounded-md text-[0.75rem] font-medium cursor-pointer border-none transition-colors"
                    style={advCatStyle(cat)}>
                    {cat}
                  </button>
                {/each}
              </div>
              <div class="flex items-center gap-2">
                <button onclick={clearAdvanced}
                  class="h-8 px-3.5 rounded-md text-[0.7rem] font-semibold uppercase cursor-pointer border-none transition-colors"
                  style="background:#fff;color:#ef4444;border:1px solid rgba(239,68,68,0.35)">
                  Reset
                </button>
                <button onclick={applyAdvanced}
                  class="h-8 px-4 rounded-md text-[0.7rem] font-semibold uppercase cursor-pointer border-none transition-colors"
                  style="background:#00cc66;color:#fff">
                  Apply
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  {/if}

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
        <div style="max-height:{resultsMaxH};min-height:{resultsMinH};overflow-y:auto;overflow-x:auto" bind:this={resultsBox}>
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
                <td class="py-2.5 text-[#2563eb]" style="font-weight:600">
                  <a href="/rph/{r.registration_number}" class="hover:underline no-underline" aria-label="View profile for {r.registration_number}">
                    {r.registration_number}
                  </a>
                </td>
                <td class="py-2.5 truncate hidden lg:table-cell" title={r.name}>{r.name}</td>
                <td class="py-2.5 truncate hidden lg:table-cell" title={r.father_name || ''}>{r.father_name || '—'}</td>
                <td class="py-2.5 hidden xl:table-cell">{r.gender || '—'}</td>
                <td class="py-2.5" style="color:{CATEGORY_COLORS[r.category]}">{r.category}</td>
                <td class="py-2.5 hidden xl:table-cell">{r.validity_date || '—'}</td>
                <td class="py-2.5 text-right pr-10">
                  {#if r.status}
                    <span style="color:{r.status === 'Active' ? '#111827' : '#ef4444'}">{r.status}</span>
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
                <a href="/rph/{r.registration_number}" class="text-[#2563eb] hover:underline no-underline" style="font-weight:600" aria-label="View profile for {r.registration_number}">{r.registration_number}</a>
                <div class="mt-0.5 text-[#374151] truncate">{r.name}</div>
                <div class="mt-0.5 text-[#374151] truncate">{r.father_name || '—'}</div>
                <div class="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-1 text-[#374151]">
                  {#if r.gender}<span>{r.gender}</span>{/if}
                  <span style="color:{CATEGORY_COLORS[r.category]}">{r.category}</span>
                  {#if r.validity_date}<span>Valid till: {r.validity_date}</span>{/if}
                  {#if r.status}
                    <span style="color:{r.status === 'Active' ? '#111827' : '#ef4444'}">{r.status}</span>
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
