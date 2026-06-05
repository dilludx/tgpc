<script lang="ts">
  import Clock from './Clock.svelte';

  let { now }: { now: Date } = $props();
</script>

<div class="flex items-center gap-2 text-[0.75rem] text-tgpc-gray-muted flex-wrap">
  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-[10px] text-[0.7rem] font-semibold"
        style="background:linear-gradient(135deg,#00cc66,#00cc6640);color:#fff">
    ✓ Synced
  </span>
  <span style="background:linear-gradient(135deg,#7c3aed,#2563eb);-webkit-background-clip:text;-webkit-text-fill-color:transparent">
    <Clock {now} />
  </span>
  <span>|</span>
  <a href="/notice" class="text-tgpc-purple no-underline hover:underline font-medium">NOTICES</a>
  <a href="/dispatch" class="text-tgpc-red no-underline hover:underline font-medium"
     style="animation:pulse-border 2s ease-in-out infinite">DISPATCH</a>
  <span>|</span>
  <span class="text-tgpc-gray-muted">Unofficial data | Not for legal use</span>
</div>
