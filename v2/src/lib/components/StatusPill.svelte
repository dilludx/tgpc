<script lang="ts">
  import type { ConnectionStatus } from '$lib/types';

  let { status }: { status: ConnectionStatus } = $props();

  const config: Record<ConnectionStatus, { bg: string; text: string; dot: string; label: string }> = {
    Live: { bg: '#dcfce7', text: '#16a34a', dot: '#00cc66', label: 'Connected to database' },
    Busy: { bg: '#fff7ed', text: '#9a3412', dot: '#f97316', label: 'Checking connection…' },
    Offline: { bg: '#fee2e2', text: '#dc2626', dot: '#ef4444', label: 'Connection lost' }
  };
</script>

<span class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[0.65rem] font-bold uppercase tracking-wider shadow-sm"
      style="background:{config[status].bg};color:{config[status].text}"
      title={config[status].label}>
  <span class="w-2 h-2 rounded-full" style="background:{config[status].dot};box-shadow:0 0 6px {config[status].dot}80;animation:pulse-dot 2s ease-in-out infinite"></span>
  {status}
</span>
