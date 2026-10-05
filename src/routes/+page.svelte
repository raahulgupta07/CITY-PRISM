<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { api, ApiError, ROLE_LABELS, type User } from '$lib/api';

	let user = $state<User | null>(null);
	let error = $state('');

	onMount(async () => {
		try {
			user = await api<User>('/me');
		} catch (e) {
			if (e instanceof ApiError && e.status === 401) await goto(resolve('/signin'));
			else error = e instanceof Error ? e.message : String(e);
		}
	});

	async function signOut() {
		await api('/auth/logout', { method: 'POST' });
		await goto(resolve('/signin'));
	}
</script>

<header class="flex h-14 items-center justify-between bg-navy px-4 text-white sm:px-6">
	<span class="font-condensed text-lg font-semibold tracking-wide">City Prism</span>
	{#if user}
		<div class="flex items-center gap-4 text-sm">
			<span>{user.name} · {ROLE_LABELS[user.role]}</span>
			<button
				class="min-h-11 px-3 text-teal-on-dark underline-offset-4 hover:underline"
				onclick={signOut}>Sign out</button
			>
		</div>
	{/if}
</header>

<main class="mx-auto max-w-3xl px-4 py-10 sm:px-6">
	{#if error}
		<p role="alert" class="border-l-4 border-weak bg-panel p-4">{error}</p>
	{:else if user}
		<h1 class="font-condensed text-3xl font-semibold">AI project portfolio</h1>
		<p class="mt-2 text-muted">You are signed in. The portfolio screen is being built next.</p>
	{:else}
		<p class="text-muted">Loading…</p>
	{/if}
</main>
