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
  <div class="flex items-center justify-between pt-4 mt-2 border-t border-tgpc-gray-border">
    <span class="text-[0.85rem] text-tgpc-text-secondary font-medium tabular-nums">{start}–{end} of {total}</span>
    <div class="flex items-center gap-1.5">
      <button onclick={onPrev} disabled={page <= 1}
        class="px-4 py-2 rounded-xl text-[0.85rem] font-semibold transition-all cursor-pointer border-2 border-tgpc-gray-border disabled:opacity-30 disabled:cursor-not-allowed active:scale-95 bg-white"
        style="color:var(--color-tgpc-text)"
        aria-label="Previous page">
        &larr; Prev
      </button>
      <span class="px-3 py-1 text-[0.85rem] font-semibold text-tgpc-text-secondary tabular-nums" role="status" aria-live="polite">{page} / {totalPages}</span>
      <button onclick={onNext} disabled={page >= totalPages}
        class="px-4 py-2 rounded-xl text-[0.85rem] font-semibold transition-all cursor-pointer border-2 border-tgpc-gray-border disabled:opacity-30 disabled:cursor-not-allowed active:scale-95 bg-white"
        style="color:var(--color-tgpc-text)"
        aria-label="Next page">
        Next &rarr;
      </button>
    </div>
  </div>
{/if}
