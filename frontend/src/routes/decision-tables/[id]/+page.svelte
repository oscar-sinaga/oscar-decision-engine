<script lang="ts">
	import { page } from '$app/state';
	import { api } from '$lib/api/client';
	import type { ConfigEntity, ConfigVersion, Meta, ReasonCode } from '$lib/api/types';
	import { auth } from '$lib/auth.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import Card from '$lib/components/Card.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';
	import FeaturePicker from '$lib/components/FeaturePicker.svelte';
	import JsonBlock from '$lib/components/JsonBlock.svelte';
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
		grid = structuredClone(grid);
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
		const copy = structuredClone(grid.rows[index]);
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
		} catch (err) {
			error = err;
		} finally {
			busy = false;
		}
	}

	async function activate() {
		if (!selectedVersion) return;
		const reason = window.prompt('Approval reason', 'Reviewed decision-table grid') ?? '';
		busy = true;
		try {
			await api<ConfigVersion>(
				`/v1/decision-tables/${page.params.id}/versions/${selectedVersion.id}/activate`,
				{ body: { reason } }
			);
			await load(selectedVersion.id);
			notice = 'Version activated.';
		} catch (err) {
			error = err;
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
{#if notice}<div
		class="mb-4 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
	>
		{notice}
	</div>{/if}

{#if entity && selectedVersion}
	<div class="mb-4 flex flex-wrap items-start justify-between gap-3">
		<div>
			<div class="flex items-center gap-2">
				<a class="text-sm text-blue-700 underline" href="/decision-tables">Decision Tables</a>
				<span class="text-slate-400">/</span>
				<h1 class="text-xl font-bold text-slate-800">{entity.code}</h1>
				<Badge value={selectedVersion.status} />
			</div>
			<p class="text-sm text-slate-500">{entity.name} · {entity.description || 'No description'}</p>
		</div>
		<div class="flex flex-wrap items-end gap-2">
			<label class="text-xs font-semibold text-slate-600">
				Version
				<select
					class="mt-1 block rounded border-slate-300 text-sm"
					bind:value={selectedVersionId}
					onchange={() => {
						const version = entity?.versions.find((item) => item.id === selectedVersionId);
						if (version) applyVersion(version);
					}}
				>
					{#each entity.versions as version (version.id)}
						<option value={version.id}>v{version.version} · {version.status}</option>
					{/each}
				</select>
			</label>
			{#if editable}
				<button
					class="rounded bg-blue-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
					disabled={busy}
					onclick={save}>Save draft</button
				>
				<button
					class="rounded border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50"
					disabled={busy}
					onclick={submitApproval}>Submit approval</button
				>
			{:else if selectedVersion.status === 'PENDING_APPROVAL' && auth.hasPermission('rule.approve')}
				<button
					class="rounded bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
					disabled={busy}
					onclick={activate}>Activate</button
				>
			{:else if !entity.versions.some((version) => version.status === 'DRAFT' || version.status === 'PENDING_APPROVAL') && auth.hasPermission('rule.create')}
				<button
					class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
					disabled={busy}
					onclick={createDraft}>New draft from this version</button
				>
			{/if}
		</div>
	</div>

	<div class="mb-4 flex gap-2 border-b border-slate-200">
		<button
			class="border-b-2 px-3 py-2 text-sm font-semibold {tab === 'grid'
				? 'border-blue-700 text-blue-700'
				: 'border-transparent text-slate-500'}"
			onclick={() => (tab = 'grid')}>Grid</button
		>
		<button
			class="border-b-2 px-3 py-2 text-sm font-semibold {tab === 'json'
				? 'border-blue-700 text-blue-700'
				: 'border-transparent text-slate-500'}"
			onclick={() => (tab = 'json')}>Advanced JSON</button
		>
	</div>

	{#if tab === 'json'}
		<Card title="Generated decision-table configuration"
			><JsonBlock value={configPreview} maxHeight="42rem" /></Card
		>
	{:else}
		<div class="space-y-4">
			<Card title="Table settings">
				<div class="grid gap-3 lg:grid-cols-5">
					<label class="text-xs font-semibold text-slate-600"
						>Hit policy
						<select
							class="mt-1 block w-full rounded border-slate-300 text-sm"
							bind:value={grid.hitPolicy}
							disabled={!editable}
							onchange={touch}
						>
							<option value="FIRST_MATCH">FIRST MATCH</option><option value="PRIORITY"
								>PRIORITY</option
							>
						</select>
					</label>
					<label class="text-xs font-semibold text-slate-600"
						>No-match decision
						<select
							class="mt-1 block w-full rounded border-slate-300 text-sm"
							bind:value={grid.noMatchDecision}
							disabled={!editable}
							onchange={touch}
						>
							{#each meta?.decisions ?? [] as decision (decision)}<option value={decision}
									>{decision}</option
								>{/each}
						</select>
					</label>
					<label class="text-xs font-semibold text-slate-600"
						>No-match reason
						<select
							class="mt-1 block w-full rounded border-slate-300 text-sm"
							bind:value={grid.noMatchReasonCode}
							disabled={!editable}
							onchange={touch}
						>
							<option value="">None</option>{#each reasonCodes as reason (reason.id)}<option
									value={reason.code}>{reason.code}</option
								>{/each}
						</select>
					</label>
					<label class="text-xs font-semibold text-slate-600"
						>Above-limit reason
						<select
							class="mt-1 block w-full rounded border-slate-300 text-sm"
							bind:value={grid.aboveLimitReasonCode}
							disabled={!editable}
							onchange={touch}
						>
							<option value="">None</option>{#each reasonCodes as reason (reason.id)}<option
									value={reason.code}>{reason.code}</option
								>{/each}
						</select>
					</label>
					<label class="text-xs font-semibold text-slate-600"
						>Version note
						<input
							class="mt-1 block w-full rounded border-slate-300 text-sm"
							bind:value={versionNote}
							disabled={!editable}
						/>
					</label>
				</div>
			</Card>

			{#if selectedVersion.warnings.length}
				<div class="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
					<strong>Overlap warning:</strong>
					{selectedVersion.warnings.length} row pair(s) may match the same input. The selected hit policy
					determines the winner.
				</div>
			{/if}

			<Card title="Condition columns">
				<div class="flex flex-wrap items-center gap-2">
					<FeaturePicker features={featureOptions} bind:value={newColumnPath} />
					<button
						class="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
						disabled={!editable || !newColumnPath}
						onclick={addColumn}>Add condition column</button
					>
					<span class="text-xs text-slate-500">Blank cells are wildcards (*).</span>
				</div>
			</Card>

			<div class="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
				<table class="min-w-max text-xs" data-testid="decision-table-grid">
					<thead class="sticky top-0 z-10 bg-slate-100 text-left text-slate-600">
						<tr>
							<th class="sticky left-0 z-20 w-20 border-r border-slate-200 bg-slate-100 px-2 py-2"
								>Row</th
							>
							{#if grid.hitPolicy === 'PRIORITY'}<th
									class="w-20 border-r border-slate-200 px-2 py-2">Priority</th
								>{/if}
							{#each grid.columns as column, columnIndex (column.path)}
								<th class="min-w-64 border-r border-slate-200 px-2 py-2">
									<div class="flex items-center justify-between gap-2">
										<span class="font-mono text-[11px]">{column.path}</span>
										{#if editable}<span class="flex gap-1"
												><button title="Move left" onclick={() => moveColumn(columnIndex, -1)}
													>←</button
												><button title="Move right" onclick={() => moveColumn(columnIndex, 1)}
													>→</button
												><button
													class="text-red-600"
													title="Remove column"
													onclick={() => removeColumn(column.path)}>×</button
												></span
											>{/if}
									</div>
									<span class="mt-1 block text-[10px] font-normal text-slate-400"
										>{feature(column.path)?.data_type ?? 'UNKNOWN'}</span
									>
								</th>
							{/each}
							<th class="min-w-48 border-r border-slate-200 px-2 py-2">Decision</th>
							<th class="min-w-32 border-r border-slate-200 px-2 py-2">Risk grade</th>
							<th class="min-w-60 border-r border-slate-200 px-2 py-2">Approved limit</th>
							<th class="min-w-32 border-r border-slate-200 px-2 py-2">Tenor</th>
							<th class="min-w-32 border-r border-slate-200 px-2 py-2">Pricing rate</th>
							<th class="min-w-52 border-r border-slate-200 px-2 py-2">Reason code</th>
							<th class="w-36 px-2 py-2">Actions</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-200">
						{#each grid.rows as row, rowIndex (row.key)}
							<tr
								class={warningForRow(rowIndex) ? 'bg-amber-50' : 'bg-white'}
								title={rowSummary(row, grid.columns)}
							>
								<td
									class="sticky left-0 z-10 border-r border-slate-200 bg-inherit px-2 py-2 align-top font-semibold"
								>
									#{rowIndex + 1}
									{#if warningForRow(rowIndex)}<span
											class="mt-1 block rounded bg-amber-200 px-1 py-0.5 text-[9px] text-amber-900"
											>OVERLAP</span
										>{/if}
								</td>
								{#if grid.hitPolicy === 'PRIORITY'}<td
										class="border-r border-slate-200 px-2 py-2 align-top"
										><input
											class="w-16 rounded border-slate-300 text-xs"
											type="number"
											bind:value={row.priority}
											disabled={!editable}
											onchange={touch}
										/></td
									>{/if}
								{#each grid.columns as column (column.path)}
									{@const cell = row.cells[column.path]}
									<td class="border-r border-slate-200 px-2 py-2 align-top">
										<label class="mb-1 flex items-center gap-1 text-[10px] text-slate-500"
											><input
												type="checkbox"
												checked={cell.active}
												disabled={!editable}
												onchange={(event) =>
													setCellActive(cell, event.currentTarget.checked, column.path)}
											/> use condition</label
										>
										{#if !cell.active}
											<div
												class="rounded border border-dashed border-slate-300 py-3 text-center text-lg text-slate-400"
											>
												*
											</div>
										{:else}
											<select
												class="mb-1 block w-full rounded border-slate-300 text-xs"
												bind:value={cell.operator}
												disabled={!editable}
												onchange={touch}
											>
												{#each operators(column.path) as operator (operator)}<option
														value={operator}>{operator}</option
													>{/each}
											</select>
											{#if cell.operator !== 'exists' && cell.operator !== 'is_null'}
												{#if feature(column.path)?.data_type === 'BOOLEAN'}
													<select
														class="block w-full rounded border-slate-300 text-xs"
														value={String(cell.value)}
														disabled={!editable}
														onchange={(event) => {
															cell.value = event.currentTarget.value === 'true';
															touch();
														}}
														><option value="true">true</option><option value="false">false</option
														></select
													>
												{:else}
													<input
														class="block w-full rounded border-slate-300 text-xs"
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
													/>
												{/if}
											{/if}
										{/if}
									</td>
								{/each}
								<td class="border-r border-slate-200 px-2 py-2 align-top"
									><select
										class="w-full rounded border-slate-300 text-xs"
										bind:value={row.output.decision}
										disabled={!editable}
										onchange={touch}
										>{#each meta?.decisions ?? [] as decision (decision)}<option value={decision}
												>{decision}</option
											>{/each}</select
									></td
								>
								<td class="border-r border-slate-200 px-2 py-2 align-top"
									><input
										class="w-full rounded border-slate-300 text-xs"
										maxlength="5"
										placeholder="optional"
										value={row.output.risk_grade ?? ''}
										disabled={!editable}
										oninput={(event) => {
											row.output.risk_grade = event.currentTarget.value || null;
											touch();
										}}
									/></td
								>
								<td class="border-r border-slate-200 px-2 py-2 align-top">
									<input
										class="mb-1 w-full rounded border-slate-300 text-xs"
										type="number"
										placeholder="literal amount"
										value={row.output.approved_limit ?? ''}
										disabled={!editable || Boolean(row.output.approved_limit_pct_of)}
										oninput={(event) => {
											row.output.approved_limit =
												event.currentTarget.value === '' ? null : Number(event.currentTarget.value);
											touch();
										}}
									/>
									<label class="flex items-center gap-1 text-[10px] text-slate-500"
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
									>
									{#if row.output.approved_limit_pct_of}<div class="mt-1 flex gap-1">
											<input
												class="min-w-36 flex-1 rounded border-slate-300 text-[10px]"
												list="limit-fields"
												bind:value={row.output.approved_limit_pct_of.field}
												disabled={!editable}
												onchange={touch}
											/><input
												class="w-16 rounded border-slate-300 text-[10px]"
												type="number"
												step="0.01"
												min="0.01"
												max="1"
												bind:value={row.output.approved_limit_pct_of.pct}
												disabled={!editable}
												onchange={touch}
											/>
										</div>{/if}
								</td>
								<td class="border-r border-slate-200 px-2 py-2 align-top"
									><input
										class="w-full rounded border-slate-300 text-xs"
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
								<td class="border-r border-slate-200 px-2 py-2 align-top"
									><input
										class="w-full rounded border-slate-300 text-xs"
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
								<td class="border-r border-slate-200 px-2 py-2 align-top"
									><select
										class="w-full rounded border-slate-300 text-xs"
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
								<td class="px-2 py-2 align-top"
									><div class="flex flex-wrap gap-1">
										{#if editable}<button
												class="rounded border px-1.5 py-1"
												title="Move up"
												onclick={() => moveRow(rowIndex, -1)}>↑</button
											><button
												class="rounded border px-1.5 py-1"
												title="Move down"
												onclick={() => moveRow(rowIndex, 1)}>↓</button
											><button
												class="rounded border px-1.5 py-1"
												title="Duplicate"
												onclick={() => duplicateRow(rowIndex)}>Copy</button
											><button
												class="rounded border border-red-200 px-1.5 py-1 text-red-600"
												title="Delete"
												onclick={() => deleteRow(rowIndex)}>Delete</button
											>{/if}
									</div></td
								>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<datalist id="limit-fields"
				>{#each featureOptions as item (item.path)}<option value={item.path}>{item.label}</option
					>{/each}</datalist
			>
			{#if editable}<button
					class="rounded border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
					onclick={() => addRow()}>+ Add row</button
				>{/if}
		</div>
	{/if}
{:else if !error}
	<p class="text-sm text-slate-500">Loading decision table…</p>
{/if}
