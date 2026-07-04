<script lang="ts">
	let {
		page,
		pageSize,
		total,
		onchange
	}: { page: number; pageSize: number; total: number; onchange: (page: number) => void } = $props();

	const pages = $derived(Math.max(1, Math.ceil(total / pageSize)));
</script>

<div class="flex items-center justify-between text-sm text-slate-600">
	<span>{total} records</span>
	<div class="flex items-center gap-2">
		<button
			class="rounded border border-slate-300 px-2 py-1 disabled:opacity-40"
			disabled={page <= 1}
			onclick={() => onchange(page - 1)}>Prev</button
		>
		<span>Page {page} / {pages}</span>
		<button
			class="rounded border border-slate-300 px-2 py-1 disabled:opacity-40"
			disabled={page >= pages}
			onclick={() => onchange(page + 1)}>Next</button
		>
	</div>
</div>
