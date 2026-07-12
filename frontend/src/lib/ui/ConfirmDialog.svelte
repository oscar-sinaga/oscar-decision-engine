<script module lang="ts">
	export { confirmAction } from './confirm';
</script>

<script lang="ts">
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { Label } from '$lib/components/ui/label';
	import { Textarea } from '$lib/components/ui/textarea';
	import type { ConfirmOptions, ConfirmResult } from './confirm';

	type Request = {
		options: ConfirmOptions;
		resolve: (result: ConfirmResult) => void;
	};

	let request = $state<Request | null>(null);
	let reason = $state('');

	$effect(() => {
		const handler = (event: Event): void => {
			const custom = event as CustomEvent<Request>;
			request = custom.detail;
			reason = '';
		};
		window.addEventListener('oscar-confirm', handler);
		return () => window.removeEventListener('oscar-confirm', handler);
	});

	function finish(ok: boolean): void {
		if (!request) return;
		request.resolve(ok ? { ok: true, reason: reason.trim() || undefined } : { ok: false });
		request = null;
		reason = '';
	}
</script>

<AlertDialog.Root
	open={request !== null}
	onOpenChange={(open) => {
		if (!open && request) finish(false);
	}}
>
	{#if request}
		<AlertDialog.Content class="rounded-card shadow-overlay">
			<AlertDialog.Header>
				<AlertDialog.Title>{request.options.title}</AlertDialog.Title>
				<AlertDialog.Description>
					{request.options.body ?? 'Confirm this action before continuing.'}
				</AlertDialog.Description>
			</AlertDialog.Header>

			{#if request.options.requireReason}
				<div class="space-y-1.5">
					<Label for="confirm-reason">Reason</Label>
					<Textarea id="confirm-reason" rows={3} bind:value={reason} />
				</div>
			{/if}

			<AlertDialog.Footer>
				<AlertDialog.Cancel onclick={() => finish(false)}>Cancel</AlertDialog.Cancel>
				<AlertDialog.Action
					variant={request.options.tone === 'danger' ? 'destructive' : 'default'}
					disabled={request.options.requireReason && !reason.trim()}
					onclick={() => finish(true)}
				>
					{request.options.confirmLabel}
				</AlertDialog.Action>
			</AlertDialog.Footer>
		</AlertDialog.Content>
	{/if}
</AlertDialog.Root>
