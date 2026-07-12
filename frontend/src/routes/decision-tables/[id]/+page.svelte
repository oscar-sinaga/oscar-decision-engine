<script lang="ts">
	import { page } from '$app/state';
	import { api } from '$lib/api/client';
	import type { ConfigEntity, ConfigVersion, Meta, ReasonCode } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import FeaturePicker from '$lib/components/FeaturePicker.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
	import PageHeader from '$lib/ui/PageHeader.svelte';
	import StatusBadge from '$lib/ui/StatusBadge.svelte';
	import { confirmAction } from '$lib/ui/confirm';
	import { toast } from 'svelte-sonner';
	import {
		configToGrid,
		emptyGridRow,
		gridToConfig,
		rowSummary,
		type DecisionTableGridState,
		type GridCell,
		type GridRow
	} from '$lib/decision-table';

	let entity = $state<ConfigEntity | null>(null);
	let meta = $state<Meta | null>(null);
	let reasonCodes = $state<ReasonCode[]>([]);
	let selectedVersionId = $state('');
	let grid = $state<DecisionTableGridState>(configToGrid({ rows: [] }));
	let versionNote = $state('');
	let newColumnPath = $state('');
	let tab = $state<'grid' | 'json'>('grid');
	let error = $state<unknown>(null);
	let notice = $state('');
	let busy = $state(false);

	let selectedVersion = $derived(
		entity?.versions.find((version) => version.id === selectedVersionId) ?? null
	);
	let editable = $derived(selectedVersion?.status === 'DRAFT' && auth.hasPermission('rule.create'));
	let configPreview = $derived(gridToConfig(grid));
	let featureOptions = $derived(meta?.features ?? []);

	function applyVersion(version: ConfigVersion) {
		selectedVersionId = version.id;
		grid = configToGrid(version.config);
		versionNote = version.version_note ?? '';
		notice = '';
	}

	async function load(preferredVersionId?: string) {
		error = null;
		try {
			const [detail, metadata, reasons] = await Promise.all([
				api<ConfigEntity>(`/v1/decision-tables/${page.params.id}`),
				api<Meta>('/v1/meta'),
				api<ReasonCode[]>('/v1/reason-codes')
			]);
			entity = detail;
			meta = metadata;
			reasonCodes = reasons.filter((reason) => reason.active);
			const queryVersion = page.url.searchParams.get('version');
			const version =
				detail.versions.find((item) => item.id === preferredVersionId) ??
				detail.versions.find((item) => String(item.version) === queryVersion) ??
				detail.versions.at(-1);
			if (version) applyVersion(version);
		} catch (err) {
			error = err;
		}
	}

	function touch() {
		grid = structuredClone($state.snapshot(grid));
	}

	function feature(path: string) {
		return meta?.features.find((item) => item.path === path);
	}

	function operators(path: string): string[] {
		const type = feature(path)?.data_type;
		return (type && meta?.operators_by_type[type]) || meta?.operators || ['=', '!='];
	}

	function defaultValue(path: string): unknown {
		return feature(path)?.data_type === 'BOOLEAN' ? false : '';
	}

	function addColumn() {
		const path = newColumnPath.trim();
		if (!path || grid.columns.some((column) => column.path === path)) return;
		grid.columns.push({ path });
		for (const row of grid.rows) {
			row.cells[path] = {
				active: false,
				operator: operators(path)[0] ?? '=',
				value: defaultValue(path)
			};
		}
		newColumnPath = '';
		touch();
	}

	function removeColumn(path: string) {
		grid.columns = grid.columns.filter((column) => column.path !== path);
		for (const row of grid.rows) delete row.cells[path];
		touch();
	}

	function moveColumn(index: number, delta: number) {
		const target = index + delta;
		if (target < 0 || target >= grid.columns.length) return;
		[grid.columns[index], grid.columns[target]] = [grid.columns[target], grid.columns[index]];
		touch();
	}

	function addRow(after = grid.rows.length - 1) {
		grid.rows.splice(after + 1, 0, emptyGridRow(grid.columns, grid.rows.length + 1));
		touch();
	}

	function duplicateRow(index: number) {
		const copy = structuredClone($state.snapshot(grid.rows[index]));
		copy.key = `${copy.key}-copy-${Date.now()}`;
		grid.rows.splice(index + 1, 0, copy);
		touch();
	}

	function deleteRow(index: number) {
		if (grid.rows.length === 1) return;
		grid.rows.splice(index, 1);
		touch();
	}

	function moveRow(index: number, delta: number) {
		const target = index + delta;
		if (target < 0 || target >= grid.rows.length) return;
		[grid.rows[index], grid.rows[target]] = [grid.rows[target], grid.rows[index]];
		touch();
	}

	function setCellActive(cell: GridCell, active: boolean, path: string) {
		cell.active = active;
		if (active && cell.value === undefined) cell.value = defaultValue(path);
		touch();
	}

	function setCellValue(row: GridRow, path: string, raw: string) {
		const cell = row.cells[path];
		const dataType = feature(path)?.data_type;
		if (cell.operator === 'in' || cell.operator === 'not_in') {
			cell.value = raw
				.split(',')
				.map((item) => item.trim())
				.filter(Boolean)
				.map((item) => (dataType === 'NUMBER' ? Number(item) : item));
		} else if (dataType === 'NUMBER') {
			cell.value = raw === '' ? '' : Number(raw);
		} else {
			cell.value = raw;
		}
		touch();
	}

	function cellText(cell: GridCell): string {
		return Array.isArray(cell.value) ? cell.value.join(', ') : String(cell.value ?? '');
	}

	function warningForRow(index: number): boolean {
		return Boolean(
			selectedVersion?.warnings.some(
				(warning) => warning.warning === 'OVERLAPPING_ROWS' && warning.rows?.includes(index)
			)
		);
	}

	async function save() {
		if (!selectedVersion || !editable) return;
		busy = true;
		error = null;
		notice = '';
		try {
			await api<ConfigVersion>(
				`/v1/decision-tables/${page.params.id}/versions/${selectedVersion.id}`,
				{ method: 'PUT', body: { config: configPreview, version_note: versionNote } }
			);
			await load(selectedVersion.id);
			notice = 'Draft saved. Overlap warnings have been refreshed.';
			toast.success('Decision table draft saved');
		} catch (err) {
			error = err;
		} finally {
			busy = false;
		}
	}

	async function submitApproval() {
		if (!selectedVersion) return;
		busy = true;
		try {
			await api<ConfigVersion>(
				`/v1/decision-tables/${page.params.id}/versions/${selectedVersion.id}/submit-approval`,
				{ method: 'POST' }
			);
			await load(selectedVersion.id);
			notice = 'Version submitted for approval.';
			toast.success('Decision table submitted for approval');
		} catch (err) {
			error = err;
		} finally {
			busy = false;
		}
	}

	async function activate() {
		if (!selectedVersion) return;
		const confirmation = await confirmAction({
			title: 'Activate decision table version?',
			body: 'This version will become available to active strategies.',
			confirmLabel: 'Activate',
			requireReason: true
		});
		if (!confirmation.ok) return;
		busy = true;
		try {
			await api<ConfigVersion>(
				`/v1/decision-tables/${page.params.id}/versions/${selectedVersion.id}/activate`,
				{ body: { reason: confirmation.reason ?? '' } }
			);
			await load(selectedVersion.id);
			notice = 'Version activated.';
			toast.success('Decision table activated');
		} catch (err) {
			error = err;
			toast.error('Could not activate decision table');
		} finally {
			busy = false;
		}
	}

	async function createDraft() {
		busy = true;
		try {
			const created = await api<ConfigVersion>(`/v1/decision-tables/${page.params.id}/versions`, {
				body: { config: configPreview, version_note: 'Draft copied from selected version' }
			});
			await load(created.id);
			notice = `Draft v${created.version} created.`;
			toast.success(`Draft v${created.version} created`);
		} catch (err) {
			error = err;
		} finally {
			busy = false;
		}
	}

	$effect(() => {
		load();
	});
