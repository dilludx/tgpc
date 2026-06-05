<script lang="ts">
  let { class: className = '', width = '100%', height = '1rem' }: {
    class?: string;
    width?: string;
    height?: string;
  } = $props();
</script>

<div class="skeleton {className}" style="width:{width};height:{height}" role="presentation" aria-hidden="true"></div>
