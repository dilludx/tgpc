<script lang="ts">
  let { label = 'Loading…' }: { label?: string } = $props();
</script>

<div class="flex flex-col items-center py-8 text-tgpc-gray-muted text-[0.875rem]" role="status" aria-live="polite">
  <div class="w-6 h-6 border-3 border-tgpc-gray-border border-t-tgpc-green rounded-full animate-spin mb-3"></div>
  <p>{label}</p>
</div>
