<script lang="ts">
  import type { DispatchFile } from '$lib/types';
  import { fetchDispatchFiles } from '$lib/api';
  import Skeleton from '$lib/components/Skeleton.svelte';
  import EmptyState from '$lib/components/EmptyState.svelte';

  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const BASE_URL = 'https://pub-4591c8c5282040459ade2ed1e5e3d5be.r2.dev/dispatch';

  let files = $state<DispatchFile[]>([]);
  let years = $state<string[]>([]);
  let sizeMap = $state<Record<string, number>>({});
  let activeTab = $state<string | null>(null);
  let query = $state('');
  let loading = $state(true);

  function parseName(name: string) {
    const m = name.match(/DL(\d{2})(\d{2})(\d{4})[A-Z]*\.pdf/i);
    if (!m) return null;
    return { d: m[1], mo: m[2], y: m[3], date: new Date(+m[3], +m[2] - 1, +m[1]) };
  }

  function fmt(f: { d: string; mo: string; y: string }) {
    return `${f.d} ${MONTHS[+f.mo - 1]} ${f.y}`;
  }

  function formatSize(bytes: number) {
    if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    if (bytes >= 1024) return Math.round(bytes / 1024) + ' KB';
    return bytes + ' B';
  }

  function buildFromRaw(raw: { name: string; size?: number }[]) {
    const sm: Record<string, number> = {};
    raw.forEach(f => { if (f.size) sm[f.name] = f.size; });
    sizeMap = sm;

    const fl: DispatchFile[] = raw
      .map(f => ({ name: f.name, parsed: parseName(f.name), size: f.size }))
      .filter(f => f.parsed)
      .sort((a, b) => b.parsed!.date.getTime() - a.parsed!.date.getTime());

    files = fl;
    years = [...new Set(fl.map(f => f.parsed!.y))].sort((a, b) => +b - +a);
    activeTab = years[0] || null;
  }

  let filtered = $derived.by(() => {
    return files.filter(f => {
      if (!f.parsed) return false;
      if (activeTab && f.parsed.y !== activeTab) return false;
      if (!query) return true;
      const q = query.toLowerCase();
      return f.name.toLowerCase().includes(q) || fmt(f.parsed).toLowerCase().includes(q);
    });
  });

  async function load() {
    loading = true;
    const data = await fetchDispatchFiles();
    buildFromRaw(data);
    loading = false;
  }

  $effect(() => { load(); });
</script>

<div class="space-y-5">
  <div class="bg-white border border-tgpc-gray-border rounded-2xl p-5 shadow-sm">
    <div class="flex items-center justify-between flex-wrap gap-2">
      <h2 class="text-[1.4rem] font-bold tracking-tight">
        <span class="text-tgpc-gray-light">Dispatch Lists</span>
      </h2>
      {#if !loading}
        <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-tgpc-gray-border/50 text-[0.75rem] font-semibold text-tgpc-gray-muted tabular-nums">
          {files.length}
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
        <input type="text" bind:value={query} placeholder="Search files…"
          aria-label="Search dispatch files"
          class="w-full pl-11 pr-4 py-2.5 border-2 border-tgpc-gray-border rounded-2xl text-[0.9rem] bg-white outline-none transition-all max-sm:text-base font-medium"
          onfocus={(e) => { e.currentTarget.style.borderColor = '#00cc66'; e.currentTarget.style.boxShadow = '0 0 0 4px #00cc6620'; }}
          onblur={(e) => { e.currentTarget.style.borderColor = ''; e.currentTarget.style.boxShadow = ''; }} />
      </div>
      {#if query}
        <span class="text-[0.8rem] font-medium text-tgpc-gray-muted tabular-nums">{filtered.length} / {files.length}</span>
      {/if}
    </div>

    <div class="flex gap-1.5 overflow-x-auto pb-0.5" style="scrollbar-width:none" role="tablist" aria-label="Filter by year">
      {#each years as year}
        <button role="tab" aria-selected={year === activeTab} onclick={() => activeTab = year}
          class="flex-shrink-0 px-4 py-2 rounded-xl text-[0.8rem] font-semibold transition-all cursor-pointer border-none active:scale-95"
          style={year === activeTab ? 'background:#00cc66;color:#fff;box-shadow:0 2px 8px #00cc6640' : 'background:white;color:#4a4a5a;border:1.5px solid #e2e8f0'}>
          {year}
          <span class="opacity-60 text-[0.65rem]"> ({files.filter(f => f.parsed?.y === year).length})</span>
        </button>
      {/each}
    </div>
  </div>

  {#if loading}
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
      {#each Array(10) as _}
        <div class="flex items-center gap-3 p-3 border border-tgpc-gray-border rounded-2xl bg-white">
          <Skeleton width="36px" height="44px" />
          <div class="flex-1 space-y-2">
            <Skeleton height="0.9rem" width="80%" />
            <Skeleton height="0.6rem" width="50%" />
          </div>
        </div>
      {/each}
    </div>
  {:else if filtered.length === 0}
    <EmptyState message="No files match your search" />
  {:else}
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
      {#if activeTab === null}
        {#each years as year}
          {@const fy = filtered.filter(f => f.parsed?.y === year)}
          {#if fy.length > 0}
            <div class="col-span-full text-[0.7rem] font-bold uppercase tracking-widest text-tgpc-gray-muted px-1 py-2 border-b border-tgpc-gray-border mb-1">
              {year} &mdash; {fy.length} file{fy.length !== 1 ? 's' : ''}
            </div>
            {#each fy as f}
              <a href={`${BASE_URL}/${f.name}`} target="_blank" rel="noopener"
                class="card-hover flex items-center gap-3 p-3 border border-tgpc-gray-border rounded-2xl no-underline text-tgpc-text bg-white"
                aria-label="Download {fmt(f.parsed!)}">
                <div class="w-9 h-11 flex items-center justify-center flex-shrink-0">
                  <img src="/pdf.png" alt="" width="32" height="32" class="block" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="text-[0.9rem] font-semibold truncate">{fmt(f.parsed!)}</div>
                  <div class="text-[0.65rem] text-tgpc-gray-muted mt-0.5 tabular-nums font-medium">{sizeMap[f.name] ? formatSize(sizeMap[f.name]) : ''}</div>
                </div>
              </a>
            {/each}
          {/if}
        {/each}
      {:else}
        {#each filtered as f}
          <a href={`${BASE_URL}/${f.name}`} target="_blank" rel="noopener"
            class="card-hover flex items-center gap-3 p-3 border border-tgpc-gray-border rounded-2xl no-underline text-tgpc-text bg-white"
            aria-label="Download {fmt(f.parsed!)}">
            <div class="w-9 h-11 flex items-center justify-center flex-shrink-0">
              <img src="/pdf.png" alt="" width="32" height="32" class="block" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-[0.9rem] font-semibold truncate">{fmt(f.parsed!)}</div>
              <div class="text-[0.65rem] text-tgpc-gray-muted mt-0.5 tabular-nums font-medium">{sizeMap[f.name] ? formatSize(sizeMap[f.name]) : ''}</div>
            </div>
          </a>
        {/each}
      {/if}
    </div>
  {/if}
</div>
