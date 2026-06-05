<script lang="ts">
  import { escapeHtml } from '$lib/utils';

  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  let notices = $state<any[]>([]);
  let years = $state<string[]>([]);
  let activeTab = $state<string | null>(null);
  let query = $state('');
  let loading = $state(true);

  function fmtDate(dateStr: string) {
    const d = new Date(dateStr + 'T00:00:00');
    return `${String(d.getDate()).padStart(2, '0')} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
  }

  function getYear(dateStr: string) { return dateStr.slice(0, 4); }

  function ext(url: string) {
    const m = url.match(/\.([a-z0-9]+)(?:\?.*)?$/i);
    return m ? m[1].toLowerCase() : 'link';
  }

  function linkClass(url: string) {
    const e = ext(url);
    if (e === 'pdf') return 'pdf';
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(e)) return 'image';
    return 'ext';
  }

  let filtered = $derived.by(() => {
    return notices.filter(n => {
      if (activeTab && getYear(n.date) !== activeTab) return false;
      if (!query) return true;
      const q = query.toLowerCase();
      return n.title.toLowerCase().includes(q) || fmtDate(n.date).toLowerCase().includes(q);
    });
  });

  async function load() {
    loading = true;
    try {
      const resp = await fetch('/api/notice');
      if (!resp.ok) throw new Error('Failed');
      const data = await resp.json();
      data.sort((a: any, b: any) => b.date.localeCompare(a.date));
      notices = data;
      years = [...new Set(notices.map((n: any) => getYear(n.date)))].sort((a, b) => +b - +a);
      activeTab = years[0] || null;
    } catch {
      notices = [];
    }
    loading = false;
  }

  function setTab(year: string | null) {
    activeTab = year;
  }

  $effect(() => { load(); });
</script>

<div class="space-y-4">
  <div class="bg-white border border-tgpc-gray-border rounded-lg p-3">
    <div class="flex items-center justify-between flex-wrap gap-2">
      <h2 class="text-[1.1rem] max-md:text-[0.9rem] font-semibold">
        <span class="text-tgpc-gray-light">Notices &amp; Circulars</span>
      </h2>
      {#if !loading}
        <span class="text-[0.8rem] text-tgpc-gray-muted">{notices.length} notice{notices.length !== 1 ? 's' : ''}</span>
      {/if}
    </div>
  </div>

  <!-- Search + Tabs -->
  <div class="bg-white border border-tgpc-gray-border rounded-lg p-3 space-y-3">
    <div class="flex items-center gap-2 flex-wrap">
      <div class="flex-1 min-w-0 relative">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-tgpc-gray-muted pointer-events-none" viewBox="0 0 24 24" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
        <input type="text" bind:value={query} placeholder="Search notices..."
          class="w-full pl-9 pr-4 py-2 border border-tgpc-gray-border rounded-full text-[0.85rem] bg-tgpc-bg outline-none focus:border-tgpc-green transition-colors max-sm:text-base" />
      </div>
      {#if query}
        <span class="text-[0.8rem] text-tgpc-gray-muted">{filtered.length} of {notices.length} notices</span>
      {/if}
    </div>

    <div class="flex gap-1 overflow-x-auto pb-0.5" style="scrollbar-width:none">
      {#each years as year}
        <button onclick={() => setTab(year)}
          class="flex-shrink-0 px-3 py-1.5 rounded-lg text-[0.8rem] font-medium transition-colors cursor-pointer border-none"
          style={year === activeTab ? 'background:#00cc66;color:#fff' : 'background:transparent;color:#4a4a5a;border:1px solid #e2e8f0'}>
          {year}
          <span class="opacity-60 text-[0.7rem]"> ({notices.filter(n => getYear(n.date) === year).length})</span>
        </button>
      {/each}
    </div>
  </div>

  <!-- Results -->
  {#if loading}
    <div class="bg-white border border-tgpc-gray-border rounded-lg p-3 text-center py-8 text-tgpc-gray-muted text-[0.875rem]">
      <div class="w-6 h-6 border-3 border-tgpc-gray-border border-t-tgpc-green rounded-full animate-spin mx-auto mb-3"></div>
      <p>Loading notices...</p>
    </div>
  {:else if filtered.length === 0}
    <div class="bg-white border border-tgpc-gray-border rounded-lg p-3 text-center py-8 text-tgpc-gray-muted text-[0.875rem]">
      <p>No notices match your search</p>
    </div>
  {:else}
    <div class="bg-white border border-tgpc-gray-border rounded-lg overflow-hidden" style="max-height:calc(100vh - 275px);overflow-y:auto">
      <!-- Desktop Table -->
      <table class="w-full text-[0.85rem] hidden md:table">
        <thead class="bg-gray-50 sticky top-0 z-10">
          <tr class="text-[0.75rem] uppercase font-semibold tracking-wider text-tgpc-text-secondary border-b-2 border-tgpc-gray-border">
            <th class="text-left py-3 px-4 whitespace-nowrap">Date</th>
            <th class="text-left py-3 px-4">Title / Description</th>
            <th class="text-left py-3 px-4">Links</th>
          </tr>
        </thead>
        <tbody>
          {#if activeTab === null}
            {#each years as year}
              {@const fy = filtered.filter((n: any) => getYear(n.date) === year)}
              {#if fy.length > 0}
                <tr class="bg-gray-50 font-semibold text-tgpc-gray-muted text-[0.75rem] uppercase tracking-wider">
                  <td colspan="3" class="py-3 px-4 border-b-2 border-tgpc-gray-border">{year} &mdash; {fy.length} notice{fy.length !== 1 ? 's' : ''}</td>
                </tr>
                {#each fy as n}
                  {#each [n] as _}
                    <tr class="border-b border-tgpc-table-border hover:bg-[#f0fdf4]">
                      <td class="py-3 px-4 whitespace-nowrap font-medium text-tgpc-text-secondary">{escapeHtml(fmtDate(n.date))}</td>
                      <td class="py-3 px-4">{escapeHtml(n.title)}</td>
                      <td class="py-3 px-4 whitespace-nowrap space-x-1">
                        {#each n.links || [] as link}
                          {@const cls = linkClass(link.url)}
                          {@const href = link.url.startsWith('http') ? link.url : `https://pub-4591c8c5282040459ade2ed1e5e3d5be.r2.dev/notice${link.url}`}
                          <a href={href} target="_blank" rel="noopener"
                            class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[0.75rem] font-medium no-underline transition-colors"
                            style={cls === 'pdf' ? 'color:#dc2626;border:1px solid #fca5a5;background:transparent' : cls === 'image' ? 'color:#7c3aed;border:1px solid #c4b5fd;background:transparent' : 'color:#2563eb;border:1px solid #93c5fd;background:transparent'}>
                            {escapeHtml(link.label)}
                          </a>
                        {/each}
                      </td>
                    </tr>
                  {/each}
                {/each}
              {/if}
            {/each}
          {:else}
            {#each filtered as n}
              <tr class="border-b border-tgpc-table-border hover:bg-[#f0fdf4]">
                <td class="py-3 px-4 whitespace-nowrap font-medium text-tgpc-text-secondary">{escapeHtml(fmtDate(n.date))}</td>
                <td class="py-3 px-4">{escapeHtml(n.title)}</td>
                <td class="py-3 px-4 whitespace-nowrap space-x-1">
                  {#each n.links || [] as link}
                    {@const cls = linkClass(link.url)}
                    {@const href = link.url.startsWith('http') ? link.url : `https://pub-4591c8c5282040459ade2ed1e5e3d5be.r2.dev/notice${link.url}`}
                    <a href={href} target="_blank" rel="noopener"
                      class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[0.75rem] font-medium no-underline transition-colors"
                      style={cls === 'pdf' ? 'color:#dc2626;border:1px solid #fca5a5;background:transparent' : cls === 'image' ? 'color:#7c3aed;border:1px solid #c4b5fd;background:transparent' : 'color:#2563eb;border:1px solid #93c5fd;background:transparent'}>
                      {escapeHtml(link.label)}
                    </a>
                  {/each}
                </td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>

      <!-- Mobile Cards -->
      <div class="md:hidden space-y-1 p-2">
        {#if activeTab === null}
          {#each years as year}
            {@const fy = filtered.filter((n: any) => getYear(n.date) === year)}
            {#if fy.length > 0}
              <div class="text-[0.75rem] font-semibold uppercase tracking-wider text-tgpc-gray-muted py-2 px-1">{year} &mdash; {fy.length}</div>
              {#each fy as n}
                <div class="border border-tgpc-gray-border rounded-lg p-3">
                  <div class="flex flex-col gap-1">
                    <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Date</span>
                    <span class="text-[0.85rem]">{escapeHtml(fmtDate(n.date))}</span>
                  </div>
                  <div class="flex flex-col gap-1 mt-2">
                    <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Title</span>
                    <span class="text-[0.85rem]">{escapeHtml(n.title)}</span>
                  </div>
                  {#if n.links?.length}
                    <div class="flex flex-col gap-1 mt-2">
                      <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Links</span>
                      <div class="flex gap-1 flex-wrap">
                        {#each n.links as link}
                          {@const cls = linkClass(link.url)}
                          {@const href = link.url.startsWith('http') ? link.url : `https://pub-4591c8c5282040459ade2ed1e5e3d5be.r2.dev/notice${link.url}`}
                          <a href={href} target="_blank" rel="noopener"
                            class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[0.75rem] font-medium no-underline transition-colors"
                            style={cls === 'pdf' ? 'color:#dc2626;border:1px solid #fca5a5' : cls === 'image' ? 'color:#7c3aed;border:1px solid #c4b5fd' : 'color:#2563eb;border:1px solid #93c5fd'}>
                            {escapeHtml(link.label)}
                          </a>
                        {/each}
                      </div>
                    </div>
                  {/if}
                </div>
              {/each}
            {/if}
          {/each}
        {:else}
          {#each filtered as n}
            <div class="border border-tgpc-gray-border rounded-lg p-3">
              <div class="flex flex-col gap-1">
                <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Date</span>
                <span class="text-[0.85rem]">{escapeHtml(fmtDate(n.date))}</span>
              </div>
              <div class="flex flex-col gap-1 mt-2">
                <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Title</span>
                <span class="text-[0.85rem]">{escapeHtml(n.title)}</span>
              </div>
              {#if n.links?.length}
                <div class="flex flex-col gap-1 mt-2">
                  <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Links</span>
                  <div class="flex gap-1 flex-wrap">
                    {#each n.links as link}
                      {@const cls = linkClass(link.url)}
                      {@const href = link.url.startsWith('http') ? link.url : `https://pub-4591c8c5282040459ade2ed1e5e3d5be.r2.dev/notice${link.url}`}
                      <a href={href} target="_blank" rel="noopener"
                        class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[0.75rem] font-medium no-underline transition-colors"
                        style={cls === 'pdf' ? 'color:#dc2626;border:1px solid #fca5a5' : cls === 'image' ? 'color:#7c3aed;border:1px solid #c4b5fd' : 'color:#2563eb;border:1px solid #93c5fd'}>
                        {escapeHtml(link.label)}
                      </a>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</div>
