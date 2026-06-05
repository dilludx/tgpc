<script lang="ts">
  let { message = 'No results' }: { message?: string } = $props();
</script>

<div class="text-center py-8 text-tgpc-gray-muted text-[0.875rem]" role="status">
  <p>{message}</p>
</div>
