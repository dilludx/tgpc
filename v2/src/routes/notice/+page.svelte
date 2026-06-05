<script lang="ts">
  import type { Notice } from '$lib/types';
  import { fetchNotices } from '$lib/api';
  import Spinner from '$lib/components/Spinner.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';
  import LinkBadge from '$lib/components/LinkBadge.svelte';

  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  let notices = $state<Notice[]>([]);
  let years = $state<string[]>([]);
  let activeTab = $state<string | null>(null);
  let query = $state('');
  let loading = $state(true);

  function fmtDate(dateStr: string) {
    const d = new Date(dateStr + 'T00:00:00');
    return `${String(d.getDate()).padStart(2, '0')} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
  }

  function getYear(dateStr: string) { return dateStr.slice(0, 4); }

  function linkClass(url: string): string {
    const e = url.match(/\.([a-z0-9]+)(?:\?.*)?$/i)?.[1]?.toLowerCase() || 'link';
    if (e === 'pdf') return 'pdf';
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(e)) return 'image';
    return 'ext';
  }

  function resolveUrl(url: string): string {
    if (url.startsWith('http')) return url;
    return `https://pub-4591c8c5282040459ade2ed1e5e3d5be.r2.dev/notice${url}`;
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
    notices = await fetchNotices();
    years = [...new Set(notices.map(n => getYear(n.date)))].sort((a, b) => +b - +a);
    activeTab = years[0] || null;
    loading = false;
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

  <div class="bg-white border border-tgpc-gray-border rounded-lg p-3 space-y-3">
    <div class="flex items-center gap-2 flex-wrap">
      <div class="flex-1 min-w-0 relative">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-tgpc-gray-muted pointer-events-none" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
        </svg>
        <input type="text" bind:value={query} placeholder="Search notices..."
          aria-label="Search notices"
          class="w-full pl-9 pr-4 py-2 border border-tgpc-gray-border rounded-full text-[0.85rem] bg-tgpc-bg outline-none focus:border-tgpc-green focus:ring-3 focus:ring-tgpc-green/20 transition-all max-sm:text-base" />
      </div>
      {#if query}
        <span class="text-[0.8rem] text-tgpc-gray-muted">{filtered.length} of {notices.length} notices</span>
      {/if}
    </div>

    <div class="flex gap-1 overflow-x-auto pb-0.5" style="scrollbar-width:none" role="tablist" aria-label="Filter by year">
      {#each years as year}
        <button role="tab" aria-selected={year === activeTab} onclick={() => activeTab = year}
          class="flex-shrink-0 px-3 py-1.5 rounded-lg text-[0.8rem] font-medium transition-colors cursor-pointer border-none"
          style={year === activeTab ? 'background:#00cc66;color:#fff' : 'background:transparent;color:#4a4a5a;border:1px solid #e2e8f0'}>
          {year}
          <span class="opacity-60 text-[0.7rem]"> ({notices.filter(n => getYear(n.date) === year).length})</span>
        </button>
      {/each}
    </div>
  </div>

  {#if loading}
    <Spinner label="Loading notices…" />
  {:else if filtered.length === 0}
    <EmptyState message="No notices match your search" />
  {:else}
    <div class="bg-white border border-tgpc-gray-border rounded-lg overflow-hidden" style="max-height:calc(100vh - 275px);overflow-y:auto">
      <table class="w-full text-[0.85rem] hidden md:table">
        <thead class="bg-gray-50 sticky top-0 z-10">
          <tr class="text-[0.75rem] uppercase font-semibold tracking-wider text-tgpc-text-secondary border-b-2 border-tgpc-gray-border">
            <th class="text-left py-3 px-4 whitespace-nowrap" scope="col">Date</th>
            <th class="text-left py-3 px-4" scope="col">Title / Description</th>
            <th class="text-left py-3 px-4" scope="col">Links</th>
          </tr>
        </thead>
        <tbody>
          {#if activeTab === null}
            {#each years as year}
              {@const fy = filtered.filter(n => getYear(n.date) === year)}
              {#if fy.length > 0}
                <tr class="bg-gray-50 font-semibold text-tgpc-gray-muted text-[0.75rem] uppercase tracking-wider">
                  <td colspan="3" class="py-3 px-4 border-b-2 border-tgpc-gray-border">{year} &mdash; {fy.length} notice{fy.length !== 1 ? 's' : ''}</td>
                </tr>
                {#each fy as n}
                  <tr class="border-b border-tgpc-table-border hover:bg-[#f0fdf4]">
                    <td class="py-3 px-4 whitespace-nowrap font-medium text-tgpc-text-secondary">{fmtDate(n.date)}</td>
                    <td class="py-3 px-4">{n.title}</td>
                    <td class="py-3 px-4 whitespace-nowrap space-x-1">
                      {#each n.links || [] as link}
                        <LinkBadge url={resolveUrl(link.url)} label={link.label} cls={linkClass(link.url)} />
                      {/each}
                    </td>
                  </tr>
                {/each}
              {/if}
            {/each}
          {:else}
            {#each filtered as n}
              <tr class="border-b border-tgpc-table-border hover:bg-[#f0fdf4]">
                <td class="py-3 px-4 whitespace-nowrap font-medium text-tgpc-text-secondary">{fmtDate(n.date)}</td>
                <td class="py-3 px-4">{n.title}</td>
                <td class="py-3 px-4 whitespace-nowrap space-x-1">
                  {#each n.links || [] as link}
                    <LinkBadge url={resolveUrl(link.url)} label={link.label} cls={linkClass(link.url)} />
                  {/each}
                </td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>

      <div class="md:hidden space-y-1 p-2">
        {#if activeTab === null}
          {#each years as year}
            {@const fy = filtered.filter(n => getYear(n.date) === year)}
            {#if fy.length > 0}
              <div class="text-[0.75rem] font-semibold uppercase tracking-wider text-tgpc-gray-muted py-2 px-1">{year} &mdash; {fy.length}</div>
              {#each fy as n}
                <article class="border border-tgpc-gray-border rounded-lg p-3">
                  <div class="flex flex-col gap-1">
                    <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Date</span>
                    <span class="text-[0.85rem]">{fmtDate(n.date)}</span>
                  </div>
                  <div class="flex flex-col gap-1 mt-2">
                    <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Title</span>
                    <span class="text-[0.85rem]">{n.title}</span>
                  </div>
                  {#if n.links?.length}
                    <div class="flex flex-col gap-1 mt-2">
                      <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Links</span>
                      <div class="flex gap-1 flex-wrap">
                        {#each n.links as link}
                          <LinkBadge url={resolveUrl(link.url)} label={link.label} cls={linkClass(link.url)} />
                        {/each}
                      </div>
                    </div>
                  {/if}
                </article>
              {/each}
            {/if}
          {/each}
        {:else}
          {#each filtered as n}
            <article class="border border-tgpc-gray-border rounded-lg p-3">
              <div class="flex flex-col gap-1">
                <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Date</span>
                <span class="text-[0.85rem]">{fmtDate(n.date)}</span>
              </div>
              <div class="flex flex-col gap-1 mt-2">
                <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Title</span>
                <span class="text-[0.85rem]">{n.title}</span>
              </div>
              {#if n.links?.length}
                <div class="flex flex-col gap-1 mt-2">
                  <span class="text-[0.7rem] uppercase font-semibold text-tgpc-gray-muted">Links</span>
                  <div class="flex gap-1 flex-wrap">
                    {#each n.links as link}
                      <LinkBadge url={resolveUrl(link.url)} label={link.label} cls={linkClass(link.url)} />
                    {/each}
                  </div>
                </div>
              {/if}
            </article>
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</div>
