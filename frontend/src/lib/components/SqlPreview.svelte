<script lang="ts">
	let { value }: { value: string } = $props();
</script>

<div class="space-y-2">
	<p
		class="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900"
	>
		Preview only — OSCAR never executes SQL.
	</p>
	<pre
		class="max-h-96 overflow-auto whitespace-pre-wrap rounded bg-slate-950 p-3 text-sm text-slate-100">{value}</pre>
</div>
