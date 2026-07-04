<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/auth.svelte';
	import ErrorNote from '$lib/components/ErrorNote.svelte';

	let username = $state('');
	let password = $state('');
	let error = $state<unknown>(null);
	let submitting = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		submitting = true;
		try {
			await auth.login(username, password);
			goto('/dashboard');
		} catch (err) {
			error = err;
		} finally {
			submitting = false;
		}
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-slate-900">
	<form class="w-96 rounded-lg bg-white p-8 shadow-xl" onsubmit={submit}>
		<h1 class="text-xl font-bold text-slate-800">OSCAR Decision Engine</h1>
		<p class="mb-6 text-sm text-slate-500">Sign in to the risk policy workbench</p>

		<label class="mb-3 block">
			<span class="text-xs font-semibold text-slate-600 uppercase">Username</span>
			<input
				class="mt-1 w-full rounded border-slate-300 text-sm"
				bind:value={username}
				name="username"
				autocomplete="username"
				required
			/>
		</label>
		<label class="mb-4 block">
			<span class="text-xs font-semibold text-slate-600 uppercase">Password</span>
			<input
				class="mt-1 w-full rounded border-slate-300 text-sm"
				type="password"
				name="password"
				bind:value={password}
				autocomplete="current-password"
				required
			/>
		</label>

		{#if error}
			<div class="mb-3"><ErrorNote {error} /></div>
		{/if}

		<button
			class="w-full rounded bg-slate-900 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
			type="submit"
			disabled={submitting}
		>
			{submitting ? 'Signing in…' : 'Sign in'}
		</button>
	</form>
</div>
