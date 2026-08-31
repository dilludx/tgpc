<script lang="ts">
  import { R2_DISPATCH } from '$lib/r2';
  let { data } = $props();
</script>

<svelte:head>
  <title>{data.name} — TGPC Dispatch</title>
</svelte:head>

<div class="h-[calc(100vh-4rem)] flex flex-col">
  <div class="flex items-center justify-between gap-2 border-b border-[#e5e7eb] bg-white px-3 py-2">
    <span class="text-sm font-semibold text-[#111827] truncate" title={data.name}>{data.name}</span>
    <a href={`${R2_DISPATCH}/${data.name}`} target="_blank" rel="noopener" class="rounded border border-[#e5e7eb] bg-white px-3 py-1 text-xs font-semibold text-[#2563eb] no-underline hover:bg-[#f9fafb]">Open raw</a>
  </div>
  <iframe title={data.name} src={`${R2_DISPATCH}/${data.name}`} class="flex-1 w-full border-0 bg-white"></iframe>
</div>
