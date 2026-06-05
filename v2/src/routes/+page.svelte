<script lang="ts">
  import { escapeHtml, fmtNumber } from '$lib/utils';

  let query = $state('');
  let category = $state('all');
  let page = $state(1);
  const PER_PAGE = $derived(window.innerWidth <= 768 ? 25 : 50);

  const CATEGORIES = ['all', 'BPharm', 'DPharm', 'MPharm', 'PharmD', 'QC', 'QP'];

  const badgeColors: Record<string, { bg: string; text: string }> = {
    BPharm: { bg: '#dcfce7', text: '#166534' },
    DPharm: { bg: '#fef9c3', text: '#854d0e' },
    MPharm: { bg: '#ede9fe', text: '#5b21b6' },
    PharmD: { bg: '#fecaca', text: '#991b1b' },
    QC: { bg: '#dbeafe', text: '#1e40af' },
    QP: { bg: '#fed7aa', text: '#9a3412' }
  };

  const mockResults = [
    { registration_number: 'TS12345', name: 'John Doe', father_name: 'Richard Doe', category: 'BPharm' },
    { registration_number: 'TG67890', name: 'Jane Smith', father_name: 'Robert Smith', category: 'DPharm' },
    { registration_number: 'TSDR1111', name: 'Alice Johnson', father_name: 'Michael Johnson', category: 'MPharm' },
    { registration_number: 'TGDR2222', name: 'Bob Williams', father_name: 'David Williams', category: 'PharmD' },
    { registration_number: 'TG33333', name: 'Carol Brown', father_name: 'James Brown', category: 'QC' },
    { registration_number: 'TS44444', name: 'Dave Miller', father_name: 'John Miller', category: 'QP' },
    { registration_number: 'TG55555', name: 'Eve Davis', father_name: 'Thomas Davis', category: 'BPharm' },
    { registration_number: 'TS66666', name: 'Frank Wilson', father_name: 'Charles Wilson', category: 'DPharm' },
    { registration_number: 'TG77777', name: 'Grace Taylor', father_name: 'George Taylor', category: 'MPharm' },
    { registration_number: 'TS88888', name: 'Henry Anderson', father_name: 'Edward Anderson', category: 'PharmD' },
  ];

  let filtered = $derived(
    category === 'all'
      ? mockResults
      : mockResults.filter(r => r.category === category)
  );

  let totalPages = $derived(Math.max(1, Math.ceil(filtered.length / PER_PAGE)));
  let paginated = $derived(filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE));
  let start = $derived(filtered.length === 0 ? 0 : (page - 1) * PER_PAGE + 1);
  let end = $derived(Math.min(page * PER_PAGE, filtered.length));

  function doSearch() {
    page = 1;
  }

  function setCategory(cat: string) {
    category = cat;
    page = 1;
  }

  function prevPage() {
    if (page > 1) page--;
  }

  function nextPage() {
    if (page < totalPages) page++;
  }
</script>

