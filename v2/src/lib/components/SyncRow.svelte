<script lang="ts">
  import Clock from './Clock.svelte';

  let { now }: { now: Date } = $props();
</script>

<div class="flex items-center gap-2.5 text-[0.75rem] text-tgpc-gray-muted flex-wrap">
  <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[0.65rem] font-bold uppercase tracking-wide"
        style="background:linear-gradient(135deg,#00cc66,#00cc6680);color:#fff;box-shadow:0 1px 4px #00cc6640">
    ✓ Synced
  </span>
  <span class="font-medium tabular-nums"
        style="background:linear-gradient(135deg,#7c3aed,#2563eb);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
    <Clock {now} />
  </span>
  <span class="w-1 h-1 rounded-full bg-tgpc-gray-border"></span>
  <a href="/notice" class="text-tgpc-purple no-underline hover:underline font-semibold tracking-wide text-[0.7rem]">NOTICES</a>
  <a href="/dispatch" class="text-tgpc-red no-underline hover:underline font-semibold tracking-wide text-[0.7rem]"
     style="animation:pulse-border 2s ease-in-out infinite">DISPATCH</a>
  <span class="w-1 h-1 rounded-full bg-tgpc-gray-border"></span>
  <span class="text-tgpc-gray-muted/60">Unofficial data</span>
</div>
