<script lang="ts">
	let { value, maxHeight = '24rem' }: { value: unknown; maxHeight?: string } = $props();
</script>

<pre
	class="overflow-auto rounded-card bg-text p-3 font-mono text-xs leading-relaxed text-surface"
	style:max-height={maxHeight}>{JSON.stringify(value, null, 2)}</pre>
