<script lang="ts">
  import type { Notice } from '$lib/types';
  import { fetchNotices } from '$lib/api';
  import Skeleton from '$lib/components/Skeleton.svelte';
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

<div class="space-y-5">
  <div class="bg-white border border-tgpc-gray-border rounded-2xl p-5 shadow-sm">
    <div class="flex items-center justify-between flex-wrap gap-2">
      <h2 class="text-[1.4rem] font-bold tracking-tight">
        <span class="text-tgpc-gray-light">Notices &amp; Circulars</span>
      </h2>
      {#if !loading}
        <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-tgpc-gray-border/50 text-[0.75rem] font-semibold text-tgpc-gray-muted tabular-nums">
          {notices.length}
        </span>
      {/if}
    </div>
  </div>

  <div class="bg-white border border-tgpc-gray-border rounded-2xl p-5 shadow-sm space-y-4">
    <div class="flex items-center gap-2 flex-wrap">
      <div class="flex-1 min-w-0 relative">
        <svg class="absolute left-4 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-tgpc-gray-muted pointer-events-none" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <input type="text" bind:value={query} placeholder="Search notices…"
          aria-label="Search notices"
          class="w-full pl-11 pr-4 py-2.5 border-2 border-tgpc-gray-border rounded-2xl text-[0.9rem] bg-white outline-none transition-all max-sm:text-base font-medium"
          onfocus={(e) => { e.currentTarget.style.borderColor = '#00cc66'; e.currentTarget.style.boxShadow = '0 0 0 4px #00cc6620'; }}
          onblur={(e) => { e.currentTarget.style.borderColor = ''; e.currentTarget.style.boxShadow = ''; }} />
      </div>
      {#if query}
        <span class="text-[0.8rem] font-medium text-tgpc-gray-muted tabular-nums">{filtered.length} / {notices.length}</span>
      {/if}
    </div>

    <div class="flex gap-1.5 overflow-x-auto pb-0.5" style="scrollbar-width:none" role="tablist" aria-label="Filter by year">
      {#each years as year}
        <button role="tab" aria-selected={year === activeTab} onclick={() => activeTab = year}
          class="flex-shrink-0 px-4 py-2 rounded-xl text-[0.8rem] font-semibold transition-all cursor-pointer border-none active:scale-95"
          style={year === activeTab ? 'background:#00cc66;color:#fff;box-shadow:0 2px 8px #00cc6640' : 'background:white;color:#4a4a5a;border:1.5px solid #e2e8f0'}>
          {year}
          <span class="opacity-60 text-[0.65rem]"> ({notices.filter(n => getYear(n.date) === year).length})</span>
        </button>
      {/each}
    </div>
  </div>

  {#if loading}
    <div class="bg-white border border-tgpc-gray-border rounded-2xl p-5 shadow-sm space-y-3">
      <Skeleton height="1rem" width="25%" />
      <Skeleton height="3rem" />
      <Skeleton height="3rem" />
      <Skeleton height="3rem" />
      <Skeleton height="3rem" />
    </div>
  {:else if filtered.length === 0}
    <EmptyState message="No notices match your search" />
  {:else}
    <div class="bg-white border border-tgpc-gray-border rounded-2xl shadow-sm overflow-hidden" style="max-height:calc(100vh - 275px);overflow-y:auto">
      <table class="w-full text-[0.9rem] hidden md:table border-separate border-spacing-0">
        <thead class="sticky top-0 z-10">
          <tr class="text-[0.7rem] uppercase font-bold tracking-wider text-tgpc-gray-muted">
            <th class="text-left py-3 px-4 bg-white" scope="col">Date</th>
            <th class="text-left py-3 px-4 bg-white" scope="col">Title / Description</th>
            <th class="text-left py-3 px-4 bg-white" scope="col">Links</th>
          </tr>
        </thead>
        <tbody class="stagger">
          {#if activeTab === null}
            {#each years as year}
              {@const fy = filtered.filter(n => getYear(n.date) === year)}
              {#if fy.length > 0}
                <tr class="bg-tgpc-bg/50">
                  <td colspan="3" class="py-2.5 px-4 text-[0.7rem] font-bold uppercase tracking-widest text-tgpc-gray-muted">{year} &mdash; {fy.length}</td>
                </tr>
                {#each fy as n}
                  <tr class="border-t border-tgpc-table-border transition-colors hover:bg-[#00cc66]/[0.03]">
                    <td class="py-3 px-4 whitespace-nowrap font-semibold text-tgpc-text-secondary tabular-nums">{fmtDate(n.date)}</td>
                    <td class="py-3 px-4">{n.title}</td>
                    <td class="py-3 px-4 whitespace-nowrap space-x-1.5">
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
              <tr class="border-t border-tgpc-table-border transition-colors hover:bg-[#00cc66]/[0.03]">
                <td class="py-3 px-4 whitespace-nowrap font-semibold text-tgpc-text-secondary tabular-nums">{fmtDate(n.date)}</td>
                <td class="py-3 px-4">{n.title}</td>
                <td class="py-3 px-4 whitespace-nowrap space-x-1.5">
                  {#each n.links || [] as link}
                    <LinkBadge url={resolveUrl(link.url)} label={link.label} cls={linkClass(link.url)} />
                  {/each}
                </td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>

      <div class="md:hidden space-y-2 p-3 stagger">
        {#if activeTab === null}
          {#each years as year}
            {@const fy = filtered.filter(n => getYear(n.date) === year)}
            {#if fy.length > 0}
              <div class="text-[0.7rem] font-bold uppercase tracking-widest text-tgpc-gray-muted py-2 px-1">{year} &mdash; {fy.length}</div>
              {#each fy as n}
                <article class="card-hover bg-white border border-tgpc-gray-border rounded-2xl p-4">
                  <div class="flex flex-col gap-0.5">
                    <span class="text-[0.6rem] uppercase font-bold tracking-wider text-tgpc-gray-muted">Date</span>
                    <span class="text-[0.9rem] font-medium tabular-nums">{fmtDate(n.date)}</span>
                  </div>
                  <div class="flex flex-col gap-0.5 mt-2">
                    <span class="text-[0.6rem] uppercase font-bold tracking-wider text-tgpc-gray-muted">Title</span>
                    <span class="text-[0.9rem]">{n.title}</span>
                  </div>
                  {#if n.links?.length}
                    <div class="flex flex-col gap-0.5 mt-2">
                      <span class="text-[0.6rem] uppercase font-bold tracking-wider text-tgpc-gray-muted">Links</span>
                      <div class="flex gap-1.5 flex-wrap">
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
            <article class="card-hover bg-white border border-tgpc-gray-border rounded-2xl p-4">
              <div class="flex flex-col gap-0.5">
                <span class="text-[0.6rem] uppercase font-bold tracking-wider text-tgpc-gray-muted">Date</span>
                <span class="text-[0.9rem] font-medium tabular-nums">{fmtDate(n.date)}</span>
              </div>
              <div class="flex flex-col gap-0.5 mt-2">
                <span class="text-[0.6rem] uppercase font-bold tracking-wider text-tgpc-gray-muted">Title</span>
                <span class="text-[0.9rem]">{n.title}</span>
              </div>
              {#if n.links?.length}
                <div class="flex flex-col gap-0.5 mt-2">
                  <span class="text-[0.6rem] uppercase font-bold tracking-wider text-tgpc-gray-muted">Links</span>
                  <div class="flex gap-1.5 flex-wrap">
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
