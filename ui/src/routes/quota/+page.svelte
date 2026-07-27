<script lang="ts">
  import type { PageData } from './$types';

  let { data } = $props<{ data: PageData }>();

  let secret = $state('');
  let authed = $state(false);
  let error = $state('');
  let loading = $state(false);
  let report = $state(data.report);

  function barColor(pct: string): string {
    const n = parseFloat(pct);
    if (isNaN(n)) return '#e5e7eb';
    if (n > 90) return '#ef4444';
    if (n > 70) return '#f59e0b';
    return '#00cc66';
  }

  async function login() {
    if (!secret.trim()) return;
    loading = true;
    error = '';
    try {
      const r = await fetch('/api/quota', {
        headers: { 'x-quota-secret': secret.trim() }
      });
      if (r.status === 403) {
        error = 'Wrong password';
        loading = false;
        return;
      }
      if (r.ok) {
        authed = true;
        report = await r.json();
      } else {
        error = 'Server error';
      }
    } catch {
      error = 'Connection error';
    }
    loading = false;
  }
</script>

<svelte:head>
  <title>Quota — TGPC RPh Registry</title>
</svelte:head>

<div class="max-w-2xl mx-auto py-6">
  {#if !authed}
    <h1 class="text-2xl font-bold mb-1">Quota Dashboard</h1>
    <p class="text-xs text-[#9ca3af] mb-6">Enter the admin password to access usage data.</p>
    <form onsubmit={(e) => { e.preventDefault(); login(); }}>
      <div class="flex gap-2 items-center">
        <input
          type="password"
          bind:value={secret}
          placeholder="Password"
          class="border border-[#e5e7eb] rounded px-3 py-1.5 text-sm flex-1 outline-none focus:border-[#00cc66]"
          disabled={loading}
        >
        <button
          type="submit"
          disabled={loading}
          class="bg-[#00cc66] text-white text-sm font-semibold px-4 py-1.5 rounded disabled:opacity-50"
        >{loading ? 'Checking...' : 'Unlock'}</button>
      </div>
      {#if error}
        <p class="text-xs text-[#ef4444] mt-2">{error}</p>
      {/if}
    </form>
  {:else}
    <div class="mb-6">
      <h1 class="text-2xl font-bold mb-1">Free Tier Usage</h1>
      <p class="text-xs text-[#9ca3af]">
        Generated {report ? new Date(report.generated_at).toLocaleString() : '—'}
        &middot; <code class="text-[#00cc66]">make quota</code> for CLI
      </p>
    </div>

    {#if report?.missing_vars?.length}
      <div class="text-xs bg-[#fff3cd] border border-[#ffc107] text-[#856404] rounded px-3 py-2 mb-4">
        <strong>Note:</strong> Some credentials are not configured as Cloudflare Pages environment variables:
        {report.missing_vars.join(', ')}. Set them in the Cloudflare dashboard for live data.
      </div>
    {/if}

    {#each (report?.services ?? []) as service}
      <div class="mb-5 border border-[#e5e7eb] rounded-lg overflow-hidden">
        <div class="bg-[#f8f9fa] px-3 py-2 font-semibold text-sm border-b border-[#e5e7eb]">
          {service.name}
        </div>
        {#if service.error}
          <div class="px-3 py-3 text-xs text-[#ef4444]">{service.error}</div>
        {:else if service.items.length === 0}
          <div class="px-3 py-3 text-xs text-[#9ca3af]">No data available.</div>
        {:else}
          <table class="w-full text-xs">
            <thead>
              <tr class="text-left text-[#9ca3af] border-b border-[#e5e7eb]">
                <th class="px-3 py-1.5 font-medium">Metric</th>
                <th class="px-3 py-1.5 font-medium text-right">Used</th>
                <th class="px-3 py-1.5 font-medium text-right">Limit</th>
                <th class="px-3 py-1.5 font-medium text-center w-28">Usage</th>
              </tr>
            </thead>
            <tbody>
              {#each service.items as item}
                <tr class="border-b border-[#e5e7eb] last:border-b-0">
                  <td class="px-3 py-1.5">{item.label}</td>
                  <td class="px-3 py-1.5 text-right font-mono">{item.used}</td>
                  <td class="px-3 py-1.5 text-right font-mono">{item.limit ?? '—'}</td>
                  <td class="px-3 py-1.5">
                    <div class="flex items-center gap-2">
                      <div class="flex-1 h-1.5 bg-[#e5e7eb] rounded-full overflow-hidden">
                        {#if item.pct !== '-'}
                          <div class="h-full rounded-full transition-all" style="width:{item.pct};background:{barColor(item.pct)}"></div>
                        {/if}
                      </div>
                      <span class="text-[10px] text-[#6b7280] font-mono w-10 text-right">{item.pct === '-' ? '—' : item.pct}</span>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    {/each}
  {/if}
</div>

<style>
  :global(body) { background: white; }
</style>