</script>

{#if error}<div class="mb-4"><ErrorNote {error} /></div>{/if}

{#if entity && selectedVersion}
	<PageHeader
		title={entity.code}
		description={`${entity.name} · ${entity.description || 'No description'}`}
	>
		{#snippet actions()}
			<div class="flex flex-wrap items-center gap-2">
				<StatusBadge value={selectedVersion.status} />
				<label class="sr-only" for="decision-table-version">Version</label>
				<select
					id="decision-table-version"
					class="h-9 rounded-control border border-border bg-surface px-3 text-xs text-text shadow-card"
					bind:value={selectedVersionId}
					onchange={() => {
						const version = entity?.versions.find((item) => item.id === selectedVersionId);
						if (version) applyVersion(version);
					}}
				>
					{#each entity?.versions ?? [] as version (version.id)}<option value={version.id}
							>v{version.version} · {version.status}</option
						>{/each}
				</select>
			</div>
		{/snippet}
	</PageHeader>

	{#if notice}<div
			class="mb-4 rounded-card border border-success/20 bg-success-bg px-3 py-2 text-xs text-success"
		>
			{notice}
		</div>{/if}

	<div
		class="sticky top-14 z-30 mb-4 flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface/95 p-2 shadow-card backdrop-blur"
	>
		<div class="flex items-center gap-1" role="tablist" aria-label="Decision table view">
			<button
				class="rounded-control px-3 py-2 text-xs font-semibold {tab === 'grid'
					? 'bg-primary-50 text-primary-700'
					: 'text-text-muted hover:bg-surface-muted'}"
				onclick={() => (tab = 'grid')}>Grid</button
			>
			<button
				class="rounded-control px-3 py-2 text-xs font-semibold {tab === 'json'
					? 'bg-primary-50 text-primary-700'
					: 'text-text-muted hover:bg-surface-muted'}"
				onclick={() => (tab = 'json')}>Advanced JSON</button
			>
		</div>
		<div class="flex flex-wrap items-center gap-2">
			{#if tab === 'grid' && editable}<button
					class="rounded-control border border-border bg-surface px-3 py-2 text-xs font-semibold text-text hover:bg-surface-muted"
					onclick={() => addRow()}>Add row</button
				>{/if}
			{#if editable}
				<button
					class="rounded-control bg-primary-600 px-3 py-2 text-xs font-semibold text-white hover:bg-primary-700 disabled:opacity-50"
					disabled={busy}
					onclick={save}>Save draft</button
				>
				<button
					class="rounded-control border border-border bg-surface px-3 py-2 text-xs font-semibold text-text hover:bg-surface-muted disabled:opacity-50"
					disabled={busy}
					onclick={submitApproval}>Submit approval</button
				>
			{:else if selectedVersion.status === 'PENDING_APPROVAL' && auth.hasPermission('rule.approve')}
				<button
					class="rounded-control bg-success px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
					disabled={busy}
					onclick={activate}>Activate</button
				>
			{:else if !entity.versions.some((version) => version.status === 'DRAFT' || version.status === 'PENDING_APPROVAL') && auth.hasPermission('rule.create')}
				<button
					class="rounded-control bg-primary-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
					disabled={busy}
					onclick={createDraft}>New draft from version</button
				>
			{/if}
		</div>
	</div>

	{#if tab === 'json'}
		<section class="rounded-card border border-border bg-surface p-4 shadow-card">
			<h2 class="mb-3 text-sm font-semibold text-text">Generated configuration</h2>
			<JsonBlock value={configPreview} maxHeight="42rem" />
		</section>
	{:else}
		<div class="space-y-4">
			<section class="rounded-card border border-border bg-surface p-4 shadow-card">
				<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
					<label class="text-xs font-medium text-text-muted"
						>Hit policy<select
							class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-xs text-text"
							bind:value={grid.hitPolicy}
							disabled={!editable}
							onchange={touch}
							><option value="FIRST_MATCH">FIRST MATCH</option><option value="PRIORITY"
								>PRIORITY</option
							></select
						></label
					>
					<label class="text-xs font-medium text-text-muted"
						>No-match decision<select
							class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-xs text-text"
							bind:value={grid.noMatchDecision}
							disabled={!editable}
							onchange={touch}
							>{#each meta?.decisions ?? [] as decision (decision)}<option value={decision}
									>{decision}</option
								>{/each}</select
						></label
					>
					<label class="text-xs font-medium text-text-muted"
						>No-match reason<select
							class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-xs text-text"
							bind:value={grid.noMatchReasonCode}
							disabled={!editable}
							onchange={touch}
							><option value="">None</option>{#each reasonCodes as reason (reason.id)}<option
									value={reason.code}>{reason.code}</option
								>{/each}</select
						></label
					>
					<label class="text-xs font-medium text-text-muted"
						>Above-limit reason<select
							class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-xs text-text"
							bind:value={grid.aboveLimitReasonCode}
							disabled={!editable}
							onchange={touch}
							><option value="">None</option>{#each reasonCodes as reason (reason.id)}<option
									value={reason.code}>{reason.code}</option
								>{/each}</select
						></label
					>
					<label class="text-xs font-medium text-text-muted"
						>Version note<input
							class="mt-1 h-9 w-full rounded-control border border-border bg-surface px-2 text-xs text-text"
							bind:value={versionNote}
							disabled={!editable}
						/></label
					>
				</div>
			</section>
			{#if selectedVersion.warnings.length}<div
					class="rounded-card border border-warning/25 bg-warning-bg px-4 py-3 text-xs text-warning"
					role="status"
				>
					<strong>Overlap warning.</strong>
					{selectedVersion.warnings.length} row pair(s) may match the same input; the selected hit policy
					determines the winner.
				</div>{/if}
			<section class="rounded-card border border-border bg-surface p-3 shadow-card">
				<div class="flex flex-wrap items-end gap-2">
					<div class="min-w-64 flex-1">
						<FeaturePicker features={featureOptions} bind:value={newColumnPath} />
					</div>
					<button
						class="h-9 rounded-control border border-border bg-surface px-3 text-xs font-semibold text-text hover:bg-surface-muted disabled:opacity-50"
						disabled={!editable || !newColumnPath}
						onclick={addColumn}>Add condition column</button
					><span class="pb-2 text-[11px] text-text-muted">Blank cells use wildcard ∗.</span>
				</div>
			</section>
			<div
				class="max-h-[calc(100vh-22rem)] min-h-[28rem] overflow-auto rounded-card border border-border bg-surface shadow-card"
			>
				<table
					class="min-w-max border-separate border-spacing-0 text-xs"
					data-testid="decision-table-grid"
				>
					<thead class="sticky top-0 z-20 bg-surface-sunken text-left text-text-muted"
						><tr
							><th
								scope="col"
								class="sticky left-0 z-30 w-20 border-b border-r border-border bg-surface-sunken px-2 py-2"
								>Row</th
							>{#if grid.hitPolicy === 'PRIORITY'}<th
									scope="col"
									class="w-20 border-b border-r border-border px-2 py-2">Priority</th
								>{/if}
							{#each grid.columns as column, columnIndex (column.path)}<th
									scope="col"
									class="min-w-64 border-b border-r border-border px-2 py-2"
									><div class="flex items-center justify-between gap-2">
										<span class="font-mono text-[11px] text-text">{column.path}</span
										>{#if editable}<span class="flex gap-1"
												><button
													aria-label={`Move ${column.path} left`}
													onclick={() => moveColumn(columnIndex, -1)}>←</button
												><button
													aria-label={`Move ${column.path} right`}
													onclick={() => moveColumn(columnIndex, 1)}>→</button
												><button
													class="text-danger"
													aria-label={`Remove ${column.path}`}
													onclick={() => removeColumn(column.path)}>×</button
												></span
											>{/if}
									</div>
									<span class="mt-1 block text-[10px] font-normal text-text-faint"
										>{feature(column.path)?.data_type ?? 'UNKNOWN'}</span
									></th
								>{/each}
							{#each ['Decision', 'Risk grade', 'Approved limit', 'Tenor', 'Pricing rate', 'Reason code', 'Actions'] as heading (heading)}<th
									scope="col"
									class="min-w-36 border-b border-r border-border px-2 py-2">{heading}</th
								>{/each}</tr
						></thead
					>
					<tbody
						>{#each grid.rows as row, rowIndex (row.key)}<tr
								class={warningForRow(rowIndex) ? 'bg-warning-bg' : 'bg-surface'}
								title={rowSummary(row, grid.columns)}
							>
								<td
									class="sticky left-0 z-10 h-9 border-b border-r border-border bg-inherit px-2 py-2 align-top font-semibold text-text"
									>#{rowIndex + 1}{#if warningForRow(rowIndex)}<span
											class="mt-1 block rounded-control bg-warning/15 px-1 py-0.5 text-[9px] text-warning"
											>OVERLAP</span
										>{/if}</td
								>
								{#if grid.hitPolicy === 'PRIORITY'}<td
										class="border-b border-r border-border p-2 align-top"
										><input
											class="w-16 rounded-control border border-border bg-surface px-2 py-1"
											type="number"
											bind:value={row.priority}
											disabled={!editable}
											onchange={touch}
										/></td
									>{/if}
								{#each grid.columns as column (column.path)}{@const cell =
										row.cells[column.path]}<td class="border-b border-r border-border p-2 align-top"
										><label class="mb-1 flex items-center gap-1 text-[10px] text-text-muted"
											><input
												type="checkbox"
												checked={cell.active}
												disabled={!editable}
												onchange={(event) =>
													setCellActive(cell, event.currentTarget.checked, column.path)}
											/> condition</label
										>{#if !cell.active}<div
												class="rounded-control bg-surface-sunken py-3 text-center text-lg text-text-faint"
											>
												∗
											</div>{:else}<select
												class="mb-1 block w-full rounded-control border border-border bg-surface px-2 py-1"
												bind:value={cell.operator}
												disabled={!editable}
												onchange={touch}
												>{#each operators(column.path) as operator (operator)}<option
														value={operator}>{operator}</option
													>{/each}</select
											>{#if cell.operator !== 'exists' && cell.operator !== 'is_null'}{#if feature(column.path)?.data_type === 'BOOLEAN'}<select
														class="block w-full rounded-control border border-border bg-surface px-2 py-1"
														value={String(cell.value)}
														disabled={!editable}
														onchange={(event) => {
															cell.value = event.currentTarget.value === 'true';
															touch();
														}}
														><option value="true">true</option><option value="false">false</option
														></select
													>{:else}<input
														class="block w-full rounded-control border border-border bg-surface px-2 py-1"
														type={feature(column.path)?.data_type === 'NUMBER'
															? 'number'
															: feature(column.path)?.data_type === 'DATE'
																? 'date'
																: 'text'}
														value={cellText(cell)}
														placeholder={cell.operator === 'in' || cell.operator === 'not_in'
															? 'comma-separated'
															: 'value'}
														disabled={!editable}
														oninput={(event) =>
															setCellValue(row, column.path, event.currentTarget.value)}
													/>{/if}{/if}{/if}</td
									>{/each}
								<td class="border-b border-r border-border p-2 align-top"
									><select
										class="w-full rounded-control border border-border bg-surface px-2 py-1"
										bind:value={row.output.decision}
										disabled={!editable}
										onchange={touch}
										>{#each meta?.decisions ?? [] as decision (decision)}<option value={decision}
												>{decision}</option
											>{/each}</select
									></td
								>
								<td class="border-b border-r border-border p-2 align-top"
									><input
										class="w-full rounded-control border border-border bg-surface px-2 py-1"
										maxlength="5"
										value={row.output.risk_grade ?? ''}
										disabled={!editable}
										oninput={(event) => {
											row.output.risk_grade = event.currentTarget.value || null;
											touch();
										}}
									/></td
								>
								<td class="min-w-60 border-b border-r border-border p-2 align-top"
									><input
										class="mb-1 w-full rounded-control border border-border bg-surface px-2 py-1"
										type="number"
										value={row.output.approved_limit ?? ''}
										disabled={!editable || Boolean(row.output.approved_limit_pct_of)}
										oninput={(event) => {
											row.output.approved_limit =
												event.currentTarget.value === '' ? null : Number(event.currentTarget.value);
											touch();
										}}
									/><label class="flex items-center gap-1 text-[10px] text-text-muted"
										><input
											type="checkbox"
											checked={Boolean(row.output.approved_limit_pct_of)}
											disabled={!editable}
											onchange={(event) => {
												row.output.approved_limit_pct_of = event.currentTarget.checked
													? { field: 'vehicle.appraisal_value', pct: 0.7 }
													: null;
												row.output.approved_limit = null;
												touch();
											}}
										/> % of field</label
									>{#if row.output.approved_limit_pct_of}<div class="mt-1 flex gap-1">
											<input
												class="min-w-36 flex-1 rounded-control border border-border bg-surface px-2 py-1 text-[10px]"
												list="limit-fields"
												bind:value={row.output.approved_limit_pct_of.field}
												disabled={!editable}
												onchange={touch}
											/><input
												class="w-16 rounded-control border border-border bg-surface px-2 py-1 text-[10px]"
												type="number"
												step="0.01"
												min="0.01"
												max="1"
												bind:value={row.output.approved_limit_pct_of.pct}
												disabled={!editable}
												onchange={touch}
											/>
										</div>{/if}</td
								>
								<td class="border-b border-r border-border p-2 align-top"
									><input
										class="w-full rounded-control border border-border bg-surface px-2 py-1"
										type="number"
										value={row.output.approved_tenor_months ?? ''}
										disabled={!editable}
										oninput={(event) => {
											row.output.approved_tenor_months =
												event.currentTarget.value === '' ? null : Number(event.currentTarget.value);
											touch();
										}}
									/></td
								>
								<td class="border-b border-r border-border p-2 align-top"
									><input
										class="w-full rounded-control border border-border bg-surface px-2 py-1"
										type="number"
										step="0.001"
										value={row.output.pricing_rate ?? ''}
										disabled={!editable}
										oninput={(event) => {
											row.output.pricing_rate =
												event.currentTarget.value === '' ? null : Number(event.currentTarget.value);
											touch();
										}}
									/></td
								>
								<td class="border-b border-r border-border p-2 align-top"
									><select
										class="w-full rounded-control border border-border bg-surface px-2 py-1"
										value={row.output.reason_code ?? ''}
										disabled={!editable}
										onchange={(event) => {
											row.output.reason_code = event.currentTarget.value || null;
											touch();
										}}
										><option value="">None</option>{#each reasonCodes as reason (reason.id)}<option
												value={reason.code}>{reason.code}</option
											>{/each}</select
									></td
								>
								<td class="border-b border-border p-2 align-top"
									>{#if editable}<div class="flex flex-wrap gap-1">
											<button
												class="rounded-control border border-border px-1.5 py-1"
												aria-label={`Move row ${rowIndex + 1} up`}
												onclick={() => moveRow(rowIndex, -1)}>↑</button
											><button
												class="rounded-control border border-border px-1.5 py-1"
												aria-label={`Move row ${rowIndex + 1} down`}
												onclick={() => moveRow(rowIndex, 1)}>↓</button
											><button
												class="rounded-control border border-border px-1.5 py-1"
												onclick={() => duplicateRow(rowIndex)}>Copy</button
											><button
												class="rounded-control border border-danger/25 px-1.5 py-1 text-danger"
												onclick={() => deleteRow(rowIndex)}>Delete</button
											>
										</div>{/if}</td
								>
							</tr>{/each}</tbody
					>
				</table>
			</div>
			<datalist id="limit-fields"
				>{#each featureOptions as item (item.path)}<option value={item.path}>{item.label}</option
					>{/each}</datalist
			>
		</div>
	{/if}
{:else if !error}<p class="text-sm text-text-muted">Loading decision table…</p>{/if}
