<script lang="ts">
	let { value, maxHeight = '24rem' }: { value: unknown; maxHeight?: string } = $props();
</script>

<pre
	class="overflow-auto rounded bg-slate-900 p-3 text-xs leading-relaxed text-slate-100"
	style="max-height: {maxHeight}">{JSON.stringify(value, null, 2)}</pre>
