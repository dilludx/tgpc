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
  <div class="flex items-center justify-between pt-3.5 mt-1 border-t border-tgpc-table-border">
    <span class="text-[0.8rem] text-tgpc-text-secondary tabular-nums">{start}–{end} of {total}</span>
    <div class="flex items-center gap-2">
      <button onclick={onPrev} disabled={page <= 1}
        class="px-3 py-1.5 rounded-lg text-[0.8125rem] font-medium transition-all cursor-pointer border-none disabled:opacity-30 disabled:cursor-not-allowed active:scale-95"
        style="background:var(--color-tgpc-bg);color:var(--color-tgpc-text)"
        aria-label="Previous page">
        &larr; Prev
      </button>
      <span class="text-[0.8rem] text-tgpc-text-secondary tabular-nums" role="status" aria-live="polite">{page} / {totalPages}</span>
      <button onclick={onNext} disabled={page >= totalPages}
        class="px-3 py-1.5 rounded-lg text-[0.8125rem] font-medium transition-all cursor-pointer border-none disabled:opacity-30 disabled:cursor-not-allowed active:scale-95"
        style="background:var(--color-tgpc-bg);color:var(--color-tgpc-text)"
        aria-label="Next page">
        Next &rarr;
      </button>
    </div>
  </div>
{/if}