<div class="space-y-4">
  <!-- Search Section -->
  <div class="bg-white border border-tgpc-gray-border rounded-lg p-2.5 sm:p-3">
    <h2 class="text-[1.1rem] max-md:text-[0.9rem] font-semibold mb-3">
      <span class="text-tgpc-gray-light">Search</span>
      <span style="color:#ef4444">Rx</span>
    </h2>

    <!-- Search Input + Buttons -->
    <div class="flex flex-col sm:flex-row gap-2">
      <input
        type="text"
        bind:value={query}
        onkeydown={(e) => e.key === 'Enter' && doSearch()}
        placeholder="Enter Name or Registration Number (min 3 chars)"
        class="flex-1 px-4 py-2.5 border border-tgpc-gray-border rounded-full text-[0.875rem] bg-tgpc-bg outline-none focus:border-tgpc-green transition-colors max-sm:text-base"
      />
      <div class="flex gap-2 flex-wrap">
        <button onclick={doSearch}
          class="px-4 py-2 rounded-full text-[0.8125rem] font-medium bg-tgpc-green text-white hover:bg-tgpc-green-hover transition-colors cursor-pointer border-none">
          Search
        </button>
        <button onclick={() => { query = ''; category = 'all'; page = 1; }}
          class="px-4 py-2 rounded-full text-[0.8125rem] font-medium bg-gray-200 text-tgpc-text-secondary hover:bg-tgpc-bg-hover transition-colors cursor-pointer border-none">
          Reset
        </button>
        <button disabled
          class="px-4 py-2 rounded-full text-[0.8125rem] font-medium bg-gray-100 text-tgpc-gray-muted cursor-not-allowed border-none">
          PDF
        </button>
        <button disabled
          class="px-4 py-2 rounded-full text-[0.8125rem] font-medium bg-gray-100 text-tgpc-gray-muted cursor-not-allowed border-none">
          CSV
        </button>
      </div>
    </div>

    <!-- Filter Chips -->
    <div class="flex gap-2 mt-3 overflow-x-auto pb-1" style="scrollbar-width:none;-ms-overflow-style:none">
      {#each CATEGORIES as cat}
        <button
          onclick={() => setCategory(cat)}
          class="flex-shrink-0 px-3 py-1.5 rounded-full text-[0.75rem] font-medium transition-colors cursor-pointer border-none"
          style={cat === category
            ? 'background:#00cc66;color:#fff'
            : 'background:transparent;color:#6b7280;border:1px solid #e5e7eb'}
        >
          {cat === 'all' ? 'All' : cat}
        </button>
      {/each}
    </div>
  </div>

  <!-- Results Section -->
  {#if query.length >= 3 || filtered.length > 0}
    <div class="bg-white border border-tgpc-gray-border rounded-lg p-2.5 sm:p-3"
         style="max-height:calc(100vh - 275px);overflow-y:auto">
      <div class="text-[0.8rem] text-tgpc-gray-muted mb-2 pb-2 border-b border-tgpc-table-border">
        Showing {filtered.length} result{filtered.length !== 1 ? 's' : ''}
      </div>

      <!-- Desktop Table -->
      <div class="hidden md:block">
        <table class="w-full text-[0.875rem]">
          <thead>
            <tr class="text-[0.75rem] uppercase font-semibold tracking-wider text-tgpc-text-secondary border-b border-tgpc-table-border">
              <th class="text-left py-2 px-3">Registration Number</th>
              <th class="text-left py-2 px-3">Name</th>
              <th class="text-left py-2 px-3">Father's Name</th>
              <th class="text-left py-2 px-3">Category</th>
            </tr>
          </thead>
          <tbody>
            {#each paginated as result}
              <tr class="border-b border-tgpc-table-border">
                <td class="py-2.5 px-3 font-medium text-tgpc-blue">{escapeHtml(result.registration_number)}</td>
                <td class="py-2.5 px-3">{escapeHtml(result.name)}</td>
                <td class="py-2.5 px-3 text-tgpc-text-secondary">{escapeHtml(result.father_name)}</td>
                <td class="py-2.5 px-3">
                  {#if badgeColors[result.category]}
                    <span class="inline-block px-2 py-0.5 text-[0.8125rem] font-semibold rounded-md"
                          style="background:{badgeColors[result.category].bg};color:{badgeColors[result.category].text}">
                      {result.category}
                    </span>
                  {/if}
                </td>
              </tr>
            {:else}
              <tr>
                <td colspan="4" class="text-center py-8 text-tgpc-gray-muted">No results</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Mobile Cards -->
      <div class="md:hidden space-y-2">
        {#each paginated as result}
          <div class="border border-tgpc-gray-border rounded-lg p-3">
            <div class="flex items-center justify-between mb-1">
              <span class="font-medium text-tgpc-blue text-[0.875rem]">{escapeHtml(result.registration_number)}</span>
              <span class="inline-block px-2 py-0.5 text-[0.8125rem] font-semibold rounded-md"
                    style="background:{badgeColors[result.category].bg};color:{badgeColors[result.category].text}">
                {result.category}
              </span>
            </div>
            <div class="text-[0.875rem] text-tgpc-text">{escapeHtml(result.name)}</div>
            <div class="text-[0.75rem] text-tgpc-text-secondary mt-0.5">{escapeHtml(result.father_name)}</div>
          </div>
        {:else}
          <div class="text-center py-8 text-tgpc-gray-muted">No results</div>
        {/each}
      </div>

      <!-- Pagination -->
      {#if filtered.length > PER_PAGE}
        <div class="flex items-center justify-between mt-3 pt-3 border-t border-tgpc-table-border text-[0.8rem]">
          <span class="text-tgpc-text-secondary">{start}–{end} of {filtered.length}</span>
          <div class="flex items-center gap-3">
            <button onclick={prevPage} disabled={page <= 1}
              class="px-3 py-1.5 rounded-full text-[0.8125rem] font-medium transition-colors cursor-pointer border-none disabled:opacity-40 disabled:cursor-not-allowed"
              style="background:var(--color-tgpc-bg);color:var(--color-tgpc-text)">
              &larr; Prev
            </button>
            <span class="text-tgpc-text-secondary">Page {page} of {totalPages}</span>
            <button onclick={nextPage} disabled={page >= totalPages}
              class="px-3 py-1.5 rounded-full text-[0.8125rem] font-medium transition-colors cursor-pointer border-none disabled:opacity-40 disabled:cursor-not-allowed"
              style="background:var(--color-tgpc-bg);color:var(--color-tgpc-text)">
              Next &rarr;
            </button>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>
