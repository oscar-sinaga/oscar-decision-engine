<script lang="ts">
	let { value }: { value: string } = $props();
</script>

<div class="space-y-2">
	<p
		class="rounded border border-warning/30 bg-warning-bg px-3 py-2 text-xs font-semibold text-warning"
	>
		Preview only — OSCAR never executes SQL.
	</p>
	<pre
		class="max-h-96 overflow-auto whitespace-pre-wrap rounded bg-text p-3 text-sm text-surface">{value}</pre>
</div>
