<script module lang="ts">
	import type { Snippet } from 'svelte';

	export interface Column<R extends Record<string, unknown>> {
		key: keyof R & string;
		header: string;
		sortable?: boolean;
		align?: 'left' | 'right';
		width?: string;
		cell?: Snippet<[R]>;
	}

	export interface EmptyConfig {
		title: string;
		hint?: string;
		actionLabel?: string;
		onAction?: () => void;
	}
</script>

<script lang="ts" generics="T extends Record<string, unknown>">
	import { ChevronDown, ChevronUp, ChevronsUpDown } from '@lucide/svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { cn } from '$lib/utils';
	import EmptyState from './EmptyState.svelte';
	import { nextSortState, sortRows, type SortState } from './datatable-sort';

	let {
		columns,
		rows,
		loading = false,
		empty,
		onRowClick,
		rowKey,
		class: className = ''
	}: {
		columns: Column<T>[];
		rows: T[];
		loading?: boolean;
		empty?: EmptyConfig;
		onRowClick?: (row: T) => void;
		rowKey: keyof T & string;
		class?: string;
	} = $props();

	const skeletonRows = Array.from({ length: 8 }, (_, index) => index);
	let sort = $state<SortState | null>(null);
	const sortedRows = $derived(sortRows(rows, sort));

	function toggle(column: Column<T>): void {
		if (column.sortable) sort = nextSortState(sort, column.key);
	}

	function keyboardRow(event: KeyboardEvent, row: T): void {
		if (onRowClick && (event.key === 'Enter' || event.key === ' ')) {
			event.preventDefault();
			onRowClick(row);
		}
	}
</script>

<div
	class={cn('overflow-hidden rounded-card border border-border bg-surface shadow-card', className)}
>
	<div class="max-w-full overflow-auto">
		<table class="w-full border-collapse text-[12.5px]">
			<thead class="sticky top-0 z-10 bg-surface-sunken">
				<tr>
					{#each columns as column (column.key)}
						<th
							scope="col"
							style:width={column.width}
							class={cn(
								'h-10 border-b border-border px-3 font-semibold text-text-muted',
								column.align === 'right' ? 'text-right' : 'text-left'
							)}
						>
							{#if column.sortable}
								<button
									type="button"
									class="inline-flex items-center gap-1 rounded-control"
									onclick={() => toggle(column)}
								>
									{column.header}
									{#if sort?.key === column.key}
										{#if sort.direction === 'asc'}
											<ChevronUp size={13} />
										{:else}
											<ChevronDown size={13} />
										{/if}
									{:else}
										<ChevronsUpDown size={13} class="text-text-faint" />
									{/if}
								</button>
							{:else}
								{column.header}
							{/if}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody class="divide-y divide-border">
				{#if loading}
					{#each skeletonRows as index (index)}
						<tr>
							{#each columns as column (column.key)}
								<td class="h-10 px-3"><Skeleton class="h-4 w-full" /></td>
							{/each}
						</tr>
					{/each}
				{:else}
					{#each sortedRows as row (String(row[rowKey]))}
						<tr
							class={cn('h-10 transition', onRowClick && 'cursor-pointer hover:bg-surface-muted')}
							tabindex={onRowClick ? 0 : undefined}
							onclick={() => onRowClick?.(row)}
							onkeydown={(event) => keyboardRow(event, row)}
						>
							{#each columns as column (column.key)}
								<td
									class={cn(
										'px-3 text-text',
										column.align === 'right' && 'text-right tabular-nums'
									)}
								>
									{#if column.cell}
										{@render column.cell(row)}
									{:else}
										{String(row[column.key] ?? '—')}
									{/if}
								</td>
							{/each}
						</tr>
					{/each}
				{/if}
			</tbody>
		</table>
	</div>
	{#if !loading && rows.length === 0 && empty}
		<EmptyState {...empty} />
	{/if}
</div>
