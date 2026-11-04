<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/auth.svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import ErrorNote from '$lib/components/ErrorNote.svelte';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		error = '';
		loading = true;
		try {
			await auth.login(username, password);
			goto('/dashboard');
		} catch (caught) {
			error = caught instanceof Error ? caught.message : 'Login failed';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head><title>Sign in · OSCAR</title></svelte:head>

<div class="flex min-h-screen items-center justify-center bg-surface-muted px-4 py-10">
	<div class="w-full max-w-md">
		<div class="mb-6 text-center">
			<div
				class="mx-auto mb-3 flex size-12 items-center justify-center rounded-card bg-primary-600 text-lg font-bold text-white shadow-card"
			>
				O
			</div>
			<h1 class="text-xl font-semibold text-text">OSCAR Decision Engine</h1>
			<p class="mt-1 text-sm text-text-muted">
				Governed decisioning, simulation, and audit in one workbench.
			</p>
		</div>

		<Card.Root class="border-border shadow-card">
			<Card.Header>
				<Card.Title>Sign in to your workspace</Card.Title>
				<Card.Description>Use your OSCAR account to continue.</Card.Description>
			</Card.Header>
			<Card.Content>
				<form class="space-y-4" onsubmit={submit}>
					<div class="space-y-1.5">
						<Label for="username">Username</Label>
						<Input id="username" autocomplete="username" bind:value={username} required />
					</div>
					<div class="space-y-1.5">
						<Label for="password">Password</Label>
						<Input
							id="password"
							type="password"
							autocomplete="current-password"
							bind:value={password}
							required
						/>
					</div>
					{#if error}<ErrorNote {error} />{/if}
					<Button type="submit" class="w-full" disabled={loading}>
						{loading ? 'Signing in…' : 'Sign in'}
					</Button>
				</form>
			</Card.Content>
		</Card.Root>
	</div>
</div>
