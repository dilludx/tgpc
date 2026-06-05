<script lang="ts">
  let { url, label, cls }: { url: string; label: string; cls: string } = $props();

  const colors: Record<string, { color: string; border: string; hover: string }> = {
    pdf: { color: '#dc2626', border: '#fca5a5', hover: '#fef2f2' },
    image: { color: '#7c3aed', border: '#c4b5fd', hover: '#f5f3ff' },
    ext: { color: '#2563eb', border: '#93c5fd', hover: '#eff6ff' }
  };

  let c = $derived(colors[cls] || colors.ext);
</script>

<a href={url} target="_blank" rel="noopener"
   class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[0.75rem] font-medium no-underline transition-colors hover:(bg-[var(--hover)])"
   style="color:{c.color};border:1px solid {c.border};background:transparent"
   onmouseenter={(e) => e.currentTarget.style.background = c.hover}
   onmouseleave={(e) => e.currentTarget.style.background = 'transparent'}>
  {label}
</a>
