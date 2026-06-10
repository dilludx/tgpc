<script lang="ts">
  import type { PharmacistRecord, Category, CategoryFilter } from '$lib/types';
  import { searchRecords } from '$lib/api';
  import { CATEGORY_COLORS, CATEGORY_BG, CATEGORIES as CAT_NAMES } from '$lib/colors';

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
    return cat === 'all' ? 'background:#111;color:#fff' : 'background:' + CATEGORY_COLORS[cat as Category] + ';color:#fff';
  }

  function reset() {
    query = '';
    category = 'all';
    page = 1;
    results = [];
    searched = false;
  }
</script>

<div class="space-y-4">
  <!-- Search -->
  <div class="flex items-center gap-2">
    <div class="relative flex-1">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9ca3af] pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
      <input
        type="text"
        bind:value={query}
        onkeydown={(e) => e.key === 'Enter' && doSearch()}
        placeholder="Search by name or registration number"
        aria-label="Search"
        class="w-full pl-9 pr-4 py-2.5 border-b-2 border-[#e5e7eb] text-[0.95rem] bg-transparent outline-none transition-colors focus:border-[#00cc66] max-sm:text-base"
      />
    </div>
    <button onclick={doSearch} disabled={query.trim().length < 3}
      class="px-4 py-2 rounded text-[0.8rem] font-semibold transition-all cursor-pointer border-none disabled:opacity-30 disabled:cursor-not-allowed"
      style="background:{query.trim().length >= 3 ? '#00cc66' : '#e5e7eb'};color:{query.trim().length >= 3 ? '#fff' : '#9ca3af'}">
      {loading ? '…' : 'Search'}
    </button>
  </div>

  <!-- Chips -->
  {#if searched}
    <div class="flex items-center gap-1 text-[0.75rem]">
      {#each CATEGORY_FILTERS as cat}
        <button onclick={() => { category = cat; page = 1; }}
          class="px-2.5 py-1 rounded text-[0.7rem] font-medium transition-all cursor-pointer border-none"
          style={chipStyle(cat)}>
          {cat === 'all' ? 'All' : cat}
        </button>
      {/each}
      <button onclick={reset}
        class="ml-2 px-2.5 py-1 rounded text-[0.7rem] font-medium text-[#9ca3af] hover:text-[#111] transition-colors cursor-pointer border-none bg-transparent">
        Clear
      </button>
    </div>
  {/if}

  <!-- Results -->
  {#if searched}
    {#if loading}
      <div class="space-y-3 py-4">
        {#each Array(5) as _}
          <div class="h-4 bg-[#f3f4f6] rounded" style="width:{70 + Math.random() * 30}%"></div>
        {/each}
      </div>
    {:else if filtered.length === 0}
      <p class="text-[0.85rem] text-[#9ca3af] py-8 text-center">No results</p>
    {:else}
      <div class="text-[0.75rem] text-[#9ca3af] mb-1 tabular-nums">{start}–{end} of {filtered.length}</div>

      <div style="max-height:calc(100vh - 240px);overflow-y:auto">
        <!-- Desktop -->
        <div class="hidden md:block">
          {#each paginated as r}
            <div class="flex items-center gap-3 py-2.5 border-b border-[#f3f4f6] text-[0.875rem]">
              <span class="font-semibold text-[#2563eb] w-36 flex-shrink-0">{r.registration_number}</span>
              <span class="flex-1">{r.name}</span>
              <span class="w-36 flex-shrink-0 text-[#6b7280] hidden lg:block">{r.father_name || '—'}</span>
              <span class="inline-flex items-center px-1.5 rounded-full text-[0.65rem] font-semibold leading-[18px]" style="background:{CATEGORY_BG[r.category]};color:{CATEGORY_COLORS[r.category]}">
                {r.category}
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
                <span class="inline-flex items-center px-1.5 rounded-full text-[0.6rem] font-semibold leading-[18px]" style="background:{CATEGORY_BG[r.category]};color:{CATEGORY_COLORS[r.category]}">{r.category}</span>
              </div>
              <div class="text-[0.875rem] mt-0.5">{r.name}</div>
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
