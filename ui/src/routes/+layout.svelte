<svelte:head>
  <title>TGPC RPh Registry</title>
</svelte:head>

<script lang="ts">
  import '../app.css';
  import type { ConnectionStatus, Stats } from '$lib/types';
  import { getStats } from '$lib/api';
  import { supabase } from '$lib/supabase';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { beforeNavigate } from '$app/navigation';
  import { page } from '$app/stores';
  import type { LayoutProps } from './$types';
  import { CATEGORY_COLORS, CATEGORIES, CATEGORY_KEYS } from '$lib/colors';

  import Clock from '$lib/components/Clock.svelte';

  let { children, data } = $props();
  let { stats: ssrStats, lastSync: ssrSync } = data;

  let status = $state<ConnectionStatus>(ssrStats ? 'Live' : 'Busy');
  let stats = $state<Stats | null>(ssrStats);
  let lastSync = $state<string>(ssrSync);

  let navigated = $state(false);

  beforeNavigate(() => {
    navigated = true;
  });

  const publicRoutes = ['/', '/admin'];

  onMount(() => {
    if (!navigated && !publicRoutes.includes($page.url.pathname)) {
      goto('/');
    }
  });

  function cachedOrNull<T>(key: string): T | null {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return null;
      const { data, expiry } = JSON.parse(raw);
      if (Date.now() > expiry) { localStorage.removeItem(key); return null; }
      return data as T;
    } catch { return null; }
  }

  function setCache<T>(key: string, data: T, ttl = 300_000) {
    try { localStorage.setItem(key, JSON.stringify({ data, expiry: Date.now() + ttl })); } catch {}
  }

  async function loadStats() {
    status = 'Busy';
    const data = await getStats();
    if (data) {
      stats = data;
      status = 'Live';
      setCache('tgpc_stats', data);
    } else if (!ssrStats) {
      status = 'Offline';
    }
  }

  async function loadLastSync() {
    try {
      const { data, error } = await supabase
        .from('metadata')
        .select('value')
        .eq('key', 'last_sync')
        .single();
      if (!error && data?.value) {
        const d = new Date(data.value);
        const s = d.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', weekday: 'short', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
        lastSync = s.toUpperCase().replace(/,/g, '');
        setCache('tgpc_last_sync', lastSync);
      }
    } catch {}
  }

  $effect(() => {
    loadStats();
    loadLastSync();
    const channel = supabase
      .channel('metadata-changes')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'metadata', filter: `key=eq.last_sync` }, () => { loadStats(); loadLastSync(); })
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  });

  let statusConfig = $derived.by(() => ({
    Live: { bg: 'rgba(34,197,94,0.05)', border: '#86efac', text: '#166534', dot: '#22c55e' },
    Busy: { bg: 'rgba(239,68,68,0.05)', border: '#fca5a5', text: '#991b1b', dot: '#ef4444' },
    Offline: { bg: 'rgba(239,68,68,0.05)', border: '#fca5a5', text: '#991b1b', dot: '#ef4444' }
  })[status]);

  function val(key: keyof Stats): string {
    return stats ? stats[key].toLocaleString() : '0';
  }

  let sortedCategories = $derived.by(() => {
    if (!stats) return CATEGORIES;
    const s = stats;
    return [...CATEGORIES].sort((a, b) => {
      const ka = CATEGORY_KEYS[CATEGORIES.indexOf(a)] as keyof Stats;
      const kb = CATEGORY_KEYS[CATEGORIES.indexOf(b)] as keyof Stats;
      return (s[kb] ?? 0) - (s[ka] ?? 0);
    });
  });

  let activeTab = $derived($page.url.pathname === '/' ? 'search' : $page.url.pathname === '/notice' ? 'notice' : $page.url.pathname === '/dispatch' ? 'dispatch' : '');

  let searchRef: HTMLAnchorElement | undefined;
  let noticeRef: HTMLAnchorElement | undefined;
  let dispatchRef: HTMLAnchorElement | undefined;
  let sliderStyle = $state('');

  $effect(() => {
    const tab = activeTab;
    if (!tab) { sliderStyle = ''; return; }
    let el = tab === 'search' ? searchRef : tab === 'notice' ? noticeRef : dispatchRef;
    if (el) {
      sliderStyle = `transform:translateX(${el.offsetLeft}px);width:${el.offsetWidth}px`;
    }
  });
