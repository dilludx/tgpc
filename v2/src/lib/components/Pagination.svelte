<script lang="ts">
  let { page, totalPages, total, perPage, onPrev, onNext } = $props<{
    page: number;
    totalPages: number;
    total: number;
    perPage: number;
    onPrev: () => void;
    onNext: () => void;
  }>();

  let start = $derived(total === 0 ? 0 : (page - 1) * perPage + 1);
  let end = $derived(Math.min(page * perPage, total));
</script>

{#if total > perPage}
  <div class="flex items-center justify-between pt-3 border-t border-tgpc-table-border text-[0.8rem]">
    <span class="text-tgpc-text-secondary">{start}–{end} of {total}</span>
    <div class="flex items-center gap-3">
      <button onclick={onPrev} disabled={page <= 1}
        class="px-3 py-1.5 rounded-full text-[0.8125rem] font-medium transition-colors cursor-pointer border-none disabled:opacity-40 disabled:cursor-not-allowed"
        style="background:var(--color-tgpc-bg);color:var(--color-tgpc-text)"
        aria-label="Previous page">
        &larr; Prev
      </button>
      <span class="text-tgpc-text-secondary" role="status" aria-live="polite">Page {page} of {totalPages}</span>
      <button onclick={onNext} disabled={page >= totalPages}
        class="px-3 py-1.5 rounded-full text-[0.8125rem] font-medium transition-colors cursor-pointer border-none disabled:opacity-40 disabled:cursor-not-allowed"
        style="background:var(--color-tgpc-bg);color:var(--color-tgpc-text)"
        aria-label="Next page">
        Next &rarr;
      </button>
    </div>
  </div>
{/if}