</script>
<div class="min-h-screen flex flex-col bg-white">
  <header class="sticky top-0 z-50 bg-white">
    <div class="w-full px-4 sm:px-6 py-2.5 flex items-center justify-between gap-4">
      <div class="flex flex-col">
          <div style="display:table;width:0">
            <a href="/" class="no-underline" style="display:table-row;white-space:nowrap;width:1px">
              <span class="text-[1.4rem] font-bold tracking-tight inline-flex items-center gap-1" style="color:#111;white-space:nowrap">
                <span style="color:#00cc66">TGPC</span><span style="color:#ef4444">RPh</span><span class="text-[#9ca3af]">Registry</span>
              </span>
            </a>
            <span class="text-[0.65rem] text-[#9ca3af] font-medium truncate mb-0.5" style="display:table-row;overflow:hidden">Open-Source TGPC Pharmacist Data</span>
            <div style="display:table-row;overflow:hidden">
              <div class="flex items-center gap-2 text-[0.7rem]">
                <span class="flex w-full items-center justify-center gap-px h-5 px-1.5 rounded-full text-[0.75rem] font-medium box-border overflow-hidden"
                      style="background:{statusConfig.bg};border:1px solid {statusConfig.border};color:{statusConfig.text}">
                  <span class="w-1.5 h-1.5 rounded-full flex-shrink-0" style="background:{statusConfig.dot}"></span>
                  <span class="text-[10px] font-medium leading-[18px] inline-block w-[28px] text-center">{status}</span>
                  {#if status !== 'Offline'}
                  <Clock/>
                  {/if}
                </span>
              </div>
            </div>
          </div>
      </div>
      <div style="background:#f8f9fa;border:1px solid #e5e7eb;border-radius:8px;padding:6px 10px 4px 10px;display:flex;flex-direction:column;gap:0;flex-shrink:0">
        <div style="display:flex;gap:10px;align-items:center;justify-content:center">
          <div style="border-right:1px solid #e5e7eb;padding-right:12px">
              <div style="display:flex;flex-direction:column;gap:4px;text-align:center">
              <div style="font-size:0.8rem;font-weight:500;letter-spacing:0.5px;color:#ef4444">RPh</div>
              <div style="font-size:1.25rem;font-weight:700;color:#1a1a1a;line-height:1;font-variant-numeric:tabular-nums">{val('total')}</div>
            </div>
          </div>
          {#each sortedCategories as cat, i}
            <div style="border-right:{i < 5 ? '1px solid #e5e7eb' : 'none'};padding-right:{i < 5 ? '12px' : '0'}">
              <div style="display:flex;flex-direction:column;gap:4px;text-align:center">
                <div style="font-size:0.8rem;font-weight:500;letter-spacing:0.5px;color:{CATEGORY_COLORS[cat]}">{cat}</div>
                <div style="font-size:1.25rem;font-weight:700;color:#1a1a1a;line-height:1;font-variant-numeric:tabular-nums">{val(CATEGORY_KEYS[CATEGORIES.indexOf(cat)] as keyof Stats)}</div>
              </div>
            </div>
          {/each}
        </div>
             <div style="font-size:0.5rem;color:#a1a1aa;font-weight:500;letter-spacing:0.3px;text-transform:uppercase;margin-top:4px;padding-top:4px;border-top:1px solid #e5e7eb;display:flex;align-items:center;gap:6px;flex-wrap:wrap">
          <span style="display:inline-flex;align-items:center;gap:3px;background:rgba(0,204,102,0.1);padding:1px 6px 1px 4px;border-radius:10px">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:10px;height:10px;background:#00cc66;border-radius:50%;color:white;font-size:6px;font-weight:bold">&#10003;</span>
            <span style="color:#00cc66;font-size:0.45rem;font-weight:600;text-transform:uppercase;letter-spacing:0.3px">Synced</span>
          </span>
          <span style="background:linear-gradient(135deg,#2563eb 0%,#7c3aed 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">{lastSync || '—'}</span>
          <span style="opacity:0.4">|</span>
          <span>Active: <span style="color:#00cc66;font-weight:600">{val('active')}</span></span>
          <span style="opacity:0.4">|</span>
          <span>Inactive: <span style="color:#ef4444;font-weight:600">{val('inactive')}</span></span>
          <span style="opacity:0.4">|</span>
          <span style="color:#9ca3af">Unofficial data — Not for legal use</span>
        </div>
      </div>
    </div>
    <div class="w-full px-4 sm:px-6 border-b border-[#e5e7eb]" style="display:flex;align-items:center;gap:2px;font-size:0.7rem;padding-top:3px;padding-bottom:3px;overflow-x:auto;position:relative">
      <a href="/" bind:this={searchRef} style="text-decoration:none;padding:2px 4px;font-weight:700;color:{activeTab === 'search' ? '#00cc66' : '#6b7280'};white-space:nowrap">SEARCH</a>
      <span style="color:#d1d5db;font-weight:300;padding:0 2px;user-select:none">/</span>
      <a href="/notice" bind:this={noticeRef} style="text-decoration:none;padding:2px 4px;font-weight:700;color:{activeTab === 'notice' ? '#00cc66' : '#6b7280'};white-space:nowrap">NOTICES</a>
      <span style="color:#d1d5db;font-weight:300;padding:0 2px;user-select:none">/</span>
      <a href="/dispatch" bind:this={dispatchRef} style="text-decoration:none;padding:2px 4px;font-weight:700;color:{activeTab === 'dispatch' ? '#00cc66' : '#6b7280'};white-space:nowrap">DISPATCH LIST</a>
      {#if sliderStyle}
      <div style="position:absolute;bottom:0;left:0;height:2px;background:#00cc66;border-radius:1px;transition:transform 0.25s ease-out,width 0.25s ease-out;will-change:transform,width;{sliderStyle}"></div>
      {/if}
    </div>
  </header>

  <main class="flex-1 w-full px-4 sm:px-6 pt-1 pb-14">
    {@render children()}
  </main>

  <footer class="fixed bottom-0 w-full bg-white border-t border-[#e5e7eb] py-1 text-[0.5rem] text-[#9ca3af] leading-tight"
          style="padding-bottom:calc(0.25rem + env(safe-area-inset-bottom, 0px))">
    <div class="w-full px-4 sm:px-6 flex items-center justify-between gap-4">
      <span class="text-left flex-1 pr-4" style="text-wrap:balance"><span style="color:#ef4444">DISCLAIMER:</span> This is an unofficial, third-party tool not affiliated with TGPC or any government body. Data is for reference only — verify all information from official sources before use. Users assume all risk.<br>No warranty as to accuracy, completeness, or timeliness. No liability for errors, omissions, or actions taken based on this content. Operated under fair dealing (Indian Copyright Act, 1957, Section 52).</span>
      <span class="text-right whitespace-nowrap font-semibold flex-shrink-0 text-[0.7rem]">TGPC RPh Registry &copy; {new Date().getFullYear()}</span>
    </div>
  </footer>
</div>

<style>
</style>
